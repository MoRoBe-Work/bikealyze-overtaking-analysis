"""Pydantic configurations for all modules in the overtaking analysis."""
from logging import WARNING, Logger
from os import R_OK, access
from pathlib import Path

from pydantic import BaseModel, Field, model_validator, field_validator


def is_readable_csv(file_path: str | Path) -> bool:
    """
    Check if the provided file path points to a readable CSV file.

    Parameters
    ----------
    file_path : str
        The path to the file to check.

    Returns
    -------
    bool
        True if the file exists, is a file, has a .csv extension, and is readable.
        False otherwise.
    """
    p = Path(file_path)
    return (p.exists()
            and p.is_file()
            and p.suffix.lower() == ".csv"
            and access(p, R_OK))


class LoggingConfig(BaseModel):
    """
    Configuration for logging.

    This class is used to define the logging parameters for the application.
    Defaults: WARNING level, no logfile, console logging enabled.
    """

    logging_level: int = Field(WARNING, description="Logging level (DEBUG, INFO, "
                                "WARNING, ERROR, CRITICAL)")
    logfile: str | None = Field(None, description="Path to a logfile")
    cons_log: bool = Field(True, description="Whether to log to console")

    @field_validator("logging_level", mode="before")
    def parse_logging_level(cls, value: str | int) -> int:
        if isinstance(value, str):
            level = logging.getLevelName(value.upper())
            if not isinstance(level, int):
                raise ValueError(f"Invalid logging level: {value}")
            return level
        return value


class BicycleConfig(BaseModel):
    """
    Configuration of the bicycle parameters.

    Parameters of the bicycle model used in the analysis.
    Defaults:
        length/x: 1.9
        width/y: 0.7
        displacement along x-axis/pos: 0.095
    """

    x: float = Field(1.9, description="Length of the bicycle in meters")
    y: float = Field(0.7, description="Width of the bicycle in meters")
    pos: float = Field(0.095, description="Distance from center of coordinate system "
                                            "to center of bicycle in meters")

    @model_validator(mode='after')
    def validate_bike_conf(self) -> BicycleConfig:
        """
        Validate the bicycle configuration parameters.

        Ensures that the length and width of the bicycle are positive floats
        and that the position is within the bounds of the bicycle's length.
        Raises ValueError if any of these conditions are not met.
        """
        x, y, pos = self.x, self.y, self.pos
        if x <= 0:
            raise ValueError("Length of bicycle must be a positive float")
        if y <= 0:
            raise ValueError("Width of bicycle must be a positive float")
        if abs(pos) > abs(self.x) / 2:
            raise ValueError(f"Coordinate system should originate within the bicycles "
                                f"length, not at {pos}.")
        return self


class BicyclePolygonConfig(BaseModel):
    """
    Configuration of the bicycle polygon parameters.

    Extension of the polygons around the bicycle used in the analysis, all in meters.
    Defaults:
        pass_zone_ext: 0
        lat_pol_wid: 100
        lon_pol_len: 20
        fan_width: 16.0
    """

    pass_zone_ext: float = Field(0, description="Extension of the pass zone in meters")
    lat_pol_wid: float = Field(100, description="Width of the lateral polygon "
                                                    "in meters")
    lon_pol_len: float = Field(20, description="Length of the longitudinal polygon "
                                                    "in meters")
    fan_width: float = Field(16.0, description="Width of the longitudinal polygon fan "
                                                    "in meters")

    @model_validator(mode='after')
    def validate_fan_width(self) -> BicyclePolygonConfig:
        """Ensure the fan width is a positive float."""
        if self.fan_width <= 0:
            raise ValueError("Fan width must be a positive float")
        return self


class DataLoaderConfig(BaseModel):
    """
    Configuration for the data loader.

    This class is used to define the parameters for loading trajectories from file.
    """

    trajectory_file: str | None = Field(None, description="Path to a precomputed "
                                        "trajectory file to load instead of loading "
                                        "from labels")

    @property
    def valid_trajectory_file(self) -> Path:
        """Return the trajectory file as a Path object, ensuring it is not None."""
        if self.trajectory_file is None:
            raise ValueError("Trajectory file must be provided")
        return Path(self.trajectory_file)

    # Make sure either input source has been set
    @model_validator(mode='after')
    def validate_input(self) -> DataLoaderConfig:
        """
        Validate data loading configuration.

        A trajectory file path is required.
        """
        # Location is a mandatory parameter
        if self.trajectory_file is None or not is_readable_csv(self.trajectory_file):
            raise ValueError("Trajectory file must be a readable CSV file.")
        return self


class TrajectoryHandlerConfig(BaseModel):
    """
    Configuration for the trajectory handler.

    Kept as a placeholder for future trajectory handler configurations.
    """

class SSMConfig(BaseModel):
    """
    Configuration for the SSM calculation.

    Defines the TTC threshold, oncoming PET threshold, and TSF speed threshold.
    """

    oncoming_pet_thresh: float = Field(3.0,
                                        description="Time in seconds below which an "
                                        "overtaking maneuver is considered to involve "
                                        "oncoming traffic")
    tsf_speed_thresh: float = Field(4.0,
                                    description="Speed threshold in m/s above which "
                                            "time spent following is not calculated")


