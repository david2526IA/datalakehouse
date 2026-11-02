import csv

import duckdb

from datalakehouse.demo import generate_orders
from datalakehouse.pipeline import run_pipeline


def test_pipeline_writes_lakehouse_layers(tmp_path) -> None:
    source = tmp_path / "orders.csv"
    generate_orders(source, days=2, daily_orders=3)
    result = run_pipeline(source, tmp_path / "warehouse")
    assert result["source_rows"] == 6
    assert result["accepted_rows"] == 6
    assert (tmp_path / "warehouse" / "silver_orders.parquet").exists()
    connection = duckdb.connect(str(tmp_path / "warehouse" / "warehouse.duckdb"))
    assert connection.execute("SELECT count(*) FROM gold_daily_operations").fetchone()[0] == 2
    connection.close()


def test_pipeline_quarantines_invalid_rows(tmp_path) -> None:
    source = tmp_path / "orders.csv"
    with source.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=["order_id", "order_date", "category", "country", "quantity", "unit_price_eur", "promised_days", "delivered_days"])
        writer.writeheader()
        writer.writerow({"order_id": "ok", "order_date": "2026-01-01", "category": "home", "country": "ES", "quantity": 1, "unit_price_eur": 20, "promised_days": 2, "delivered_days": 2})
        writer.writerow({"order_id": "bad", "order_date": "2026-01-01", "category": "home", "country": "ES", "quantity": -1, "unit_price_eur": 20, "promised_days": 2, "delivered_days": 2})
    result = run_pipeline(source, tmp_path / "warehouse")
    assert result["accepted_rows"] == 1
    assert result["rejected_rows"] == 1
