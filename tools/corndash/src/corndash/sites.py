"""Site definitions for the dashboard."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Site:
    code: str
    name: str
    latitude: float
    longitude: float
    elevation_m: int
    timezone: str
    nearest_asos: str  # IEM ASOS station ID for observational backup
    description: str


SITES: dict[str, Site] = {
    "pds": Site(
        code="pds",
        name="Prairie du Sac (DFRC)",
        latitude=43.347,
        longitude=-89.703,
        elevation_m=232,
        timezone="America/Chicago",
        # KY01 = Sauk-Prairie airport AWOS, ~5 km from DFRC fields.
        # KMSN = Madison Dane Co Regional, ~33 km SE, used if KY01 has gaps.
        nearest_asos="KY01",
        description="US Dairy Forage Research Center farm. Primary site.",
    ),
    "arl": Site(
        code="arl",
        name="Arlington ARS",
        latitude=43.302,
        longitude=-89.350,
        elevation_m=320,
        timezone="America/Chicago",
        nearest_asos="KMSN",
        description="UW Arlington Agricultural Research Station.",
    ),
    "msh": Site(
        code="msh",
        name="Marshfield ARS",
        latitude=44.642,
        longitude=-90.135,
        elevation_m=389,
        timezone="America/Chicago",
        nearest_asos="KMFI",
        description="UW Marshfield Agricultural Research Station.",
    ),
}


def get(code: str) -> Site:
    return SITES[code]