class WriterConfig(BaseModel):
    """
    Configuration for file writing.

    Defines the output directory, whether to write back to scene directories,
    and an optional suffix to append to output filenames.
    """

    out_dir: str | None = Field(None,
                                description="Directory where the analysis results "
                                " are saved")
    file_name_suffix: str = Field("",
                                    description="Suffix to append to output filenames "
                                    "before the file extension.")

class AnalyzerConfig(BaseModel):
    """
    Overall configuration for the overtaking analysis.

    Aggregates configurations for the individual components in order to enable
    straightforward merging of default values, values from an optional config file,
    and CLI parameters. Furthermore, enables centralized configuration validation.
    """

    bike_conf: BicycleConfig = BicycleConfig.model_construct()
    bike_pol_conf: BicyclePolygonConfig = BicyclePolygonConfig.model_construct()
    log_conf: LoggingConfig = LoggingConfig.model_construct()
    dl_conf: DataLoaderConfig = DataLoaderConfig.model_construct()
    traj_handler_conf: TrajectoryHandlerConfig = (
        TrajectoryHandlerConfig.model_construct())
    ssm_conf: SSMConfig = SSMConfig.model_construct()
    writer_conf: WriterConfig = WriterConfig.model_construct()

    # Params controlling the process
    run_analysis: bool = Field(True,
                                description="Whether to run the analysis or stop "
                                            "after parsing")
    write_raw_trajectories: bool = Field(False,
                                            description="Whether raw trajectories "
                                            "after parsing but before analysis should "
                                            "be written")
    write_config: bool = Field(True,
                                description="Whether the configuration used for the "
                                            "analysis should be written to a file")

    epsg: str = Field("EPSG:25833", description="EPSG code for the used coordinate "
                            "system. Default is UTM zone 33N (EPSG:25833), suited for "
                            "most of Austria. Use 25832 for Western Austria.")


def merge_configs(file_params: dict | None = None,
                    cli_params: dict | None = None,
                    logger: Logger | None = None) -> dict:
    """
    Merge configuration parameters from a config file and CLI) options.

    CLI parameters will override those from the file if present and not None.

    Parameters
    ----------
    file_params : dict, optional
        Dictionary containing configuration parameters loaded from a file.
        The keys should correspond to configuration sections
        (e.g., 'log_conf', 'dl_conf', etc.), and the values should be dictionaries
        of parameter names and their values.
    cli_params : dict, optional
        Dictionary containing configuration parameters provided via the CLI.
        The keys are parameter names, and the values are their corresponding values.

    Returns
    -------
    dict
        A dictionary containing the merged configuration.
        For each configuration section, parameters provided via the CLI will override
        those from the file if present and not None.
    """
    # Initialize dictionary with default values
    assert logger is not None, ("Logger must be provided for logging warnings "
                                "and errors.")
    configs = {"log_conf": {k :
                    LoggingConfig.model_fields[k].default for k in
                    set(LoggingConfig.model_fields.keys())},
                "bike_conf": {k :
                    BicycleConfig.model_fields[k].default for k in
                    set(BicycleConfig.model_fields.keys())},
                "dl_conf": {k :
                    DataLoaderConfig.model_fields[k].default for k in
                    set(DataLoaderConfig.model_fields.keys())},
                "traj_handler_conf": {k :
                    TrajectoryHandlerConfig.model_fields[k].default for k in
                    set(TrajectoryHandlerConfig.model_fields.keys())},
                "ssm_conf": {k :
                    SSMConfig.model_fields[k].default for k in
                    set(SSMConfig.model_fields.keys())},
                "writer_conf": {k :
                    WriterConfig.model_fields[k].default for k in
                    set(WriterConfig.model_fields.keys())},
                "bike_pol_conf": {k :
                    BicyclePolygonConfig.model_fields[k].default for k in
                    set(BicyclePolygonConfig.model_fields.keys())},
                "run_analysis":
                    AnalyzerConfig.model_fields["run_analysis"].default,
                "write_raw_trajectories":
                    AnalyzerConfig.model_fields["write_raw_trajectories"].default,
                "write_config":
                    AnalyzerConfig.model_fields["write_config"].default}
    for config in configs:
        # Handle nested configurations
        if isinstance(configs[config], dict):
            for param in configs[config]:
                if (cli_params is not None and
                    param in cli_params and
                    cli_params[param] is not None):
                    configs[config][param] = cli_params[param]
                    logger.debug(f"Parameter {param} in config {config} set from CLI "
                                    f"to {cli_params[param]}")
                elif (file_params is not None and
                        param in file_params and
                        file_params[param] is not None):
                    configs[config][param] = file_params[config][param]
                    logger.debug(f"Parameter {param} in config {config} set from file "
                                    f" to {file_params[config][param]}")
                else:
                    logger.debug(f"Parameter {param} in config {config} left at "
                                    f"default value {configs[config][param]}")

        # Handle base analyzer config
        else:
            if (cli_params is not None and
                config in cli_params and
                cli_params[config] is not None):
                configs[config] = cli_params[config]
                logger.debug(f"Parameter {config} set from CLI to {cli_params[config]}")
            elif (file_params is not None and
                    config in file_params and
                    file_params[config] is not None):
                configs[config] = file_params[config]
                logger.debug(f"Parameter {config} set from file to "
                                f"{file_params[config]}")
            else:
                logger.debug(f"Parameter {config} left at default value "
                                f"{configs[config]}")


    return configs
