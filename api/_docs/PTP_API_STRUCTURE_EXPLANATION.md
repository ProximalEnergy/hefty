# PTP API Structure Explanation

## Overview

The PowerTools Platform (PTP) API is a comprehensive energy market data platform that provides access to ERCOT (Electric Reliability Council of Texas) market data. The API follows a hierarchical structure: **Markets → Endpoints → Elements → Data Points**.

## API Architecture

### Base URL

- **Production**: `https://api.ptp.energy/ptp`

### Authentication

The API supports two authentication methods:

1. **Basic Auth**: Username:password base64 encoded
2. **Bearer Token**: JWT token obtained from `/authentication/token` (valid for 24 hours)

### Rate Limiting

- Sliding window based rate limiting per user
- Average of more than 1 call per second results in 429 Too Many Requests

## API Structure Hierarchy

```
Markets
  └── Endpoints (Data Sets)
      └── Elements (Identifiers/Resources)
          └── Data Points (Metrics/Fields)
              └── Values (Time-series data)
```

## Markets

The API has **2 markets**:

### 1. ERCOTNodal

The main ERCOT market with **85 endpoints** covering:

- Market submissions (bids, offers, operating plans)
- Settlement data (day-ahead, real-time, charges)
- Performance metrics (generator, load, controllable load)
- Market prices and awards
- DART (Day-Ahead Real-Time) energy details
- Financial hedges and transactions

### 2. Operations

Market for operational data with **4 endpoints**:

- `Outage-Ticket-Data-ERCOT` - Outage ticket data
- `Test-Ticket-Data-ERCOT` - Test ticket data
- `Outage-Summary` - Outage summaries
- `Outage-Scheduler-Availability` - Outage scheduler availability

## Endpoint Types

### Submission Endpoints

These represent data that can be **submitted** to ERCOT:

- `Submissions-Current-Operating-Plan` - Current operating plans (COP)
- `Submissions-Telemetered-Current-Operating-Plan` - Telemetered COP
- `Submissions-DA-Energy-Bid` - Day-ahead energy bids
- `Submissions-DA-Energy-Only-Offer` - Day-ahead energy-only offers
- `Submissions-Availability-Plan` - Availability plans
- `Submissions-AS-Offer-DA` - Ancillary services offers (day-ahead)
- `Submissions-AS-Offer-RT` - Ancillary services offers (real-time)
- `Submissions-Three-Part-Offer-DA` - Three-part offers (day-ahead)
- `Submissions-Three-Part-Offer-RT` - Three-part offers (real-time)
- `Submissions-Output-Schedule` - Output schedules
- `Submissions-Self-Schedule` - Self-schedules
- `Submissions-PTP-Bid` - PTP bids
- `Submissions-RTM-Energy-Bid` - Real-time market energy bids

### Settlement Endpoints

These represent **settled** market data:

- `Settlement-Charges` - Settlement charges
- `Settlement-Charge-Details` - Detailed settlement charges
- `Day-Ahead-Settlement-Amounts` - Day-ahead settlement amounts
- `Real-Time-Settlement-Amounts` - Real-time settlement amounts
- `Settlement-Summary` - Settlement summaries
- `Settlement-Charges-Sequenced` - Sequenced settlement charges

### Performance Endpoints

These represent **performance metrics**:

- `Generator-Performance` - Generator performance metrics
- `Load-Performance` - Load performance metrics
- `Controllable-Load-Performance` - Controllable load performance

### Market Data Endpoints

These represent **market-wide** data:

- `Market-Prices` - Market prices
- `ERCOT-Statement-Values` - ERCOT statement values
- `Market-Settlement-Values` - Market settlement values
- `System_Load_Data` - System load data
- `System_Wind_Data` - System wind data
- `System-Solar-Data` - System solar data

### Analysis Endpoints

These represent **analytical** data:

- `DART-Energy-Details` - DART energy details
- `Configuration-Awards` - Configuration awards
- `Real-Time-Unit-Position` - Real-time unit positions
- `MktInput-5Min` - 5-minute market inputs
- `Customer_Position` - Customer positions
- `Bilateral-Transaction-Details` - Bilateral transaction details

## Data Point Types

Each endpoint has **data points** (fields/metrics) with different types:

1. **Input** - Accepts input from external sources
2. **Calculated** - Read-only calculated data
3. **Meta** - Long-standing information (e.g., IDs, names)
4. **Expression** - Calculated expressions
5. **Aggregate** - Aggregated values
6. **DimensionFilter** - Filtered by dimensions
7. **ScopedExpression** - Scoped expressions
8. **CollectionExpression** - Collection expressions

## Data Structure

### Element Structure

