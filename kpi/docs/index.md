# KPI Pipeline Documentation

This documentation explains how KPI values move through the pipeline: from
source downloads, through cleaning and transformations, to project- and
device-level uploads.

The pages are generated from the same registry definitions used by the
pipeline, so they are intended to stay close to the executable graph. Use them
to trace which inputs a field depends on, which transform produced it, and which
domain functions provide the underlying calculation.

## Organization

- **Domain Functions**: reusable calculation helpers used throughout the
  pipeline. These pages show the Python source for transparent descriptions of
  core `xarray` operations, aggregations, and project-specific utilities.
- **Download**: source data fields loaded into the KPI pipeline, including
  sensors, device attributes, events, expected energy, and project metadata.
- **Transform**: cleaning, evaluation, and summary fields that turn downloaded
  data into daily KPI inputs.
- **KPIs**: daily project- and device-level KPI outputs, including the KPI type
  ID, unit, upload version, and source transform fields.
- **Field DAG**: Shows an interactive dependency graph of each field from data 
  download to final KPI calculation.

