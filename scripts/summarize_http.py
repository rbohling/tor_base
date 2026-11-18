"""Summarize existing HTTP benchmark CSV for the class presentation.

Usage: python -m scripts.summarize_http results/http/raw.csv
"""
import argparse
import csv
import json
import math
import statistics
from pathlib import Path


def summarize(records):
    output = {}
    for mode in ("local", "onion"):
        selected = [r for r in records if r["mode"] == mode]
        successful = [r for r in selected if str(r["ok"]) == "1"]
        measurements = sorted(float(r["http_ms"]) for r in successful)
        counts = {str(r["count"]) for r in successful}
        output[mode] = {
            "requests": len(selected),
            "successes": len(successful),
            "failures": len(selected) - len(successful),
            "median_http_ms": statistics.median(measurements) if measurements else None,
            "p95_http_ms": measurements[math.ceil(.95 * len(measurements)) - 1] if measurements else None,
            "counts_consistent": len(counts) <= 1,
            "observed_count": next(iter(counts)) if len(counts) == 1 else None,
        }
    output["same_record_count_across_paths"] = (
        output["local"]["observed_count"] is not None
        and output["local"]["observed_count"] == output["onion"]["observed_count"]
        and output["local"]["counts_consistent"]
        and output["onion"]["counts_consistent"]
    )
    output["caution"] = "HTTP times include transport, Flask and SQL; the difference is not pure Tor latency."
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args()
    with args.csv_file.open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    print(json.dumps(summarize(records), indent=2))


if __name__ == "__main__":
    main()