Each element (resource/identifier) has:

- `identifier` - Unique identifier (UUID)
- `element` - Friendly name
- `definition` - Element definition type (e.g., "Generator", "Entity", "Load")
- `parent` - Parent element name
- `parentIdentifier` - Parent element identifier
- `parentDefinition` - Parent element definition
- `goLiveDate` - When element became active
- `expirationDate` - When element expires
- `dataPoints` - Array of data points

### Data Point Structure

Each data point has:

- `keyName` - Field name
- `values` - Array of time-series values
  - `intervalStartUtc` - Interval start (ISO 8601 UTC)
  - `intervalEndUtc` - Interval end (ISO 8601 UTC)
  - `data` - Array of data values
    - `value` - The actual value

## Bexar Project Information

Based on the exploration, the Bexar project has data in the following endpoints:

### Bexar Identifiers

The following identifiers are associated with Bexar in the PTP API:

#### Generator-Level Identifiers

1. **Bexar ESS ESR** (Generator)

   - **Identifier**: `53db134c-05a9-4091-a49d-91c65b9e32df`
   - **Definition**: Generator
   - **Usage**: Generator performance metrics, real-time unit positions

2. **BEXAR_ES_ESR1** (Generator Configuration)
   - **Identifier**: `01ada09d-853c-47c9-8b49-dff77388e37c`
   - **Definition**: Generator Configuration
   - **Resource_ID**: `BEXAR_ES_ESR1`
   - **Usage**: COP submissions, generator configuration data

#### Entity-Level Identifiers

3. **Bexar ESS LLC** (Entity)

   - **Identifier**: `23dd0644-1056-4308-ad82-af0a6a12d5ac`
   - **Definition**: Entity
   - **Usage**: Settlement data, DART energy details, entity-level operations

4. **Bexar ESS - ESR** (Entity)

   - **Identifier**: `52b81dd4-c81b-4c2d-8742-058389691c2a`
   - **Definition**: Entity
   - **Usage**: Entity-level settlement and operational data

5. **Bexar - Customer Optimization** (Entity)

   - **Identifier**: `f01017f3-c682-45e1-a81a-8710d56a6c1e`
   - **Definition**: Entity
   - **Usage**: Customer position and optimization data

6. **Bexar BESS** (Entity)

   - **Identifier**: `c9e0c683-135a-4bbb-8ab3-e80f28ed5a96`
   - **Definition**: Entity
   - **Usage**: Battery Energy Storage System entity data

7. **Bexar BESS - Gen** (Entity)

   - **Identifier**: `ccfc6de6-43c8-428e-ac91-b03706a22325`
   - **Definition**: Entity
   - **Usage**: Generation-related entity data

8. **Bexar BESS - CLR** (Entity)
   - **Identifier**: `c67f3121-0f5d-42f1-a465-ff3eb71956b8`
   - **Definition**: Entity
   - **Usage**: Controllable Load Resource entity data

### Key Identifiers Summary

- **Primary Generator ID**: `53db134c-05a9-4091-a49d-91c65b9e32df` (Bexar ESS ESR)
- **Primary Entity ID**: `23dd0644-1056-4308-ad82-af0a6a12d5ac` (Bexar ESS LLC)
- **COP Identifier**: `01ada09d-853c-47c9-8b49-dff77388e37c` (BEXAR_ES_ESR1)
- **Resource ID**: `BEXAR_ES_ESR1`

### Endpoints with Bexar Data

#### 1. **Generator-Performance**

- **Element**: Bexar ESS ESR
- **Data Points**:
  - `Telemetered_LSL_5_Min` - Telemetered Low Sustained Limit (5-min)
  - `Telemetered_HSL_5_Min` - Telemetered High Sustained Limit (5-min)
  - `Telemetered_Generation_15_Min` - Telemetered generation (15-min)
  - `Predictive_HSL_15_Min` - Predictive High Sustained Limit (15-min)
  - `Predictive_LSL_15_Min` - Predictive Low Sustained Limit (15-min)

#### 2. **Real-Time-Unit-Position**

- **Element**: Bexar ESS ESR
- **Data Points**:
  - `GEN_LSL` - Generator Low Sustained Limit
  - `GEN_HSL` - Generator High Sustained Limit
  - `GEN_Production` - Generator production
  - `GEN_RT_Status` - Real-time status (e.g., "ON")

#### 3. **MktInput-5Min**

- **Element**: Bexar ESS ESR
- **Data Points**:
  - `Resource_ID` - Resource identifier ("BEXAR_ES_ESR1")

#### 4. **DART-Energy-Details**

