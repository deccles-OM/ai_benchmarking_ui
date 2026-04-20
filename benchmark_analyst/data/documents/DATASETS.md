# Benchmark Datasets Reference

## Local Datasets (in `datasets/` folder)

All local datasets are generated with realistic Ford data and include intentional data quality issues for testing purposes.

### 1. sales_data.csv (300 rows)

**Purpose**: Sales volume and revenue by model, region, and year. Used primarily in Tier 1 tasks.

**Schema**:
| Column | Type | Description | Sample |
|--------|------|-------------|--------|
| model | string | Vehicle model | F150, Escape, Bronco |
| region | string | Geographic region | US, EU, Asia, Canada |
| units_sold | integer | Number of units sold | 15,000 - 120,000 |
| year | integer | Calendar year | 2022, 2023, 2024 |
| revenue_millions | float | Revenue in millions USD | 0.5 - 7.8 |

**Data Characteristics**:
- 10 models × 10 regions × 3 years = 300 rows
- No missing values
- No outliers deliberately introduced
- Good for learning SQL aggregations and grouping

**Example SQL**:
```sql
SELECT model, SUM(units_sold) as total_units
FROM sales_data
WHERE year = 2024
GROUP BY model
ORDER BY total_units DESC;
```

---

### 2. warranty_claims.csv (1,128 rows)

**Purpose**: Warranty/claim records with data quality issues. Used in Levels 2 (Cleaning), 16 (Debugging), 24 (Long-Context).

**Schema**:
| Column | Type | Description | Issues |
|--------|------|-------------|--------|
| claim_id | integer | Unique claim identifier | None |
| model | string | Vehicle model | None |
| dealer | string | Dealer code (D1-D50) | D14 has 2-3x more claims |
| mileage | string/integer | Vehicle mileage at claim | ~5% missing (NA) |
| repair_cost | integer | Cost of repair in USD | ~3% negative values |
| failure_code | string | OBD-II error code | Valid codes (P0420, etc) |
| claim_date | date | Date of claim | All dates within last year |

**Data Characteristics**:
- 1,128 total claims across 10 models
- Uneven distribution: some models have higher claim rates
- Dealer D14 has ~40 claims (normal: 10-20) - anomaly detection test
- Missing values in mileage field (5%)
- Negative repair costs for data quality testing (3%)
- Useful for handling real-world messy data

**Anomalies for Testing**:
```sql
-- Most dealers have 10-20 claims; D14 has ~40 (anomaly)
SELECT dealer, COUNT(*) as claim_count
FROM warranty_claims
GROUP BY dealer
ORDER BY claim_count DESC
LIMIT 5;
-- Result: D14 stands out significantly

-- Find negative repair costs (data quality issue)
SELECT COUNT(*) FROM warranty_claims
WHERE repair_cost < 0;
-- Result: ~30-40 records with negative values

-- Find missing mileage values
SELECT COUNT(*) FROM warranty_claims
WHERE mileage = 'NA' OR mileage IS NULL;
-- Result: ~55 records missing
```

**Example SQL**:
```sql
-- Find data quality issues
SELECT 
    COUNT(*) as total_claims,
    COUNT(CASE WHEN mileage = 'NA' THEN 1 END) as missing_mileage,
    COUNT(CASE WHEN repair_cost < 0 THEN 1 END) as negative_costs,
    AVG(CAST(repair_cost as FLOAT)) as avg_repair_cost
FROM warranty_claims
WHERE repair_cost > 0;
```

---

### 3. vehicle_telemetry.csv (547 rows)

**Purpose**: Time-series vehicle sensor data. Used in Levels 3 (EDA), 17 (Performance), 25 (Sustained Performance).

**Schema**:
| Column | Type | Description | Sample Values |
|--------|------|-------------|----------------|
| vehicle_id | string | Unique vehicle identifier | VEH000001-VEH000100 |
| timestamp | datetime | Reading timestamp (UTC) | 2024-02-XX HH:MM:SS |
| engine_temp_c | integer | Engine temperature Celsius | 80-140 (anomalies >110) |
| rpm | integer | Engine RPM | 600-7000 |
| fuel_consumption_l_100km | float | Fuel efficiency | 6.0-14.0 |
| battery_voltage | float | Battery voltage | 12.0-14.5 |
| mileage_km | integer | Cumulative mileage | 10,000-500,000 |

