"""Write overtaking analysis results to disk."""
from logging import Logger

from configuration import AnalyzerConfig, WriterConfig
from pandas import DataFrame
from toml import dump


class Writer:
    """Write overtaking analysis results to disk."""

    def __init__(self,
                    config: WriterConfig,
                    logger: Logger | None = None) -> None:
        """
        Initialize the Writer with the provided configuration.

        :param config: Configuration for the writer.
        :param logger: Logger instance for logging.
        """
        if logger is None or config is None:
            raise ValueError("Both logger and config must be provided.")
        self.config = config
        self.logger = logger

    def write_trajectories(self,
                            df: DataFrame | None = None,
                            additional_columns: list[str] | None = None) -> None:
        """
        Write the analysis results to files.

        :param df: DataFrame containing trajectory data.
        """
        if df is None:
            raise ValueError("DataFrame must be provided.")

        if 'coord_bike' not in df.columns:
            df.rename(columns={'geometry': 'coord_bike'}, inplace=True)

        # Write all columns required for the analysis to allow repeated analysis.
        input_cols = ['scene',
                        'frame',
                        'timestamp',
                        'coord_bike',
                        'theta',
                        'v_bike',
                        'id',
                        'position_x',
                        'position_y',
                        'scale_x',
                        'scale_y',
                        'rotation_z',
                    ]

        # Write result columns required for road segment assessment
        output_cols = ['traj_id',
                        'rel_v_car',
                        'lateral_clearance',
                        'longitudinal_clearance_back',
                        'maneuver',
                        'phase',
                        'with_oncoming',
                        'tsf',
                        'ttc',
                    ]

        write_columns = input_cols + output_cols

        if additional_columns is not None:
            write_columns += [col for col in additional_columns
                                if col not in write_columns]

        # Write results to specified output directory
        df.to_csv(f"{self.config.out_dir}/trajectory_df"
                    f"{self.config.file_name_suffix}.csv",
                    columns=write_columns,
                    index=False)

    def write_config(self,
                        config: AnalyzerConfig | None = None) -> None:
        """Write the configuration to a TOML file."""
        if config is None:
            raise ValueError("Configuration needs to be provided")
        with open(f"{self.config.out_dir}/config{self.config.file_name_suffix}.toml",
                    'w') as f:
            dump(config.model_dump(), f)