- **Element**: Bexar ESS LLC
- **Data Points**:
  - `GEN_MWH_INT` - Generation MWh (interval)
  - `GEN_MWH_HRLY` - Generation MWh (hourly)
  - `EOO_DA_SPP` - Energy Only Offer Day-Ahead Settlement Point Price
  - `Generation_Avg_Price` - Generation average price
  - `DAEPAMT_DAEBID` - Day-Ahead Energy Payment Amount
  - `DAEBID_DA_SPP` - Day-Ahead Energy Bid Settlement Point Price
  - `RTEIAMT` - Real-Time Energy Imbalance Amount
  - And more...

#### 5. **Day-Ahead-Settlement-Amounts**

- **Element**: Bexar ESS - ESR
- **Data Points**:
  - `DAESAMT` - Day-Ahead Energy Settlement Amount
  - `DAESAMT_Daily` - Day-Ahead Energy Settlement Amount (daily)

#### 6. **Real-Time-Settlement-Amounts**

- **Element**: Bexar ESS LLC
- **Data Points**:
  - `BPDAMT` - Base Point Deviation Amount
  - `NSFQAMT` - Non-Spin Frequency Quality Amount
  - `LAASIRNAMT` - Load Ancillary Service Imbalance Revenue Net Amount
  - `ECRFQAMT` - Emergency Contingency Reserve Frequency Quality Amount
  - `LABPDAMT` - Load Ancillary Base Point Deviation Amount
  - And 96 more settlement-related fields

#### 7. **Settlement-Charges**

- **Element**: Bexar ESS LLC
- **Data Points**: 118 settlement charge fields

#### 8. **Settlement-Charge-Details**

- **Element**: Bexar ESS LLC
- **Data Points**: 114 detailed settlement charge fields

#### 9. **Settlement-Charges-Sequenced**

- **Element**: Bexar ESS LLC
- **Data Points**: 136 sequenced settlement charge fields

#### 10. **Configuration-Awards**

- **Element**: BEXAR_ES_ESR1
- **Data Points**:
  - `DA_Energy_Awards` - Day-Ahead Energy Awards

#### 11. **Customer_Position**

- **Element**: Bexar ESS LLC
- **Data Points**: 12 customer position fields

#### 12. **Bilateral-Transaction-Details**

- **Element**: Bexar ESS LLC
- **Data Points**: 26 bilateral transaction fields

#### 13. **EnergySettlement**

- **Element**: Bexar ESS LLC
- **Data Points**: 6 energy settlement fields

#### 14. **Day_Ahead_Daily_Settlement**

- **Element**: Bexar ESS LLC
- **Data Points**: 15 day-ahead daily settlement fields

#### 15. **Estimated-Settlement-Amounts**

- **Element**: Bexar ESS LLC
- **Data Points**: 102 estimated settlement amount fields

#### 16. **BPDAMT-Summary**

- **Element**: Bexar ESS LLC
- **Data Points**: 18 Base Point Deviation Amount summary fields

#### 17. **Submissions-Current-Operating-Plan**

- Contains COP submission data

#### 18. **Submissions-Telemetered-Current-Operating-Plan**

- Contains telemetered COP submission data

#### 19. **Submissions-DA-Energy-Bid**

- Contains day-ahead energy bid submissions

#### 20. **Submissions-DA-Energy-Only-Offer**

- Contains day-ahead energy-only offer submissions

#### 21. **Submissions-Three-Part-Offer-DA**

- Contains three-part offer (day-ahead) submissions

#### 22. **Submissions-Three-Part-Offer-RT**

- Contains three-part offer (real-time) submissions

#### 23. **Submissions-Availability-Plan**

- Contains availability plan submissions

#### 24. **Submissions-Output-Schedule**

- Contains output schedule submissions

## Key Insights

### 1. **Data Availability**

- Bexar has data across **24+ endpoints**
- Most data is available at the **Entity level** (Bexar ESS LLC) and **Generator level** (Bexar ESS ESR)
- Resource ID: **BEXAR_ES_ESR1**

### 2. **Time Granularity**

- **5-minute intervals**: Real-time unit positions, market inputs
- **15-minute intervals**: Generation performance, settlement data
- **Hourly intervals**: Some settlement amounts
- **Daily aggregates**: Daily settlement summaries

### 3. **Data Types Available**

- **Performance Metrics**: Generation, LSL/HSL, basepoints
- **Settlement Data**: Day-ahead and real-time settlement amounts
- **Market Data**: Awards, prices, bids, offers
- **Operational Data**: Status, production, consumption
- **Financial Data**: Settlement charges, transaction details

### 4. **Submission vs. Settlement**

