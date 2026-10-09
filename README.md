# overtaking-analysis
Analysis of overtaking manoeuvres from trajectories of detected vehicles.
Used in the paper "BikeAlyze - Understanding car-to-bicycle overtaking", 2026, by Moritz Beeking[^1][^2], Marvin Götze[^1], Hannah Wies[^1], Markus Steinmaßl[^1], Karl Rehrl[^1], Julian Kooij[^2] and Holger Caesar[^2].
The corresponding data is available at https://osf.io/46fch/
The code in this repository was written by Moritz Beeking and Marvin Götze while employed at Salzburg Research.
It's published under the Apache 2.0 License.
This software is provided “as is,” without warranties or conditions of any kind, express or implied, and comes with no guarantee of correctness, fitness for a particular purpose, security, or suitability for any use.

[^1]: Salzburg Research
[^2]: TU Delft

## Installation
We recommend using a virtual environment for this.
In the repository root directory run `pip install .`.
Using pip's `-e` flag, you may change the code and use the new version without installation.

## Dependencies
The provided pyproject.toml lists the required dependencies.
The most relevant ones are geopandas for everything geocoordinate-related,
pandas for general data handling,
numpy for numerical computations,
and shapely for geometric calculations.
Please note that GeoPandas depends on the C-Libraries GEOS, PROJ and GDAL.
Normally, packaged versions of these should be contained within the wheels of its python dependencies.
However, on some systems, manual installation of some of these libraries may be required.
See GeoPandas installation instructions for further details.

## Usage
The analysis is normally called via its command line interface (CLI).
To run the analysis, using the terminal of your choice switch into the `src/overtaking-analysis/` directory.
There, run

```bash
python overtaking_analyzer_cli.py --help
```

to get a complete list of available parameters
See the section on CLI parameters below for a concise overview of relevant parameters.

### Usage example
For minimal analysis with default values run
```bash
python overtaking_analyzer_cli.py --trajectory-file /path/to/trajectories.csv --out-dir /path/to/output/directory
```


## CLI parameters

The command-line interface is configured in `configuration.py` and `overtaking_analyzer_cli.py`.
Run the application with `--help` to see the complete list of options and their
data types and default values.
Some especially relevant parameters are listed below:

| Parameter | Type | Default | Comment |
| --- | --- | --- | --- |
| `--help` | - | - | Print a complete list of available CLI parameters |
| `--logging-level` | `str` | WARNING | Set to INFO for additional progress information |
| `--config-file` | `str` | - | Path to a config stored in a config `.toml` file. May be used to set parameters not accessible through the CLI, like the bicycle dimensions. By default, every run writes the used config to a file which can be used as a template for creating your own configuration. |
| `--trajectory-file` | `str` | None | Required. Path to an input `.csv`. Expected columns are described below. |
| `--fan-width` | float | 16.0 | Width of the following zone in meters at its end 20m behind the bicycle. |
| `--oncoming-pet-thresh` | `float` | 3.0 | PET threshold in seconds to consider an overtaking maneuver to be influenced by oncoming traffic |
| `--tsf-speed-thresh` | `float` | 4.0 | Speed threshold for a vehicle in the following zone to accumulate time spent following. Measured in m/s |
| `--out-dir` | `str` | - | Path to directory where analysis configuration and results are saved. |
| `--file-name-suffix` | `str` | - | Suffix to append to configuration and result files to identify analysis runs. |

## Expected input format

The CLI expects the `--trajectory-file` parameter to be set to the path of a `.csv` file containing the trajectories to be analyzed.
Each row represents one observed vehicle in one frame.
The required columns and data types are listed in the table below:

| Name | Type | Comment |
| --- | --- | --- |
| `scene` | `str` | Unique identifier for each scene |
| `frame` | `int` | Continuous frame numbering per scene |
| `timestamp` | `int` | Timestamp in milliseconds |
| `coord_bike` | `WKT` | Position of the sensor bicycle as a WKT `POINT` geometry in the coordinate reference system specified by `--epsg` |
| `theta` | `float` | Riding direction of the sensor bicycle, measured in degrees counter-clockwise from east |
| `v_bike` | `float` | Riding speed of the sensor bicycle, measured in m/s |
| `id` | `int` | ID of the observed vehicle. Needs to be unique per scene |
| `position_x` | `float` | x-position of the vehicle in the local coordinate frame of the sensor bicycle |
| `position_y` | `float` | y-position of the vehicle in the local coordinate frame of the sensor bicycle |
| `scale_x` | `float` | Length of the vehicle in meters|
| `scale_y` | `float` | Width of the vehicle in meters|
| `rotation_z` | `float` | Rotation of the vehicle around its' vertical axis, also known as yaw angle |

The bike coordinates at the time of recording a frame are expected in [well-known text (WKT)](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry) format
The coordinate system the latitude and longitude of the sensor bicycle are measured in is controlled via the `--epsg` CLI parameter.
Local position and size of vehicles are measured in meters.
Rotation of vehicles is measured in radians and may be positive or negative.

## Provided output format

Analysis results are stored in a `.csv` file.
The input columns are preserved to keep additional information and for repeatedly running the analysis.
Additionally, the following columns are created:

| Name | Type | Column |
| --- | --- | --- |
| `traj_id` | `str` | Concatenation of scene and id to uniquely identify trajectories |
| `lateral_clearance` | `float` | Lateral clearance, present for all rows where a vehicle was to the left of the sensor bicycle |
| `longitudinal_clearance_back` | `float` | Longitudinal clearance while a vehicle is behind the sensor bicycle and on a collision course towards it |
| `rel_v_car` | `float` | Speed of a vehicle relative to the sensor bicycle in km/h |
| `maneuver` | `str` | Detected maneuver of a trajectory |
| `phase` | `str` | Phase of the detected maneuver the vehicle is in |
| `with_oncoming` | `bool` | Only present for overtaking maneuvers. Whether the maneuver was influenced by oncoming traffic according to the configured oncoming PET threshold |
| `tsf` | `float` | Time the vehicle has been within the following zone and below the following threshold. Both configurable via CLI parameters. |
| `ttc` | `float` | Time to collision, present whenever a vehicle is on a collision course towards the bicycle |

Again, all distances are in meters.
Times are measured in seconds.
The relative velocity of vehicles is measured in km/h.
Please refer to the paper for definitions of maneuvers, papers, and surrogate safety measure calculations.

## Components
| Name | Purpose |
|---|---|
| `overtaking_analyzer_cli` | CLI to control and run the trajectory analysis. |
| `configuration` | `typer` configurations to check and store parameters. |
| `utils/bicycle` | Geometric definitions of the bike and the surrounding zones. |
| `overtaking_analyzer` | Call the individual modules in correct order. |
| `data_loader` | Load data either from `json` files produced by the tracker or precomputed trajectories in `csv` format. |
| `trajectory_handler` | Prepare trajectories for analysis: create 2D bounding boxes, calculate distances and velocities, and detect manoeuvre types. |
| `phase_detector` | Detect the different phases of overtaking manoeuvres. |
| `ssm_calculator` | Calculate SSMs: minimal clearances, TTC, and TSF. |
| `writer` | Write analysis results to `csv` files. |

## Citation
If you use this repository in your work, please cite our corresponding paper:

"BikeAlyze - Understanding car-to-bicycle overtaking", 2026, Moritz Beeking, Marvin Götze, Hannah Wies, Markus Steinmaßl, Karl Rehrl, Julian Kooij and Holger Caesar


