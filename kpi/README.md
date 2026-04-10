

## Nominal Fields

All fields should have explicit definitions. There is no "looping" over field constructions. For example,
instead of saying calculate soc for `['string', 'pcs', and 'project']`, each one would be specifically defined:
`string_soc`, `pcs_soc`, and `project_soc`. Some parts of the pipeline can feel a little verbose because of this, 
but it is worth it because:
1) There are exceptions all the time -- rather than having messy logic that parses out why one device is handled differently
   than the rest, you can easily change the one field that acts differently.
2) No magic strings -- kpis that depend on other calculations can explicitly mention the field by name with the full
   support of mypy, pylance, and other IDE tools that ensure that names remain consistent. This improves the developer's experience
   by being able to easily trace through dependencies with `⌘ + click` and to easily rename fields.

## Naming Conventions

Use singular python module names instead of plural (`util.py` instead of `utils.py`)

Class definitions should use Pascal case even when dealing with acronyms. For example, `class BessKpi` instead of 
`class BESSKPI`.

### Field Naming Guidelines

```
(Project type) + [Device Axis] + [Quantity] + (Unit) + (time axis)
```

The entire name should be snake case.
1.  **Project Type**
    Only in cases where it is ambiguous (`pv_` or `bess_` prefix).
2.  **Device Axis**
    Describes the device axis of the particular data array. 
    It can be a shortened version of the `DeviceType` enum name.
    If there is no device axis, the first term should be `project`.

    PV Device Names
    - `PV_BLOCK -> block`
    - `PV_DC_COMBINER -> combiner`
    - `PV_INVERTER -> inverter`
    - `MET_STATION -> met`
    - `TRACKER_ROW -> tracker_row`
    - `PV_INVERTER_MODULE -> inverter_module`

    BESS Device Names
    - `BESS_MV_COLLECTOR_CIRCUIT_METER -> circuit`
    - `BESS_PCS -> pcs`
    - `BESS_PCS_MODULE -> pcs_module`
    - `BESS_PCS_MODULE_GROUP -> pcs_module_group`
    - `BESS_BANK -> bank`
    - `BESS_STRING -> string`

3.  **Quantity**
    Flexible, brief, human readable description of the field. All lower case.

4.  **Unit**
    All lower case. Only needed if there is a unit.

5.  **Time Axis**
    Short version of the `base.enums.Time` enum. Only needed if there is a time axis.
   - `5m` for `TimeCoords.TIME_5MIN_UTC`
   - `d` for `TimeCoords.DATE_LOCAL`
