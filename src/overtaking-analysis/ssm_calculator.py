"""Calculate Surrogate Safety Measures (SSMs) for overtaking maneuvers."""
from logging import Logger

import numpy as np
import pandas as pd
import shapely as shp
from configuration import SSMConfig
from utils.bicycle import OvertakenBicycle
from utils.type_casting import to_np_float


class SSMCalculator:
    """Calculate Surrogate Safety Measures (SSMs) for overtaking maneuvers."""

    def __init__(self,
                    logger: Logger,
                    config: SSMConfig | None = None,
                    bike: OvertakenBicycle | None = None) -> None:
        """Initialize the SSMCalculator with logger, configuration, and bike."""
        if logger is None or config is None or bike is None:
            raise ValueError("Logger, config, and bike must be provided.")
        self.logger = logger
        self.config = config
        self.bike = bike

    def calculate_ssms(self,
                        df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Calculate Surrogate Safety Measures (SSMs) for overtaking maneuvers.

        Parameters
        ----------
        df : pandas.DataFrame, optional
            DataFrame containing trajectory data.

        Returns
        -------
        pd.DataFrame
            Updated DataFrame with calculated SSMs.
        """
        if df is None:
            raise ValueError("DataFrame must be provided.")

        # Calculate the lateral clearances, determine minimum per
        # overtaking maneuver/oncoming traffic
        df = self.add_lateral_clearance(df=df)

        # Add boolean columns whether the car is on collision course with the bike
        # or vice versa
        df = self.add_on_collision_course(df=df)

        # Calculate longitudinal clearances to the front and back and
        # corresponding relative velocities
        df = self.add_long_clearance(df=df)

        # Add the time to collision between all cars on collision course with the bike
        df = self.add_ttc(df=df)

        # Calculate the time a car spent in the backward polygon
        df = self.add_time_spent_following(df=df)

        df = self.calculate_oncoming_pet(df=df)

        self.logger.info("SSM calculation completed.")
        return df

    def add_lateral_clearance(self,
            df: pd.DataFrame | None = None)-> pd.DataFrame:
        """
        Add the minimum lateral clearance to the DataFrame.

        Also add the relative velocity at that time.
        """
        if df is None:
            raise ValueError("DataFrame must be provided.")
        df["lateral_clearance"] = [
            # Lateral clearance only exists when the vehicle is in the passing zone.
            # Then, it can be calculated between the bikes BB and the intersection of
            # the passing zone and the vehicle BB.
            shp.distance(self.bike.pol, shp.intersection(self.bike.lat_pol, row))
            for row in df["BB_polygon"]
        ]

        self.logger.info("Minimum lateral clearance added.")

        return df


    def add_on_collision_course(self,
                                df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Add a boolean column whether the car is on course to hit the bike.

        Parameters
        ----------
        df : pandas.DataFrame, optional
            DataFrame containing trajectory data.

        Returns
        -------
        pandas.DataFrame
            DataFrame with collision course information added.
        """
        if df is None:
            raise ValueError("DataFrame must be provided.")

        front_pol_values = to_np_float(
                                df[["position_x", "position_y",
                                    "scale_x", "scale_y",
                                    "rotation_z"]])
        front_polygons = []

        for (pos_x, pos_y, scale_x, scale_y,
                rotation_z) in front_pol_values:
            front_polygons.append(
                self._create_front_polygon(
                    pos_x, pos_y, scale_x, scale_y, rotation_z
                )
            )

        df["car_front_polygon"] = front_polygons

        # Check whether 99.9% of the original car polygon are within
        # the corresponding front polygon
        # shp.within fails for minimal differences resulting from the affinity
        # transformation, so we check the area difference instead
        if not all(p1.difference(p2).area / p1.area < 0.1 for (p1, p2) in
                    zip(df["BB_polygon"], df["car_front_polygon"], strict=True)):
            raise ValueError("Car front polygon does not sufficiently"
                                " cover the original bounding box polygon.")

        df["car_on_collision_course"] = [not intersect.is_empty for intersect in
                                            shp.intersection(df["car_front_polygon"],
                                                            self.bike.pol)]
        df["bike_on_collision_course"] = [not intersect.is_empty for intersect in
                                            shp.intersection(df["BB_polygon"],
                                                self.bike.collision_course_pol)]
        self.logger.info("Collision course information added.")
        return df

    def _create_front_polygon(self,
                                pos_x: float,
                                pos_y: float,
                                scale_x: float,
                                scale_y: float,
                                rotation_z: float,
                                ) -> shp.Polygon:
        return shp.affinity.rotate(
            shp.Polygon(
                (
                    (pos_x + 25, pos_y + scale_y / 2),
                    (pos_x + 25, pos_y - scale_y / 2),
                    (pos_x - scale_x / 2, pos_y - scale_y / 2),
                    (pos_x - scale_x / 2, pos_y + scale_y / 2),
                )
            ),
            rotation_z,
            use_radians=True,
            origin=(pos_x, pos_y)
        )

    def add_long_clearance(self,
                            df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Add the minimum longitudinal clearance and relative velocity.

        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame containing trajectory data.

        Returns
        -------
        pd.DataFrame
            The updated trajectory DataFrame.
        """
        assert df is not None, "DataFrame is required"

        # We define the longitudinal clearance as the distance between the bicycles
        # and the vehicle's bounding box polygons
        # in all cases where the rear vehicle is on a collision course.

        # Calculate longitudinal clearance in behind the bicycle
        df["longitudinal_clearance_back"] = (df['dist_polygon'].
                                                where(df["car_on_collision_course"]))

        # Calculate longitudinal clearance in front of the bicycle
        df["longitudinal_clearance_front"] = (df['dist_polygon'].
                                                where(df["bike_on_collision_course"]))

        self.logger.info("Longitudinal clearances added.")

        return df

    def add_ttc(self,
                df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Add Time-To-Collision (TTC) calculations to the trajectories.

        This method computes TTC for each frame where a car is on a collision course,
        defined as distance to the collision polygon divided by the smoothed velocity.
        The TTC is set to infinity for frames where the car is not on collision course.

        Parameters
        ----------
        df : pd.DataFrame
            The main DataFrame containing trajectory and collision data.

        Returns
        -------
        pd.DataFrame
            The updated trajectory DataFrame.
        """
        if df is None:
            raise ValueError("DataFrame must be provided.")

        df["ttc"] = np.where(df["car_on_collision_course"], df["dist_polygon"] /
                                df["v_smooth_ms"], np.inf)

        self.logger.info("TTC added")

        return df

    def add_time_spent_following(self,
                            df: pd.DataFrame | None = None) -> pd.DataFrame:
            """
            Add time spent following information to the trajectories.

            Calculates and adds the time a car spends within the backwards polygon
            with a relative speed below the configured threshold.

            Parameters
            ----------
            df : pd.DataFrame, optional
                The main DataFrame containing trajectory and clearance data.

            Returns
            -------
            pd.DataFrame
                The updated trajectory DataFrame with time spent following information.
            """
            if df is None:
                raise ValueError("DataFrame must be provided.")

            df['following'] = df["phase"].isin(["overtaking_following",
                                                "following_following"])

            speed_mask = df["v_smooth_ms"].abs() <= self.config.tsf_speed_thresh
            df['tsf'] = df[df['following'] & speed_mask].groupby(
                ['traj_id'])['time_diff'].cumsum()

            df['tsf'] = df.groupby(['traj_id'])['tsf'].ffill()

            self.logger.info("Time spent following added.")
            return df

    def calculate_oncoming_pet(self,
                            df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Calculate the PET between overtaking and oncoming vehicles.

        Detects overtaking maneuvers that involve oncoming traffic
        and updates the DataFrame accordingly.

        Parameters
        ----------
        df : pd.DataFrame
            The main DataFrame containing trajectory and maneuver data.

        Returns
        -------
        pd.DataFrame
            The updated DataFrame.
        """
        if df is None:
            raise ValueError("DataFrame must be provided.")
        # TODO: Add oncoming definition for following maneuvers
        oncoming_passing_timestamps = {scene_name: scene[scene['phase'] ==
                                        'oncoming_passing']['timestamp'].astype(int)
                                    for scene_name, scene in df.groupby('scene')}

        df['oncoming_pet'] = df.apply(self.calc_framewise_pet,
                                axis=1,
                                oncoming_passing_timestamps=oncoming_passing_timestamps)

        df['with_oncoming'] = (df[df['maneuver'] == 'overtaking_maneuver']
                                .groupby(['traj_id'])
                ['oncoming_pet'].transform('min') <=
                    self.config.oncoming_pet_thresh)

        self.logger.info("Oncoming traffic during overtaking maneuvers calculated.")
        return df

    def calc_framewise_pet(self,
                            row: pd.Series | None = None,
                            oncoming_passing_timestamps: dict | None = None) -> float:
        """
        Calculate the point of encounter time (PET) based on oncoming passing frames.

        Parameters
        ----------
        row : pd.Series
            A row from the DataFrame representing a single time step of a trajectory.
        oncoming_passing_timestamps : dict
            A dictionary mapping scene names to Series of timestamps
            where oncoming passing occurs.

        Returns
        -------
        float
            The calculated PET for the given row.
        """
        if row is None or oncoming_passing_timestamps is None:
            raise ValueError("Row and oncoming passing timestamps must be provided.")

        if row['phase'] in ['overtaking_passing', 'following_following']:
            scene_timestamps = oncoming_passing_timestamps.get(row['scene'],
                                                            pd.Series(dtype=int))
            if not scene_timestamps.empty:
                return np.min([abs(int(row['timestamp']) - onf) /
                                10**3 for onf in scene_timestamps])

        return np.inf
