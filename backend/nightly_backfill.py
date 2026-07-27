"""
Nightly Price Backfill + Retrain
Run via cron or launchd once per day. Fills in price outcomes for new events
(those that now have enough time elapsed) and retrains models when ≥50 new
labeled samples have accumulated since the last retrain.
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# --- path setup so imports work when called from cron ---
sys.path.insert(0, str(Path(__file__).parent))

from services.price_collector import PriceCollector
from services.gov_event_predictor import gov_event_predictor

CORRELATION_PATH = Path(__file__).parent / "correlation_data.json"
STATS_PATH       = Path(__file__).parent / "models" / "best_params.json"
LOG_PATH         = Path(__file__).parent / "nightly_backfill.log"
MIN_NEW_SAMPLES  = 50   # retrain only when this many new labeled events exist


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def count_labeled(events: list) -> int:
    return sum(1 for e in events if e.get("return_7d") is not None)


def main():
    log("=== Nightly backfill started ===")

    # 1. Load current data
    if not CORRELATION_PATH.exists():
        log("ERROR: correlation_data.json not found — nothing to do.")
        return

    with open(CORRELATION_PATH) as f:
        data = json.load(f)

    events_before = len(data.get("events", []))
    labeled_before = count_labeled(data.get("events", []))
    log(f"Events: {events_before} total, {labeled_before} labeled before backfill")

    # 2. Run price backfill — PriceCollector reads fresh from disk
    pc = PriceCollector()
    summary = pc.collect_all_prices()
    log(f"Price backfill: {summary}")

    # 3. Reload to count new labels
    with open(CORRELATION_PATH) as f:
        data = json.load(f)
    labeled_after = count_labeled(data.get("events", []))
    new_labels = labeled_after - labeled_before
    log(f"New labeled events: {new_labels} (total labeled: {labeled_after})")

    # 4. Retrain if enough new data
    if new_labels >= MIN_NEW_SAMPLES:
        log(f"Threshold met ({new_labels} ≥ {MIN_NEW_SAMPLES}) — retraining models …")
        results = gov_event_predictor.train_model(data, n_iter=25, cv=3)
        for h, r in results.items():
            if isinstance(r, dict):
                log(f"  {h}: test={r.get('accuracy')}%  cv={r.get('cv_score')}%  n={r.get('samples')}")
            else:
                log(f"  {h}: {r}")
    else:
        log(f"Only {new_labels} new labels — skipping retrain (need {MIN_NEW_SAMPLES})")

    log("=== Nightly backfill complete ===\n")


if __name__ == "__main__":
    main()
