"""Overtaking Analyzer bundling the subsequent steps of the overtaking analysis."""
from logging import Logger

from configuration import AnalyzerConfig
from data_loader import DataLoader
from phase_detector import PhaseDetector
from ssm_calculator import SSMCalculator
from trajectory_handler import TrajectoryHandler
from utils.bicycle import OvertakenBicycle
from writer import Writer


class OvertakingAnalyzer:
    """Overtaking Analyzer bundling the subsequent steps of the overtaking analysis."""

    def __init__(
        self,
        configs: AnalyzerConfig | None = None,
        logger: Logger | None = None
    ) -> None:
        """Initialize the OvertakingAnalyzer with the provided config and logger."""
        if logger is None or configs is None:
            raise ValueError("Both logger and configs must be provided.")
        assert isinstance(configs, AnalyzerConfig), (
            "Config must be an instance of AnalyzerConfig")

        self.config = configs
        self.logger = logger

        self.writer = Writer(config=configs.writer_conf, logger=self.logger)
        self.data_loader = DataLoader(logger=self.logger,
                                        config=configs.dl_conf)

        self.bike = OvertakenBicycle(logger=self.logger,
                                        bike_conf=configs.bike_conf,
                                        bike_pol_conf=configs.bike_pol_conf)

        self.trajectory_handler = TrajectoryHandler(logger=self.logger,
                                                    bike=self.bike,
                                                    config=configs.traj_handler_conf)

        self.phase_detector = PhaseDetector(logger=self.logger,
                                            bike = self.bike)

        self.ssm_calculator = SSMCalculator(logger=self.logger,
                                            config=configs.ssm_conf,
                                            bike=self.bike)

    def run(self) -> None:
        """
        Run the overtaking analysis.

        Depending on config parse the data, run the analysis, and write the results.
        """
        if self.config.write_config:
            self.logger.info("Writing configuration to disk.")
            self.writer.write_config(config=self.config)

        df = self.data_loader.load_trajectories()
        # Store the input columns to write back later
        input_cols = list(df.columns)
        # Remove the 'geometry' column.
        # This is purely a working column, the information is preserved
        # in the 'coord_bike' column.
        input_cols.remove('geometry')

        self.logger.info("Running overtaking analysis.")
        df = self.trajectory_handler.run(df=df)

        df = self.phase_detector.run(df=df)

        df = self.ssm_calculator.calculate_ssms(df=df)

        self.writer.write_trajectories(df=df,
                                        additional_columns=input_cols)

        self.logger.info("Overtaking analysis completed.")
