# PTP Endpoint Documentation

This folder used to contain detailed documentation for each PTP API endpoint, generated using the `test_ptp_endpoint.py` script. That information was too much to hold in our codebase, so it was moved to our shared Google Drive at: `Proximal/_Internal Documentation/99. Other`

## Project Identifiers (`qse_integration.project_identifier`)

In order to make the MarketPerformance page work, a project needs to have the project_identifier and provider_config columns populated.
The `project_identifier` is the UUID of the Entity ID of the project.
The `provider_config` is a json that looks like this: `{"cop_id": "f44a3487-7349-4747-8568-8a7f4b08db7e", "entity_id": "23dd0644-1056-4308-ad82-af0a6a12d5ac", "resource_id": "BEXAR_ES_ESR1", "generator_id": "53db134c-05a9-4091-a49d-91c65b9e32df", "settlement_point_id": "2ce2d65a-d432-473d-b49b-cb5bd894ccd4"}`
Each of the keys need to be present there.
You can use the `derive_ptp_identifiers.py` file to extract those.
Run:
`cd api && uv run python _scripts/tenaska_api/derive_ptp_identifiers.py <entity_id> --json`

## Documentation Status

### ERCOTNodal Market Endpoints (86 total)

#### Documented Endpoints (✅ = has documentation file)

