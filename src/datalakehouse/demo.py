"""Generate deterministic, realistic order events for local demonstrations."""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path


def generate_orders(path: str | Path, days: int = 30, daily_orders: int = 40, seed: int = 19) -> None:
    randomizer = random.Random(seed)
    categories = {"electronics": (45, 330), "home": (12, 130), "sports": (18, 180), "books": (8, 48)}
    start = date(2026, 1, 1)
    fields = ["order_id", "order_date", "category", "country", "quantity", "unit_price_eur", "promised_days", "delivered_days"]
    with Path(path).open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        for day in range(days):
            for sequence in range(daily_orders):
                category = randomizer.choice(list(categories))
                low, high = categories[category]
                promised = randomizer.choice((1, 2, 3, 5))
                delay = 2 if randomizer.random() < 0.12 else 0
                writer.writerow({
                    "order_id": f"ORD-{day:03d}-{sequence:04d}",
                    "order_date": (start + timedelta(days=day)).isoformat(),
                    "category": category,
                    "country": randomizer.choice(("ES", "PT", "FR", "DE")),
                    "quantity": randomizer.randint(1, 4),
                    "unit_price_eur": round(randomizer.uniform(low, high), 2),
                    "promised_days": promised,
                    "delivered_days": promised + delay,
                })
