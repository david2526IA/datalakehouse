"""Bronze/silver/gold local lakehouse pipeline built on DuckDB and Parquet."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

REQUIRED_COLUMNS = {"order_id", "order_date", "category", "country", "quantity", "unit_price_eur", "promised_days", "delivered_days"}


def _assert_schema(connection: duckdb.DuckDBPyConnection) -> None:
    columns = {row[0] for row in connection.execute("DESCRIBE raw_orders").fetchall()}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"Source is missing required columns: {', '.join(sorted(missing))}")


def run_pipeline(source_csv: str | Path, warehouse: str | Path) -> dict[str, object]:
    """Build bronze, silver and gold layers and return data-quality metrics.

    Invalid rows are deliberately separated in `rejected_orders`; no silent
    correction or data loss happens during the transformation.
    """
    source = Path(source_csv).resolve()
    root = Path(warehouse).resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "warehouse.duckdb"
    connection = duckdb.connect(str(database))
    try:
        source_sql = str(source).replace("'", "''")
        connection.execute(f"CREATE OR REPLACE TABLE raw_orders AS SELECT * FROM read_csv_auto('{source_sql}', header=true)")
        _assert_schema(connection)
        connection.execute(
            """
            CREATE OR REPLACE TABLE rejected_orders AS
            SELECT *,
              CASE
                WHEN order_id IS NULL OR trim(order_id) = '' THEN 'missing order_id'
                WHEN order_date IS NULL THEN 'missing order_date'
                WHEN quantity IS NULL OR quantity <= 0 THEN 'invalid quantity'
                WHEN unit_price_eur IS NULL OR unit_price_eur < 0 THEN 'invalid unit price'
                WHEN promised_days IS NULL OR delivered_days IS NULL THEN 'missing delivery data'
                ELSE 'duplicate order_id'
              END AS rejection_reason
            FROM raw_orders
            QUALIFY order_id IS NULL OR trim(order_id) = '' OR order_date IS NULL
              OR quantity IS NULL OR quantity <= 0 OR unit_price_eur IS NULL OR unit_price_eur < 0
              OR promised_days IS NULL OR delivered_days IS NULL
              OR count(*) OVER (PARTITION BY order_id) > 1
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE TABLE silver_orders AS
            SELECT
              trim(order_id) AS order_id,
              CAST(order_date AS DATE) AS order_date,
              lower(trim(category)) AS category,
              upper(trim(country)) AS country,
              CAST(quantity AS INTEGER) AS quantity,
              CAST(unit_price_eur AS DECIMAL(12,2)) AS unit_price_eur,
              CAST(quantity * unit_price_eur AS DECIMAL(14,2)) AS revenue_eur,
              CAST(promised_days AS INTEGER) AS promised_days,
              CAST(delivered_days AS INTEGER) AS delivered_days,
              delivered_days > promised_days AS delivered_late
            FROM raw_orders
            WHERE order_id IS NOT NULL AND trim(order_id) <> '' AND order_date IS NOT NULL
              AND quantity > 0 AND unit_price_eur >= 0 AND promised_days IS NOT NULL AND delivered_days IS NOT NULL
              AND order_id NOT IN (SELECT order_id FROM rejected_orders WHERE order_id IS NOT NULL)
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE TABLE gold_daily_operations AS
            SELECT order_date, count(*) AS orders, round(sum(revenue_eur), 2) AS revenue_eur,
              round(avg(revenue_eur), 2) AS average_order_value_eur,
              round(avg(CASE WHEN delivered_late THEN 1.0 ELSE 0.0 END) * 100, 2) AS late_delivery_rate_pct
            FROM silver_orders GROUP BY order_date ORDER BY order_date
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE TABLE gold_category_performance AS
            SELECT category, count(*) AS orders, round(sum(revenue_eur), 2) AS revenue_eur,
              round(avg(CASE WHEN delivered_late THEN 1.0 ELSE 0.0 END) * 100, 2) AS late_delivery_rate_pct
            FROM silver_orders GROUP BY category ORDER BY revenue_eur DESC
            """
        )
        silver_path = str(root / "silver_orders.parquet").replace("'", "''")
        gold_path = str(root / "gold_daily_operations.parquet").replace("'", "''")
        connection.execute(f"COPY silver_orders TO '{silver_path}' (FORMAT PARQUET)")
        connection.execute(f"COPY gold_daily_operations TO '{gold_path}' (FORMAT PARQUET)")
        summary = {
            "source_rows": connection.execute("SELECT count(*) FROM raw_orders").fetchone()[0],
            "accepted_rows": connection.execute("SELECT count(*) FROM silver_orders").fetchone()[0],
            "rejected_rows": connection.execute("SELECT count(*) FROM rejected_orders").fetchone()[0],
            "total_revenue_eur": float(connection.execute("SELECT coalesce(sum(revenue_eur), 0) FROM silver_orders").fetchone()[0]),
            "warehouse": str(root),
        }
        (root / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary
    finally:
        connection.close()
