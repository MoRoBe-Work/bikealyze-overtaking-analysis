# ruff does not understand the typer arguments and complains about unused parameters.
# ruff: noqa: ARG001
"""
CLI for analyzing overtaking scenarios in trajectories based on sensor bike data.

This module provides a command-line interface to access the overtaking analysis
functionality from the shell. It allows users to configure and run the
OvertakingAnalyzer with various options including logging, data loading,
bicycle polygon, SSM calculation, and output settings.
"""
import logging
from sys import stdout

import configuration
import toml
import typer
from overtaking_analyzer import OvertakingAnalyzer


def check_configs(configs: configuration.AnalyzerConfig,
                    logger: logging.Logger) -> None:
    """
    Check the configuration for any potential issues and logs warnings if necessary.

    Parameters
    ----------
    config : AnalyzerConfig
        The configuration to check.
    logger : logging.Logger
        The logger to use for logging warnings.
    """
    if configs.bike_pol_conf.fan_width > 16.0:
        logger.warning(f"Very large fan width {configs.bike_pol_conf.fan_width} m set.")


    x, y, pos = configs.bike_conf.x, configs.bike_conf.y, configs.bike_conf.pos
    if x < 1 or x > 2.5 or y < 0.5 or y > 1.0 or abs(pos) > 0.5 * x:
        logger.warning(f"Unusual bicycle dimensions set: x={x}, y={y}, pos={pos}. "
                        "Ensure these values are appropriate for your analysis.")

analyzer = typer.Typer(help="CLI for analyzing overtaking scenarios in trajectories "
                        "based on nexus data.")

def main() -> None:
    """Entry point for the overtaking analysis CLI."""
    analyzer()

@analyzer.command()
def analyze(
    ctx: typer.Context,
    # Logging options
    logging_level: str | None = typer.Option(
        default=configuration.LoggingConfig.model_fields['logging_level'].default,
        help=configuration.LoggingConfig.model_fields['logging_level'].description),
    cons_log: bool = typer.Option(
        default=configuration.LoggingConfig.model_fields['cons_log'].default,
        help=configuration.LoggingConfig.model_fields['cons_log'].description),
    logfile: str | None = typer.Option(None,
        help=configuration.LoggingConfig.model_fields['logfile'].description),

    # Data Loader options
    trajectory_file: str | None = typer.Option(None,
        help=configuration.DataLoaderConfig.model_fields['trajectory_file'].description),

    # Trajectory Handler options

    # Bicycle Polygon options
    fan_width: float | None = typer.Option(
        default=configuration.BicyclePolygonConfig.model_fields['fan_width'].default,
        help=configuration.BicyclePolygonConfig.model_fields['fan_width'].description),

    # SSM calculation options
    oncoming_pet_thresh: float | None = typer.Option(
        default=configuration.SSMConfig.model_fields['oncoming_pet_thresh'].default,
        help=configuration.SSMConfig.model_fields['oncoming_pet_thresh'].description),
    tsf_speed_thresh: float | None = typer.Option(
        default=configuration.SSMConfig.model_fields['tsf_speed_thresh'].default,
        help=configuration.SSMConfig.model_fields['tsf_speed_thresh'].description),

    # Process control options
    write_config: bool = typer.Option(
        default=configuration.AnalyzerConfig.model_fields['write_config'].default,
        help=configuration.AnalyzerConfig.model_fields['write_config'].description),
    epsg: str | None = typer.Option(None,
            help=configuration.AnalyzerConfig.model_fields['epsg'].description),

    # Write options
    out_dir: str | None = typer.Option(None,
        help=configuration.WriterConfig.model_fields['out_dir'].description),
    file_name_suffix: str | None = typer.Option(None,
        help=configuration.WriterConfig.model_fields['file_name_suffix'].description),


    # config file
    config_file: str | None = typer.Option(None, help="Path to a TOML config file"),
) -> None:
    """
    Analyze overtaking and oncoming traffic based on the provided configuration.

    This function sets up logging, loads the configuration from a TOML file if provided,
    """
    ## Set up logging
    log_handlers = []

    # Determine logging level and logfile from config or defaults
    # Necessary because we want to set up logging before loading the config file
    if logging_level is None:
        numeric_logging_level = (configuration.LoggingConfig
                                    .model_fields["logging_level"].default)
    else:
        numeric_logging_level = logging.getLevelName(logging_level.upper())
        if not isinstance(numeric_logging_level, int):
            raise ValueError(f"Invalid logging level: {logging_level}")
        # Slightly hacky, but easiest way to set the parsed logging level for merging.
        if ctx is None:
            raise ValueError("Context not properly initialized by typer.")
        ctx.params["logging_level"] = numeric_logging_level

    if cons_log:
        log_handlers.append(logging.StreamHandler(stdout))

    if logfile is not None:
        log_handlers.append(logging.FileHandler(filename=logfile))

    logging.basicConfig(
        level=numeric_logging_level,
        format="%(asctime)s, %(filename)s:%(lineno)d: %(levelname)s - %(message)s",
        handlers=log_handlers,
    )

    logger = logging.getLogger()


    config_data = {}
    if config_file:
        logger.info(f"Attempting to load configuration from {config_file}")
        config_data = toml.load(config_file)
        if not config_data:
            logger.warning(f"No configuration found in {config_file}. "
                            f"Using default values.")


    # Merge settings from the config file with command line options
    merged_config = configuration.merge_configs(file_params=config_data,
                                                cli_params=ctx.params,
                                                logger=logger)

    configs = configuration.AnalyzerConfig(**merged_config)

    # Check the configuration for any potential issues
    configs = configuration.AnalyzerConfig.model_validate(configs)
    check_configs(configs, logger)


    logger.info(f"Used configuration: \n {configs}")

    # Initialize and run the OvertakingAnalyzer with the merged configuration
    OvertakingAnalyzer(logger=logger, configs=configs).run()

if __name__ == "__main__":
    main()
