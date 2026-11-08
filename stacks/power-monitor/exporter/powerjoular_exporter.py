#!/usr/bin/env python3
"""Expose the latest PowerJoular service CSV sample as Prometheus metrics."""
import csv
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

CSV_PATH = os.environ.get(
    "POWERJOULAR_CSV",
    "/run/powerjoular/powerjoular-service.csv",
)
HOST = os.environ.get("POWERJOULAR_EXPORTER_HOST", "172.17.0.1")
PORT = int(os.environ.get("POWERJOULAR_EXPORTER_PORT", "9108"))


def read_latest_sample():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = [row for row in csv.reader(f) if row and any(v.strip() for v in row)]
    if not rows:
        raise ValueError("PowerJoular CSV is empty")

    # Ignore an optional header and use the newest non-empty data row.
    for row in reversed(rows):
        if len(row) < 5:
            continue
        try:
            timestamp, cpu_usage, total_w, cpu_w, gpu_w = map(
                float, [cell.strip() for cell in row[:5]]
            )
            return timestamp, cpu_usage, total_w, cpu_w, gpu_w
        except ValueError:
            continue
    raise ValueError("No valid five-column PowerJoular data row found")


def metrics_text():
    try:
        timestamp, cpu_usage, total_w, cpu_w, gpu_w = read_latest_sample()
        age = max(0.0, time.time() - timestamp)
        up = 1
        values = {
            "powerjoular_exporter_up": up,
            "powerjoular_sample_age_seconds": age,
            "powerjoular_sample_timestamp_seconds": timestamp,
            "powerjoular_cpu_usage_ratio": cpu_usage,
            "powerjoular_total_watts": total_w,
            "powerjoular_cpu_watts": cpu_w,
            "powerjoular_gpu_watts": gpu_w,
        }
    except Exception:
        values = {"powerjoular_exporter_up": 0}

    help_types = {
        "powerjoular_exporter_up": ("Exporter can read a valid PowerJoular sample", "gauge"),
        "powerjoular_sample_age_seconds": ("Age of the latest PowerJoular sample", "gauge"),
        "powerjoular_sample_timestamp_seconds": ("Unix timestamp of the latest PowerJoular sample", "gauge"),
        "powerjoular_cpu_usage_ratio": ("CPU utilization as a ratio from 0 to 1", "gauge"),
        "powerjoular_total_watts": ("PowerJoular estimated total CPU plus GPU power in watts", "gauge"),
        "powerjoular_cpu_watts": ("PowerJoular estimated CPU power in watts", "gauge"),
        "powerjoular_gpu_watts": ("PowerJoular reported GPU power in watts", "gauge"),
    }
    lines = []
    for name, value in values.items():
        help_text, metric_type = help_types[name]
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {metric_type}")
        lines.append(f"{name} {value}")
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/metrics", "/"):
            self.send_error(404)
            return
        body = metrics_text().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


if __name__ == "__main__":
    print(f"PowerJoular exporter listening on {HOST}:{PORT}; CSV={CSV_PATH}", flush=True)
    HTTPServer((HOST, PORT), Handler).serve_forever()
