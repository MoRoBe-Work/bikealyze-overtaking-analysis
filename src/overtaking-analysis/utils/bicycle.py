"""Define Bicycle and adjacent polygons for overtaking analysis."""
from logging import Logger

import shapely as shp

from configuration import BicycleConfig, BicyclePolygonConfig


class Bicycle:
    """Define base bicycle."""

    def __init__(
        self,
        logger: Logger | None= None,
        bike_conf: BicycleConfig | None = None,
    ) -> None:
        """
        Init Bicycle object.

        Default values for parameters may be found in the configuration.

        Parameters
        ----------
        logger: Logger
            Logger object for logging messages.
        bike_conf: BicycleConfig
            Configuration object containing bicycle parameters.

        Returns
        -------
        Bicycle
            Bicycle object with attributes defined by the provided configuration.
        """
        if logger is None or bike_conf is None:
            raise ValueError("Logger and bike_conf must be provided.")

        self.logger = logger

        self.x, self.y, self.pos = bike_conf.x, bike_conf.y, bike_conf.pos

        logger.info(f"Initializing Bicycle object with length {self.x}m,"
                    f" width {self.y}m and centered around ({self.pos}, 0, 0).")

        if self.x * self.y == 0:
            self.logger.warning("Bicycle set to have zero area.")

        self.pol = shp.Polygon(
            [
                (self.pos - self.x / 2, -self.y / 2),
                (self.pos - self.x / 2, self.y / 2),
                (self.pos + self.x / 2, self.y / 2),
                (self.pos + self.x / 2, -self.y / 2),
            ]
        )

        # Set maximum extensions along the coordinate axis
        self.min_x = min(self.pol.exterior.xy[0])
        self.max_x = max(self.pol.exterior.xy[0])
        self.min_y = min(self.pol.exterior.xy[1])
        self.max_y = max(self.pol.exterior.xy[1])


class OvertakenBicycle(Bicycle):
    """Bicycle definition for overtaking analysis."""

    def __init__(
        self,
        logger: Logger | None= None,
        bike_conf: BicycleConfig | None = None,
        bike_pol_conf: BicyclePolygonConfig | None = None,
    ) -> None:
        """
        Init OvertakenBicycle a bicycle with added polygons for analysis.

        by adding zones around it useful for
        the analysis of overtaking maneuvers.
        Default values for parameters adhere to RADBEST definition of passing zone and
        fan behind and in front of bicycle.
        See Bicycle class for bicycle bounding box params.

        Parameters
        ----------
        logger: Logger
            Logger object for logging messages.
        bike_conf: BicycleConfig
            Configuration object containing base bicycle parameters.
        bike_pol_conf: BicyclePolygonConfig
            Configuration object containing polygon parameters.

        Returns
        -------
        Overtaken Bicycle object with attributes from configurations.
        """
        if logger is None or bike_conf is None or bike_pol_conf is None:
            raise ValueError("Logger, bike_conf and bike_pol_conf must be provided.")
        super().__init__(logger=logger, bike_conf=bike_conf)
        self.pass_zone_ext = bike_pol_conf.pass_zone_ext
        self.lat_pol_wid = bike_pol_conf.lat_pol_wid
        self.lon_pol_len = bike_pol_conf.lon_pol_len
        self.lon_pol_fan_wid_half = bike_pol_conf.fan_width / 2.0

        self.lon_pol_back = shp.Polygon(
            [
                (self.pos - self.lon_pol_len, -self.lon_pol_fan_wid_half),
                (self.pos, -self.y / 2),
                (self.pos, self.y / 2),
                (self.pos - self.lon_pol_len, self.lon_pol_fan_wid_half),
            ]
        )

        self.lon_pol_front = shp.Polygon(
            [
                (self.pos, -self.y / 2),
                (self.pos + self.lon_pol_len, -self.lon_pol_fan_wid_half),
                (self.pos + self.lon_pol_len, self.lon_pol_fan_wid_half),
                (self.pos, self.y / 2),
            ]
        )

        self.lat_pol = shp.Polygon(
            [
                (self.pos - self.pass_zone_ext - (self.x / 2), -self.lat_pol_wid),
                (self.pos - self.pass_zone_ext - (self.x / 2), self.lat_pol_wid),
                (self.pos + self.pass_zone_ext + (self.x / 2), self.lat_pol_wid),
                (self.pos + self.pass_zone_ext + (self.x / 2), -self.lat_pol_wid),
            ]
        )

        self.collision_course_pol = shp.Polygon(
            [
                (self.pos, -self.y / 2),
                (self.pos + 100, -self.y / 2),
                (self.pos + 100, self.y / 2),
                (self.pos, self.y / 2),
            ]
        )
