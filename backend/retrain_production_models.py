"""
Retrain production GBM models (1d/3d/7d/30d) with RandomizedSearchCV.

Hyperparameters are discovered automatically — nothing is hardcoded.
Best params + dataset feature medians are saved to models/ so future
inference uses real data defaults instead of guesses.

Run from backend/:
    source venv/bin/activate && python retrain_production_models.py
    source venv/bin/activate && python retrain_production_models.py --n-iter 40
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from services.gov_event_predictor import GovernmentEventPredictor

DATA_FILE  = Path("correlation_data.json")
MODEL_DIR  = Path("models")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--n-iter", type=int, default=60,
                   help="Random combinations to try per horizon (default 60)")
    p.add_argument("--cv", type=int, default=3,
                   help="Cross-validation folds inside search (default 3)")
    p.add_argument("--n-jobs", type=int, default=1,
                   help="Parallel jobs for RandomizedSearchCV (default 1)")
    p.add_argument("--max-samples", type=int, default=None,
                   help="Optional stratified sample cap per horizon for quick refreshes")
    return p.parse_args()


def main():
    args = parse_args()

    print("=" * 62)
    print("  Predovex — Production Model Retraining (RandomizedSearch)")
    print(f"  n_iter={args.n_iter}  cv={args.cv}  n_jobs={args.n_jobs}  horizons: 1d/3d/7d/30d")
    print("=" * 62)

    if not DATA_FILE.exists():
        print(f"\n✗ {DATA_FILE} not found. Run from backend/ directory.")
        sys.exit(1)

    with open(DATA_FILE) as f:
        correlation_data = json.load(f)

    total_events = len(correlation_data.get("events", []))
    print(f"\n  Dataset: {total_events:,} events")
    print(f"  Search space: {args.n_iter} combos × {args.cv}-fold CV per horizon")
    print(f"  Total fits: ~{args.n_iter * args.cv * 4} model trainings\n")

    predictor = GovernmentEventPredictor(model_dir=str(MODEL_DIR))
    results   = predictor.train_model(
        correlation_data,
        n_iter=args.n_iter,
        cv=args.cv,
        n_jobs=args.n_jobs,
        max_samples=args.max_samples,
    )

    print("\n" + "=" * 62)
    print("  Final Results")
    print("=" * 62)
    for horizon, res in results.items():
        if res == "insufficient_data":
            print(f"  {horizon}: insufficient data")
        else:
            print(f"\n  {horizon}:")
            print(f"    Test accuracy : {res['accuracy']}%")
            print(f"    CV score      : {res['cv_score']}%")
            print(f"    Samples       : {res['samples']:,}")
            print(f"    Best params   :")
            for k, v in sorted(res["best_params"].items()):
                print(f"      {k:<22} = {v}")

    print(f"\n  Models + params saved to {MODEL_DIR}/")
    print("=" * 62)


if __name__ == "__main__":
    main()