- **Submissions**: Data submitted to ERCOT (bids, offers, plans)
- **Settlement**: Final settled amounts and charges from ERCOT

## API Endpoints (HTTP)

### Get Markets

```
GET /ptp
```

### Get Endpoints for a Market

```
GET /ptp/{market}
```

### Get Endpoint Schema

```
GET /ptp/{market}/{endpoint}
```

### Get Elements for an Endpoint

```
GET /ptp/{market}/{endpoint}/elements
Query Parameters:
  - begin: Begin date (YYYY-MM-DD) (optional)
  - end: End date (YYYY-MM-DD) (optional)
```

### Query Endpoint Data

```
GET /ptp/{market}/{endpoint}/query
Query Parameters:
  - elementIdentifiers: List of element identifiers (optional)
  - begin: Begin timestamp (ISO 8601 UTC) (optional)
  - end: End timestamp (ISO 8601 UTC) (optional)
  - environment: Environment filter (optional)
```

### Submit Data to an Endpoint

```
POST /ptp/{market}/{endpoint}/commit
Content-Type: application/json
Body: Array of element data objects
```

## Important Notes

1. **Parameter Names**: The API uses `elementIdentifiers` for query parameters. The `ptp_explorer.get_endpoint_data()` function handles this automatically.

2. **Elements Endpoint**: Many endpoints return 404 for `/elements` endpoint. This doesn't mean there's no data - you can still query the `/query` endpoint directly.

3. **Date Range Parameters**: The API uses `begin` and `end` parameters to specify date ranges for queries.

4. **Data Point Types**: Understanding the data point type helps understand whether data is:

   - **Input**: Can be submitted
   - **Calculated/Expression**: Read-only, calculated
   - **Meta**: Static metadata

5. **Interval Dates**: Some intervals use placeholder dates:

   - `1753-01-01` to `9998-12-31` - Full scope (meta data)
   - Real intervals have actual timestamps

6. **Rate Limiting**: Be mindful of rate limits when querying multiple endpoints or large time ranges (average of more than 1 call per second results in 429 errors).

7. **HATEOAS**: The `/ptp` API implements HATEOAS (Hypermedia as the Engine of Application State), meaning responses include links to related resources for easier discovery.

## Example Queries

### Get Bexar Generator Performance

**Using ptp_explorer:**

```python
data = await ptp_explorer.get_endpoint_data(
    token=token,
    market="ERCOTNodal",
    endpoint="Generator-Performance",
    elements=["53db134c-05a9-4091-a49d-91c65b9e32df"],
    begin="2025-12-24T00:00:00Z",
    end="2025-12-25T00:00:00Z",
)
```

**Note**: The `ptp_explorer.get_endpoint_data()` function automatically converts the `elements` parameter to `elementIdentifiers` internally.

**Direct API call:**

```python
import httpx

url = "https://api.ptp.energy/ptp/ERCOTNodal/Generator-Performance/query"
headers = {"Authorization": f"Bearer {token}"}
params = {
    "elementIdentifiers": ["53db134c-05a9-4091-a49d-91c65b9e32df"],
    "begin": "2025-12-24T00:00:00Z",
    "end": "2025-12-25T00:00:00Z",
}

async with httpx.AsyncClient() as client:
    response = await client.get(url, headers=headers, params=params)
    data = response.json()
```

### Get Bexar Settlement Charges

**Using ptp_explorer:**

```python
data = await ptp_explorer.get_endpoint_data(
    token=token,
    market="ERCOTNodal",
    endpoint="Settlement-Charges",
    elements=["23dd0644-1056-4308-ad82-af0a6a12d5ac"],
    begin="2025-12-23T06:00:00Z",
    end="2025-12-24T06:00:00Z",
)
```

**Direct API call:**

```python
import httpx

url = "https://api.ptp.energy/ptp/ERCOTNodal/Settlement-Charges/query"
headers = {"Authorization": f"Bearer {token}"}
params = {
    "elementIdentifiers": ["23dd0644-1056-4308-ad82-af0a6a12d5ac"],
    "begin": "2025-12-23T06:00:00Z",
    "end": "2025-12-24T06:00:00Z",
}

async with httpx.AsyncClient() as client:
    response = await client.get(url, headers=headers, params=params)
    data = response.json()
```

## Summary

The PTP API provides comprehensive access to ERCOT market data for the Bexar project, including:

- Real-time operational data (generation, status, limits)
- Market submissions (bids, offers, operating plans)
- Settlement data (charges, amounts, transactions)
- Performance metrics (generation, consumption, efficiency)
- Market data (prices, awards, positions)

The API structure is hierarchical and follows RESTful principles, making it easy to navigate from markets → endpoints → elements → data points → values.