1. ✅ **API - CLREDP** - _Not yet documented_
2. ✅ **API - GREDP** - _Not yet documented_
3. ✅ **API-Submissions-Exceptional-Fuel-Cost** - _Not yet documented_
4. ✅ **API_Trade_Volumes** - _Not yet documented_
5. ✅ **AggOutput** - _Not yet documented_
6. ✅ **BPDAMT-Summary** - `bpdamt_summary_endpoint_analysis.md`
7. ✅ **Battery-Settlement-Details** - _Not yet documented_
8. ✅ **Bilateral-Transaction-Details** - `bilateral_transaction_details_endpoint_analysis.md`
9. ✅ **Configuration-Awards** - `configuration_awards_endpoint_analysis.md`
10. ✅ **Congestion-Settlement-Data** - _Not yet documented_
11. ✅ **Controllable-Load-Data** - _Not yet documented_
12. ✅ **Controllable-Load-Performance** - _Not yet documented_
13. ✅ **Curtailment-Report** - _Not yet documented_
14. ✅ **Customer_Generation_Quantities** - _Not yet documented_
15. ✅ **Customer_LMP** - _Not yet documented_
16. ✅ **Customer_Position** - `customer_position_endpoint_analysis.md`
17. ✅ **Customer_Renewable_Data** - _Not yet documented_
18. ✅ **Customer_Wind_Data** - _Not yet documented_
19. ✅ **DART-Energy-Details** - `dart_energy_details_endpoint_analysis.md`
20. ✅ **DA_Awards_Prices_All** - _Not yet documented_
21. ✅ **DA_Wind_Optimization_Activity** - _Not yet documented_
22. ✅ **DartOptimizationReport** - _Not yet documented_
23. ✅ **Day-Ahead-Settlement-Amounts** - `day_ahead_settlement_amounts_endpoint_analysis.md` (⚠️ No data available)
24. ✅ **Day_Ahead_Daily_Settlement** - `day_ahead_daily_settlement_endpoint_analysis.md` (⚠️ No data available)
25. ✅ **ERCOT-Statement-Values** - `ercot_statement_values_endpoint_analysis.md` (✅ Updated with CSV descriptions and units)
26. ✅ **ERCOT_DA_Awards_Prices** - _Not yet documented_
27. ✅ **ERCOT_and_Third_Party_Wind_Forecast** - _Not yet documented_
28. ✅ **EnergySettlement** - `energy_settlement_endpoint_analysis.md`
29. ✅ **Estimated-Settlement-Amounts** - `estimated_settlement_amounts_endpoint_analysis.md`
30. ✅ **Financial-Hedge-Details** - _Not yet documented_
31. ✅ **Gas-Costs** - _Not yet documented_
32. ✅ **Gas_Burns** - _Not yet documented_
33. ✅ **Generator-Performance** - `generator_performance_endpoint_analysis.md`
34. ✅ **Generator-Settlement-Data** - _Not yet documented_
35. ✅ **Generator-Wind-Forecast** - _Not yet documented_
36. ✅ **Load-Meter-Data** - _Not yet documented_
37. ✅ **Load-Performance** - _Not yet documented_
38. ✅ **Load-Resource-Settlement-Data** - _Not yet documented_
39. ✅ **Load-Settlement-Data** - _Not yet documented_
40. ✅ **Market-Prices** - `market_prices_endpoint_analysis.md`
41. ✅ **Market-Settlement-Values** - `market_settlement_values_endpoint_analysis.md` (✅ Updated with CSV descriptions and units)
42. ✅ **MktInput-5Min** - `mktinput_5min_endpoint_analysis.md` (⚠️ No time-series data available)
43. ✅ **Optimization-Renewable-Forecast** - _Not yet documented_
44. ✅ **PI-Data** - _Not yet documented_
45. ✅ **PTP_Obligations** - _Not yet documented_
46. ✅ **Physical-Hedge-Details** - _Not yet documented_
47. ✅ **Real-Time-Settlement-Amounts** - `realtime_settlement_amounts_endpoint_analysis.md`
48. ✅ **Real-Time-Unit-Position** - `realtime_unit_position_endpoint_analysis.md`
49. ✅ **Real_Time_Daily_Settlement** - _Not yet documented_
50. ✅ **Renewable_Optimization_Offers** - _Not yet documented_
51. ✅ **Settlement-Charge-Details** - `settlement_charge_details_endpoint_analysis.md`
52. ✅ **Settlement-Charge-Details-Market-Versioned** - _Not yet documented_
53. ✅ **Settlement-Charges** - `settlement_charges_endpoint_analysis.md`
54. ✅ **Settlement-Charges-Market-Versioned** - _Not yet documented_
55. ✅ **Settlement-Charges-Sequenced** - `settlement_charges_sequenced_endpoint_analysis.md`
56. ✅ **Settlement-Summary** - _Not yet documented_
57. ✅ **Submissions-AS-Offer-DA** - _Not yet documented_
58. ✅ **Submissions-AS-Offer-RT** - _Not yet documented_
59. ✅ **Submissions-AS-Offers-DA-RTC** - _Not yet documented_
60. ✅ **Submissions-AS-Offers-RT-RTC** - _Not yet documented_
61. ✅ **Submissions-AS-Only-Offer** - _Not yet documented_
62. ✅ **Submissions-Availability-Plan** - `submissions_availability_plan_endpoint_analysis.md` (⚠️ No time-series data available)
63. ✅ **Submissions-Current-Operating-Plan** - `submissions_current_operating_plan_endpoint_analysis.md` (⚠️ No time-series data available)
64. ✅ **Submissions-Current-Operating-Plan-RTC** - `submissions_current_operating_plan_rtc_endpoint_analysis.md`
65. ✅ **Submissions-DA-Energy-Bid** - `submissions_da_energy_bid_endpoint_analysis.md`
66. ✅ **Submissions-DA-Energy-Only-Offer** - `submissions_da_energy_only_offer_endpoint_analysis.md`
67. ✅ **Submissions-Output-Schedule** - `submissions_output_schedule_endpoint_analysis.md` (⚠️ No time-series data available)
68. ✅ **Submissions-PTP-Bid** - _Not yet documented_
69. ✅ **Submissions-RTM-Energy-Bid** - _Not yet documented_
70. ✅ **Submissions-Self-Schedule** - _Not yet documented_
71. ✅ **Submissions-Telemetered-Current-Operating-Plan** - `submissions_telemetered_current_operating_plan_endpoint_analysis.md` (⚠️ No time-series data available)
72. ✅ **Submissions-Telemetered-Current-Operating-Plan-RTC** - `submissions_telemetered_current_operating_plan_rtc_endpoint_analysis.md`
73. ✅ **Submissions-Three-Part-Offer-DA** - `submissions_three_part_offer_da_endpoint_analysis.md`
74. ✅ **Submissions-Three-Part-Offer-RT** - `submissions_three_part_offer_rt_endpoint_analysis.md`
75. ✅ **Submitted-Generation-Split** - _Not yet documented_
76. ✅ **System-Outage-Data** - _Not yet documented_
77. ✅ **System-Solar-Data** - `system_solar_data_endpoint_analysis.md`
78. ✅ **System_AS_Capacity** - _Not yet documented_
79. ✅ **System_Load_Data** - `system_load_data_endpoint_analysis.md`
80. ✅ **System_Wind_Data** - `system_wind_data_endpoint_analysis.md`
81. ✅ **Telemeterd-Gen-Data** - _Not yet documented_
82. ✅ **Telemetered-Gen-Data** - _Not yet documented_
83. ✅ **Telemetered-Output** - _Not yet documented_
84. ✅ **Transaction-Settlement-Data** - _Not yet documented_
85. ✅ **Virtual-Settlement-Data** - _Not yet documented_
86. ✅ **Wind-Shortfall** - _Not yet documented_

