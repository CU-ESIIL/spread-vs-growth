"""Executable mathematical companion to the Fire Is Metabolic SI.

The package verifies identities and consequences of stated assumptions.  It
does not validate the empirical hypotheses that wildfire has a two-thirds
perimeter-area exponent or is metabolic in the biological sense.
"""

from .growth import analytic_area, constant_beta_area
from .geometry import right_angle_polygon
from .kinematics import boundary_area_rate

__all__ = ["analytic_area", "boundary_area_rate", "constant_beta_area", "right_angle_polygon"]

__version__ = "0.1.0"
