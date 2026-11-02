# DataLakehouse

> A reproducible bronze/silver/gold pipeline for operational analytics with DuckDB and Parquet.

[![CI](https://github.com/david2526IA/datalakehouse/actions/workflows/ci.yml/badge.svg)](https://github.com/david2526IA/datalakehouse/actions/workflows/ci.yml)
[![DuckDB](https://img.shields.io/badge/DuckDB-lakehouse-FFF000?logo=duckdb&logoColor=111827)](https://duckdb.org/)
[![Parquet](https://img.shields.io/badge/Apache%20Parquet-columnar-50ABF1)](https://parquet.apache.org/)
[![License](https://img.shields.io/badge/License-MIT-2563EB.svg)](LICENSE)

DataLakehouse turns operational order exports into a documented analytical layer. It ingests CSV, preserves the raw source, quarantines invalid records, writes clean Parquet data and publishes daily and category-level metrics in DuckDB.

## Why this is useful

Data work is valuable when a business can trust the numbers. This project makes the data-quality boundary explicit: invalid rows are kept in `rejected_orders` with an explanation instead of disappearing during cleaning. The curated layer is then ready for dashboards, notebooks or BI tools.

## Architecture

```text
CSV export
   │
   ▼
Bronze: raw_orders ──► schema contract
   │
   ├──► rejected_orders (reason retained)
   ▼
Silver: typed, clean orders ──► Parquet
   ▼
Gold: daily operations + category performance ──► DuckDB / BI
```

## Quick start

```bash
git clone https://github.com/david2526IA/datalakehouse.git
cd datalakehouse
python -m venv .venv
```

Activate the environment and run:

```bash
pip install -e ".[dev]"
datalakehouse demo --output data/orders.csv
datalakehouse run data/orders.csv --warehouse warehouse
pytest -q
```

The `warehouse/` directory contains:

- `warehouse.duckdb`: bronze, quarantine, silver and gold tables.
- `silver_orders.parquet`: clean order-level data.
- `gold_daily_operations.parquet`: dashboard-ready daily metrics.
- `run_summary.json`: lineage-friendly run statistics.

## Source contract

```csv
order_id,order_date,category,country,quantity,unit_price_eur,promised_days,delivered_days
ORD-001,2026-01-01,electronics,ES,1,199.90,2,3
```

Rows with missing identifiers/dates, invalid quantity or price, missing delivery data or duplicate IDs are quarantined. The pipeline does not silently repair source data.

## Example analytics query

```sql
SELECT category, revenue_eur, late_delivery_rate_pct
FROM gold_category_performance
ORDER BY revenue_eur DESC;
```

## Container run

```bash
docker build -t datalakehouse .
docker run --rm -v "${PWD}:/data" datalakehouse run /data/data/orders.csv --warehouse /data/warehouse
```

## Scope and roadmap

This is a local reference implementation. At larger scale the same contracts can move to object storage, an orchestrator and a distributed engine without changing the bronze/silver/gold intent.

- [ ] Partitioned Parquet by order date
- [ ] Data-quality expectations and alerting
- [ ] dbt-compatible analytical models
- [ ] S3/MinIO and object-storage adapter
- [ ] Incremental loads and lineage manifest

## License

MIT © 2026 David
