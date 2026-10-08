"""
Data loader for reading trajectory files.

Stores loaded detections in a trajectory DataFrame.
"""
from logging import Logger

import geopandas as gpd
import pandas as pd
from configuration import DataLoaderConfig


class DataLoader:
    """
    Data loader for reading trajectory CSV files.

    Stores loaded detections in a trajectory DataFrame.
    """

    def __init__(self,
                    logger: Logger,
                    config: DataLoaderConfig) -> None:

        self.logger = logger
        self.config = config


    def load_trajectories(self) -> pd.DataFrame:
        """
        Load trajectories from the specified trajectory file.

        :return: DataFrame containing the merged trajectories
        """
        df = self.load_precomputed()

        return df


    def load_precomputed(self) -> pd.DataFrame:
        """
        Load precomputed trajectories from CSV files.

        :return: DataFrame containing the trajectory data
        """
        self.logger.info("Loading precomputed trajectory from CSV file.")

        # Load trajectory data
        df = pd.read_csv(self.config.valid_trajectory_file)

        # If the 'traj_id' is not explicitly provided,
        # generate it from 'scene' and 'id' columns
        if 'traj_id' not in df.columns:
            if 'scene' in df.columns and 'id' in df.columns:
                df['traj_id'] = df['scene'].astype(str) + "_" + df['id'].astype(str)
            else:
                raise ValueError("Either 'traj_id' or both 'scene' and 'id' columns "
                                    "must be present.")

        # For geopandas reasons, the coordinates need to be called 'geometry'
        df['geometry'] = gpd.GeoSeries.from_wkt(df['coord_bike'])

        return df