**Data Characteristics**:
- 100 vehicles, 5-7 readings per vehicle over 30 days
- 547 total records
- ~10% of readings have anomalies (overtemp events)
- Time-series data for trend analysis
- Good for time-windowed aggregations

**Anomalies for Testing**:
```sql
-- Find temperature anomalies (engine overtemp)
SELECT COUNT(*) FROM vehicle_telemetry
WHERE engine_temp_c > 110;
-- Result: ~50-60 anomalies

-- Group into normal/elevated/critical status
SELECT
    CASE 
        WHEN engine_temp_c > 115 THEN 'CRITICAL'
        WHEN engine_temp_c > 110 THEN 'ELEVATED'
        ELSE 'NORMAL'
    END as temp_status,
    COUNT(*) as count
FROM vehicle_telemetry
GROUP BY temp_status;
```

**Example SQL**:
```sql
-- Find vehicles with temperature issues
WITH temp_stats AS (
    SELECT
        vehicle_id,
        AVG(engine_temp_c) as avg_temp,
        MAX(engine_temp_c) as max_temp,
        COUNT(*) as readings
    FROM vehicle_telemetry
    GROUP BY vehicle_id
)
SELECT * FROM temp_stats
WHERE max_temp > 105
ORDER BY max_temp DESC;
```

---

### 4. dealer_claims.csv (533 rows)

**Purpose**: Dealer-level claim activity and reimbursement. Used in Levels 6 (Business), 24 (Long-Context).

**Schema**:
| Column | Type | Description | Sample |
|--------|------|-------------|--------|
| claim_id | integer | Unique claim identifier | 1-533 |
| dealer | string | Dealer code | D1-D50 |
| amount | integer | Claim amount in USD | 500-5,000 |
| claim_type | string | Type of claim | Warranty, Recall, Service Bulletin, Field Action, Customer Paid |
| claim_date | date | Date of claim | Within last year |
| status | string | Claim status | Approved, Pending, Denied, Paid |

**Data Characteristics**:
- 533 claims across 50 dealers
- Normal dealers: 5-15 claims
- Problem dealers (D14, D25, D38): 25-40 claims each
- Mix of claim types for classification tasks
- Status distribution for workflow analysis

**Anomalies for Testing**:
```sql
-- Identify problematic dealers (outliers)
SELECT dealer, COUNT(*) as claim_count, AVG(amount) as avg_amount
FROM dealer_claims
GROUP BY dealer
HAVING COUNT(*) > 20
ORDER BY claim_count DESC;
-- Result: D14, D25, D38 are outliers (25-40 vs typical 5-15)

-- Status breakdown by dealer
SELECT dealer, status, COUNT(*) 
FROM dealer_claims
WHERE dealer IN ('D14', 'D25')
GROUP BY dealer, status;
```

**Example SQL**:
```sql
-- Business KPI: Claim efficiency by dealer
SELECT
    dealer,
    COUNT(*) as total_claims,
    SUM(amount) as total_claimed,
    AVG(amount) as avg_claim,
    COUNT(CASE WHEN status = 'Approved' THEN 1 END) as approved,
    ROUND(100.0 * COUNT(CASE WHEN status = 'Approved' THEN 1 END) / COUNT(*), 1) as approval_rate
FROM dealer_claims
GROUP BY dealer
ORDER BY approval_rate DESC;
```

---

## BigQuery Production Datasets (Real Ford Data)

For **Level 24: Long-Context Handling** stress testing, use real Ford production data in BigQuery:

```
Project: prj-eucxipa-d
Dataset: eucx_medallia
Table:   vehicle_data_save (210 MILLION rows)
```

### vehicle_data_save Schema

**Key Columns** (210M vehicle records):

| Column | Type | Description | Sample Values |
|--------|------|-------------|----------------|
| country_code | STRING | Geographic region | US, EU, JP, CA, etc |
| vin | STRING | Vehicle Identification Number | UNIQUE identifier |
| vehicle_make | STRING | Manufacturer | Ford, Lincoln, etc |
| veh_brand_c | STRING | Brand code | Internal brand classification |
| veh_description | STRING | Vehicle description | F-150, Mustang, Escape, etc |
| vehicle_type_description | STRING | Vehicle class | Truck, SUV, Sedan, etc |
| build_date | DATE | Manufacturing date | 2020-01-15, etc |
| veh_build_year | INTEGER | Build year | 2015-2024 |
| engine_type | STRING | Engine category | Gasoline, Diesel, Hybrid, Electric |
| engine_desc | STRING | Detailed engine spec | 3.5L Ecoboost V6, etc |
| veh_warr_start_date | DATE | Warranty start | 2020-01-15, null if no warranty |
| veh_warr_cancel_date | DATE | Warranty cancellation | 2023-06-20 if cancelled, null if active |
| product_type_code | STRING | Product classification | Internal code |

