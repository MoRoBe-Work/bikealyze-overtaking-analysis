"""Detect the phases of overtaking and oncoming vehicles."""
from logging import Logger

import pandas as pd
from utils.bicycle import OvertakenBicycle


class PhaseDetector:
    """Detect the phases of overtaking and oncoming vehicles."""

    def __init__(self,
                    logger: Logger | None = None,
                    bike: OvertakenBicycle | None = None) -> None:
        if logger is None or bike is None:
            raise ValueError("Logger and bike must be provided")

        self.logger = logger
        self.bike = bike

    def run(self,
            df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Run the phase detection process on the provided DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            The main DataFrame containing trajectory data.

        Returns
        -------
        pd.DataFrame
            The updated DataFrame with phase information added.
        """
        if df is None:
            raise ValueError("DataFrame must be provided")

        df = self.add_phases(df=df)

        return df

    def detect_phase(self,
                        row: pd.Series | None = None) -> str | None:
        """
        Detect the phase of an overtaking maneuver for a given row.

        Parameters
        ----------
        row : pd.Series
            A row from the DataFrame representing a single time step of a trajectory.

        Returns
        -------
        str
            The detected phase of the overtaking maneuver.
        """
        if row is None:
            raise ValueError("Row must be provided")

        passing = row['BB_polygon'].intersects(self.bike.lat_pol)

        match row['maneuver']:
            case 'following_vehicle':
                return 'following_following' if self.bike.lon_pol_back.contains(
                    row['front_right']) else None
            case 'oncoming_traffic':
                return ('oncoming_passing' if passing else 'oncoming_approaching' if
                    row['position_x'] > 0 else 'oncoming_driving_away')
            case 'overtaking_maneuver':
                if passing:
                    return 'overtaking_passing'
                elif self.bike.lon_pol_back.contains(row['front_right']):
                    return 'overtaking_following'
                elif row['position_x'] < 0 and row['min_x'] >= -self.bike.lon_pol_len:
                    return 'steering_away'
                elif row['position_x'] > 0 and row['max_x'] <= self.bike.lon_pol_len:
                    return 'steering_back'
                else:
                    return None
            case _:
                return None

    def add_phases(self,
                    df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Add phase information to the DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            The main DataFrame containing trajectory data.

        Returns
        -------
        pd.DataFrame
            The updated DataFrame with phase information added.
        """
        assert df is not None, "DataFrame is required"

        df['phase'] = df.apply(self.detect_phase, axis=1)

        self.logger.info("Phases added to DataFrame.")
        return df
