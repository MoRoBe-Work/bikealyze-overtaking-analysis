"""Calculate primitive geometric features and relationships of the detected vehicles."""

from logging import Logger

import numpy as np
import pandas as pd
import shapely as shp
from configuration import TrajectoryHandlerConfig
from scipy.ndimage import gaussian_filter
from utils.bicycle import OvertakenBicycle
from utils.type_casting import to_np_float


class TrajectoryHandler:
    """
    Handles the trajectory data of the overtaking analysis.

    This class is responsible for recognizing and labeling trajectories of
    vehicles in relation to a bicycle, specifically identifying overtaking
    maneuvers and oncoming traffic.
    """

    def __init__(self,
                logger: Logger,
                bike: OvertakenBicycle | None = None,
                config: TrajectoryHandlerConfig | None = None) -> None:
        if logger is None or bike is None or config is None:
            raise ValueError("Logger, bike, and config must be provided.")
        self.logger = logger
        self.bike = bike
        self.config = config

    def run(self,
            df: pd.DataFrame | None = None) -> pd.DataFrame:
        """Run the trajectory recognition and labeling process."""
        if df is None:
            raise ValueError("DataFrame must be provided.")

        # Create bounding boxes and add distances of vehicles
        df = self._create_bounding_boxes(df=df)
        df = self._add_distances_bb(df=df)

        # Add and smooth velocities
        df = self._add_rel_velocities(df=df)
        df = self._smooth_velocities(df=df, sigma=2)

        # Add maneuvers to DataFrame
        df = self._add_maneuvers_to_df(df=df)

        df = self._to_global_coords(df=df)

        return df


    def _first_last_x(self,
                    group: pd.DataFrame | None = None) -> pd.Series:
        """Get the first and last frame and x-positions of a group of observations."""
        assert group is not None, "Group is required"
        first_row = group.iloc[0]
        last_row = group.iloc[-1]
        return pd.Series({
            'min_frame': first_row['frame'],
            'x_at_min_frame': first_row['position_x'],
            'max_frame': last_row['frame'],
            'x_at_max_frame': last_row['position_x'],
            'length_in_frames': int(last_row['frame']) - int(first_row['frame']) + 1,
            'max_x': group['position_x'].max(),
            'min_x': group['position_x'].min(),
            'max_x_frame': group.loc[group['position_x'].idxmax()]['frame'],
            'min_x_frame': group.loc[group['position_x'].idxmin()]['frame'],
            'y_at_min_dist': group.loc[group['dist_polygon'].idxmin()]
            ['position_y'],
        })

    def _recognize_maneuver(self,
                        row: pd.Series | None = None) -> str | None:
        if row is None:
            raise ValueError("Row is required for maneuver recognition.")
        """Recognizes the maneuver based on the x-pos at the first and last frame."""
        if (row["min_x"] < 0 and row['max_x'] > 0 and \
            row['min_x_frame'] < row['max_x_frame']):
            return "overtaking_maneuver"
        if (row["x_at_min_frame"] > 0 # starts in front of the bike
            and row['x_at_max_frame'] < 0 # ends behind the bike
            and row['y_at_min_dist'] > 0): # is left of the bike at closest distance
            return "oncoming_traffic"
        if row["x_at_min_frame"] < 0 and row['x_at_max_frame'] < 0:
            return "following_vehicle"
        else:
            return None

    def _add_maneuvers_to_df(self,
                            df: pd.DataFrame | None = None) -> pd.DataFrame:
        if df is None:
            raise ValueError("DataFrame is required")

        # Group per trajectory, then get min and max x-positions
        min_max_x = df.groupby(["traj_id"],
                        group_keys=False).apply(self._first_last_x).reset_index()

        min_max_x["maneuver"] = min_max_x.apply(self._recognize_maneuver, axis=1)

        # If the 'maneuver' column already exists in the DataFrame,
        # remove it before merging new data.
        # Necessary in case precomputed maneuvers are being reprocessed.
        if 'maneuver' in df.columns:
            df.drop(columns=['maneuver'], inplace=True)

        # Merge maneuver information into the main DataFrame
        df = df.merge(min_max_x[["traj_id", "maneuver"]],
                        on=["traj_id"],
                        how="left")

        self.logger.info("Maneuvers added to trajectories.")

        return df

    def _create_bounding_boxes(self,
                            df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Create shapely polygons representing each cars 2D bounding box.

        :param df: DataFrame with cars positions, scales and rotations.

        :return: Nothing, DataFrame is modified in place
        """
        if df is None:
            raise ValueError("DataFrame is required")
        if not pd.api.types.is_float_dtype(df["rotation_z"]):
            raise TypeError("rotation_z must be of float dtype")

        # Explicitly cast to float for type safety
        bb_values = to_np_float(df[["position_x",
                                    "position_y",
                                    "scale_x",
                                    "scale_y",
                                    "rotation_z"]])
        bb_polygons = []
        for pos_x, pos_y, scale_x, scale_y, rotation_z in bb_values:
            bb_polygons.append(
                self._create_bounding_box(
                    pos_x=pos_x,
                    pos_y=pos_y,
                    scale_x=scale_x,
                    scale_y=scale_y,
                    rotation_z=rotation_z,
                ))

        df["BB_polygon"] = bb_polygons
        df[["min_x", "max_x", "min_y", "max_y"]] = [
            (
                min(polygon.exterior.xy[0]),
                max(polygon.exterior.xy[0]),
                min(polygon.exterior.xy[1]),
                max(polygon.exterior.xy[1]),
            )
            for polygon in df["BB_polygon"]
        ]

        df['front_right'] = df.apply(self._select_front_right, axis=1)
        self.logger.info("Corner coordinates added.")

        return df

    def _create_bounding_box(self,
                                pos_x: float,
                                pos_y: float,
                                scale_x: float,
                                scale_y: float,
                                rotation_z: float) -> shp.Polygon:
        return shp.affinity.rotate(
            shp.Polygon(
                (
                    (
                        pos_x + scale_x / 2,
                        pos_y + scale_y / 2,
                    ),
                    (
                        pos_x + scale_x / 2,
                        pos_y - scale_y / 2,
                    ),
                    (
                        pos_x - scale_x / 2,
                        pos_y - scale_y / 2,
                    ),
                    (
                        pos_x - scale_x / 2,
                        pos_y + scale_y / 2,
                    ),
                )
            ),
            rotation_z,
            use_radians=True,
        )


    def _add_distances_bb(self,
                        df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Add distances between the bounding boxes of vehicles and the bicycle.

        Parameters
        ----------
        df: pandas.DataFrame
            The trajectories DataFrame

        Returns
        -------
        None, provided DataFrame is extended by three columns
        """
        if df is None:
            raise ValueError("DataFrame is required")

        df["dist_polygon"] = [
            shp.distance(self.bike.pol, row) for row in df["BB_polygon"]
        ]

        self.logger.info("Distances added.")

        return df

    def _plateau_weights(self,
                        x: float = 0.0,
                        high: float = 10.0,
                        low: float = 25.0) -> float:
        """
        Weighting function for the distance measures.

        Flat with y=0 until x=-low,
        linear between x=-low and x=-high,
        y=1 from x=-high to x=high,
        linearly declining between x=high and x=low,
        and flat with y=0 again above x=low.
        """
        x = abs(x)
        if x < high:
            return 1
        if x > low:
            return 0
        return -1 / (low - high) * x + low / (low - high) # (low - x) / (low - high)

    def _add_rel_velocities(self,
                            df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Calculate relative velocity of vehicles to the bicycle.

        Parameters
        ----------
        df : pandas.DataFrame, optional
            The trajectories DataFrame.

        Returns
        -------
        pandas.DataFrame
            DataFrame with added relative velocity columns.
        """
        if df is None:
            raise ValueError("DataFrame is required")
        # two different approaches to position difference
        # 1: distance of consecutive points
        df["diff_x"] = df.groupby(["traj_id"])[("position_x")].diff()
        df["diff_y"] = df.groupby(["traj_id"])[("position_y")].diff()
        df["d1"] = np.sqrt(np.square(df["diff_x"]) + np.square(df["diff_y"]))

        # 2: change of distance to bike
        df["dist_center_xy"] = np.sqrt(
            np.square(df["position_x"]) + np.square(df["position_y"])
        )
        df["d2"] = df.groupby(["traj_id"])["dist_center_xy"].diff()

        # check the difference between these two measures; only to check
        df["d1_d2_diff"] = df["d2"].abs() - df["d1"]

        # weighted sum of these measures
        df["d_weight"] = df["dist_center_xy"].apply(self._plateau_weights)
        df["d"] = df["d_weight"] * df["d1"] + (1 - df["d_weight"]) * df["d2"].abs()

        df["d"] = df["d"].bfill()  # fill NaN values with the next value

        # velocity
        # Time difference in seconds from timestamps in milliseconds
        df['time_diff'] = df.groupby(["traj_id"])["timestamp"].diff() * 1e-3
        df['time_diff'] = df['time_diff'].bfill()  # fill NaN values with the next value
        df["vel_rel_ms"] = df["d"] / df["time_diff"]
        df["vel_rel_kmh"] = df["vel_rel_ms"] * 3.6

        self.logger.info("Velocities added.")

        return df

    def _smooth_velocities(self,
                        df: pd.DataFrame | None = None,
                        sigma: float = 2) -> pd.DataFrame:
        """
        Smooth the velocity with a Gaussian kernel.

        Sigma=2 seems to work fine, but not tested extensively.
        """
        if df is None:
            raise ValueError("DataFrame is required")

        # The first frame per trajectory has no speed,
        # so we assume it is the same as the next frame
        df['vel_rel_kmh'] = df['vel_rel_kmh'].bfill()
        df["v_smooth_kmh"] = df.groupby(["traj_id"])["vel_rel_kmh"] \
            .transform(lambda x: gaussian_filter(x, sigma=sigma, mode='nearest'))
        df["v_smooth_ms"] = df["v_smooth_kmh"] / 3.6

        self.logger.info(f"Smoothed relative velocity with sigma = {sigma} added.")

        return df

    def _select_front_right(self,
                            row: pd.Series | None = None) -> shp.Point:
        if row is None:
            raise ValueError("Row is required")
        front_coords = [coord for coord in row['BB_polygon'].exterior.coords
                        if coord[0] > row['position_x']]

        front_right = front_coords[0] if front_coords[0][1] < front_coords[1][1] \
                                        else front_coords[1]

        return shp.Point(front_right)

    def _to_global_coords(self,
                            df: pd.DataFrame | None = None) -> pd.DataFrame:
        if df is None:
            raise ValueError("DataFrame is required")


        df["BB_bike"] = pd.Series([self.bike.pol] * len(df), index=df.index)

        df["transformed_polygon"] = df.apply(
            lambda row: self._global_coords(
                pol=row["BB_polygon"],
                theta=row["theta"],
                orig_x=row["geometry"].x,
                orig_y=row["geometry"].y,
            ),
            axis=1,
        )

        df["transformed_bike"] = df.apply(
            lambda row: self._global_coords(
                pol=row["BB_bike"],
                theta=row["theta"],
                orig_x=row["geometry"].x,
                orig_y=row["geometry"].y,
            ),
            axis=1,
        )

        return df

    def _global_coords(self,
                        pol: shp.Polygon | None = None,
                        theta: float = 0.0,
                        orig_x: float = 0.0,
                        orig_y: float = 0.0) -> shp.Polygon:
        if pol is None:
            raise ValueError("Polygon is required")

        matrix = [np.cos(theta),
                    -np.sin(theta),
                    np.sin(theta),
                    np.cos(theta),
                    orig_x,
                    orig_y]

        return shp.affinity.affine_transform(geom=pol,
                                                matrix=matrix)