### Real Data Characteristics

- **210 Million rows**: Full global Ford vehicle inventory
- **Multiple countries**: US, EU, Japan, Canada, Australia, Brazil, India, Mexico, UK
- **All vehicle types**: Trucks, SUVs, sedans, crossovers
- **Multiple engine types**: Gasoline, Diesel, Hybrid, Electric
- **Warranty coverage**: Mix of active, expired, cancelled warranties
- **Build years**: 2015-2024 (10 years of data)
- **Production-scale**: Memory constraints prevent loading entire dataset
- **Real patterns**: Geographic distribution, engine performance trends, warranty correlations

### Stress Testing Queries (Real Ford Data)

See [BIGQUERY_INTEGRATION.md](BIGQUERY_INTEGRATION.md) for complete query examples. Quick examples:

```sql
-- Pattern 1: Engine distribution by country (210M rows)
SELECT country_code, engine_type, COUNT(*) as count
FROM `prj-eucxipa-d.eucx_medallia.vehicle_data_save`
GROUP BY country_code, engine_type
HAVING COUNT(*) > 100000
ORDER BY count DESC;

-- Pattern 2: Warranty cancellation rates (analytics at scale)
SELECT 
    vehicle_make,
    engine_type,
    ROUND(100.0 * COUNT(CASE WHEN veh_warr_cancel_date IS NOT NULL THEN 1 END) /
          NULLIF(COUNT(CASE WHEN veh_warr_start_date IS NOT NULL THEN 1 END), 0), 2) as cancellation_rate
FROM `prj-eucxipa-d.eucx_medallia.vehicle_data_save`
WHERE veh_warr_start_date IS NOT NULL
GROUP BY vehicle_make, engine_type
HAVING COUNT(*) > 5000
ORDER BY cancellation_rate DESC;
```

---

## Data Generation

To regenerate the local datasets with fresh random data:

```bash
python generate_datasets.py
```

This will:
1. Create 300 sales records (10 models × 10 regions × 3 years)
2. Create 1,128 warranty claims with realistic patterns and anomalies
3. Create 547 telemetry records from 100 vehicles
4. Create 533 dealer claims with problematic dealers

All generated data uses seeded randomness (seed=42) for reproducibility.

---

## Testing Coverage

| Task Level | Primary Dataset | Secondary | Purpose |
|------------|-----------------|-----------|---------|
| **1-6** (Basics) | sales_data | warranty_claims | SQL, analysis, insights |
| **7-12** (Advanced) | warranty_claims | sales_data | Complex queries, dialects |
| **13-19** (Engineering) | dealer_claims | vehicle_telemetry | Architecture, debugging |
| **20-22** (Professional) | All local | warranty_claims | Communication, security |
| **23** (Saturation) | dealer_claims | warranty_claims | Progressive complexity |
| **24** (Long-Context) | **Ford BigQuery** (210M rows) | Local datasets | Production-scale stress |
| **25-26** (Cognitive) | warranty_claims | dealer_claims | Pattern finding |
| **27** (Writing) | All | None | Content generation |

---

## Key Statistics

```
Local Datasets Summary:
- Total Local Records: 2,508 (300 + 1,128 + 547 + 533)
- Anomalies: D14 (3× claim volume), negative costs (3%), missing mileage (5%), temp overheats (10%)
- Time Span: 30-365 days of activity
- Models: 10 (F150, Escape, Bronco, Mustang, Focus, Fusion, Explorer, EdgeSUV, Ranger, Fiesta)
- Regions: 10 (US, EU, Asia, Canada, Mexico, AU, UK, Brazil, India, Japan)
- Dealers: 50 (D1-D50, with 3 problematic outliers)

Real Ford Production Data (BigQuery):
- Total Records: 210 MILLION vehicle records
- Coverage: Global (US, EU, Asia-Pacific, Americas)
- Time Span: 10 years (2015-2024)
- Engine Types: Gasoline, Diesel, Hybrid, Electric
- Warranty Status: Active, Expired, Cancelled
- Effective for stress testing and production-scale pattern discovery
```