### Operations Market Endpoints (4 total)

1. ✅ **Outage-Scheduler-Availability** - _Not yet documented_
2. ✅ **Outage-Summary** - _Not yet documented_
3. ✅ **Outage-Ticket-Data-ERCOT** - _Not yet documented_
4. ✅ **Test-Ticket-Data-ERCOT** - _Not yet documented_

### Summary

- **Total Endpoints**: 90 (86 ERCOTNodal + 4 Operations)
- **Documented**: 30 endpoints have documentation files
- **Remaining**: 60 endpoints need documentation

## Utilities

### PTP Acronym Lookup

The `ptp_acronym_utils.py` module provides utilities for looking up PTP acronym information from the `tenaska_acronyms_categorized.csv` file. This includes human-readable descriptions, units, granularity (in minutes), sequences, dimensions, and endpoints.

#### `tenaska_acronyms_categorized.csv`

This CSV file contains a comprehensive catalog of PTP (Power Tools Platform) acronyms used across ERCOT endpoints, with detailed metadata for each acronym. The file includes the following information:

- **Keyname**: The acronym identifier (e.g., `BLTRAMT`, `BSSAMT`)
- **Element Definition**: The entity type or definition
- **Granularity (Minutes)**: Time granularity for the data point (e.g., 5, 15, 60, 1440)
- **Sequence**: Billing sequence or versioning information (e.g., "ERCOT Billing Version", "Day-Ahead Billing Version")
- **Dimension(s)**: Additional dimensional information
- **Description**: Human-readable description of what the acronym represents
- **Endpoint**: The PTP API endpoint where this acronym appears
- **Unit**: The unit of measurement (e.g., "Amount ($)", "MW", "MWh")
- **Component_UnitType**: The component unit type classification
- **Settlement_Timing**: When settlement occurs (e.g., "DA" for Day-Ahead, "RT" for Real-Time)
- **Market_Service**: Market service category (e.g., "ECRS", "NonSpin", "RegUp", "BlackStart")
- **Payment_Charge**: Whether it's a payment or charge
- **UI_Group**: UI grouping category (e.g., "Ancillary Services", "Energy", "Fees, Admin & Other Charges")
- **UI_Subgroup**: UI subcategory for further organization
- **Is_Total**: Boolean indicating if this is a total/aggregate value

Note that some acronyms may appear multiple times in the CSV with different granularities, endpoints, or other attributes, allowing for context-specific lookups.

**Usage:**

```python
from api._scripts.tenaska_api.ptp_acronym_utils import (
    get_acronym_info,
    get_all_acronym_info,
    get_acronym_description,
    get_acronym_granularity,
    get_acronym_endpoint,
    get_acronym_unit,
    get_acronyms_by_endpoint,
    get_acronyms_by_granularity,
)

# Get information for a specific acronym
info = get_acronym_info('BLTRAMT')
print(f"{info.description} - {info.granularity_minutes} min - Unit: {info.unit}")

# Get all occurrences (some acronyms appear multiple times with different granularities/endpoints)
all_matches = get_all_acronym_info('BLTRAMT')

# Filter by endpoint
info = get_acronym_info('BLTRAMT', endpoint='Settlement-Charges-Market-Versioned')

# Get unit for an acronym
unit = get_acronym_unit('BLTRAMT', endpoint='Settlement-Charges-Market-Versioned')

# Get all acronyms for a specific endpoint
endpoint_acronyms = get_acronyms_by_endpoint('Settlement-Charges-Market-Versioned')

# Get all acronyms with a specific granularity
granularity_acronyms = get_acronyms_by_granularity(1440)
```

The module handles duplicate acronyms (same acronym can appear with different granularities/endpoints) and provides both class-based and function-based APIs for convenience.

## Process

For each endpoint:

1. Run the test script:

   ```bash
   cd mono/api
   source .venv/bin/activate
   python _scripts/tenaska_api/test_ptp_endpoint.py "Endpoint-Name" --skip-schema --skip-viewport
   ```

2. If schema information is needed, run without `--skip-schema`:

   ```bash
   python _scripts/tenaska_api/test_ptp_endpoint.py "Endpoint-Name" --skip-viewport
   ```

3. Create the markdown file in this folder following the template from `generator_performance_endpoint_analysis.md`

4. Include:
   - Endpoint details and schema information
   - Required inputs (query parameters)
   - Working identifiers for Bexar
   - Output data structure
   - All available data points from schema
   - Time range testing results
   - Example queries

5. Update this README to mark the endpoint as complete (✅)
