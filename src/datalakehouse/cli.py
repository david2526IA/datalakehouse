from __future__ import annotations

import argparse
from pathlib import Path

from .demo import generate_orders
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="datalakehouse")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="generate deterministic operational-order data")
    demo.add_argument("--output", default="data/orders.csv")
    demo.add_argument("--days", type=int, default=30)
    run = commands.add_parser("run", help="run bronze/silver/gold pipeline")
    run.add_argument("input")
    run.add_argument("--warehouse", default="warehouse")
    args = parser.parse_args()
    if args.command == "demo":
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        generate_orders(args.output, days=args.days)
        print(f"Demo orders written to {args.output}")
        return
    result = run_pipeline(args.input, args.warehouse)
    print(result)


if __name__ == "__main__":
    main()
