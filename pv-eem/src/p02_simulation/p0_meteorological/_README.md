# Phase 0:  Meteorological Parameters

This module is used to calculate meteorological parameters from
the measured meteorological data

## Caveats:
  * horizon loss should not be calculated because we are using
  on-site irradiance measurements.  The assumption is that
  the horizon loss is already accounted for in the shading
  of the measured sensors.

## To Do:
 * calculate t_dew from RH instead of hard-coding it
  pending acceptance into pvlib
