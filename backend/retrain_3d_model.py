"""
Dedicated 3d-horizon model retraining with a regularization-focused search.

The 3d horizon is inherently noisier than 1d (momentum decays) and 7d/30d
(structural signals need time). This script targets it with:
  - Shallower trees (max_depth 3–5) to avoid fitting noise
  - Stronger L1/L2 regularization
  - More search iterations focused on regularization axes
  - 5-fold CV for more stable estimates

Run from backend/:
    source venv/bin/activate && python retrain_3d_model.py
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from services.gov_event_predictor import (
    GovernmentEventPredictor,
    FEATURE_COLS,
    _HAS_XGB,
    _HAS_SMOTE,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

try:
    from imblearn.over_sampling import SMOTE
except ImportError:
    SMOTE = None

DATA_FILE = Path("correlation_data.json")
MODEL_DIR  = Path("models")

# 3d-specific param space: shallow trees + heavy regularization
PARAM_DIST_3D = {
    "n_estimators":     [300, 500, 700, 1000, 1200],
    "max_depth":        [3, 4, 5],
    "learning_rate":    [0.01, 0.02, 0.03, 0.05],
    "subsample":        [0.6, 0.7, 0.8],
    "colsample_bytree": [0.5, 0.6, 0.7, 0.8],
    "min_child_weight": [3, 5, 8, 10, 15],
    "reg_alpha":        [0.1, 0.3, 0.5, 1.0, 2.0],
    "reg_lambda":       [1.0, 1.5, 2.0, 3.0, 4.0],
    "gamma":            [0.05, 0.1, 0.2, 0.3, 0.5],
}

N_ITER = 80
CV     = 5


def main():
    print("=" * 60)
    print("  Predovex — 3d Model Dedicated Retraining (v5 features)")
    print(f"  n_iter={N_ITER}  cv={CV}  shallow+regularized param space")
    print("=" * 60)

    if not DATA_FILE.exists():
        print(f"\n✗ {DATA_FILE} not found. Run from backend/")
        sys.exit(1)

    with open(DATA_FILE) as f:
        correlation_data = json.load(f)

    print(f"\n  Dataset: {len(correlation_data.get('events', [])):,} events")

    predictor = GovernmentEventPredictor(model_dir=str(MODEL_DIR))

    print("\n  [3d] Preparing data with v5 features …")
    df = predictor.prepare_data(correlation_data, "3d")
    if df is None or len(df) < 20:
        print("✗ Insufficient data for 3d training")
        sys.exit(1)

    X = df[FEATURE_COLS].fillna(0).values.astype(float)
    y = df["label"].values.astype(int)

    class_counts = np.bincount(y)
    minority_ratio = class_counts.min() / max(class_counts.max(), 1)
    print(f"  [3d] {len(df)} samples  class balance: {class_counts}  "
          f"minority_ratio: {minority_ratio:.2f}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    if SMOTE is not None and minority_ratio < 0.40 and len(X_train) >= 60:
        k = min(5, class_counts.min() - 1)
        if k >= 1:
            try:
                sm = SMOTE(random_state=42, k_neighbors=k)
                X_train, y_train = sm.fit_resample(X_train, y_train)
                print(f"  [3d] SMOTE applied → {len(X_train)} training samples")
            except Exception as e:
                print(f"  [3d] SMOTE skipped: {e}")

    scaler    = StandardScaler()
    X_tr_s    = scaler.fit_transform(X_train)
    X_te_s    = scaler.transform(X_test)
    cv_strat  = StratifiedKFold(n_splits=CV, shuffle=True, random_state=42)

    if XGBClassifier is None:
        print("✗ XGBoost not available — install xgboost and retry")
        sys.exit(1)

    base = XGBClassifier(
        random_state=42,
        eval_metric="logloss",
        verbosity=0,
        use_label_encoder=False,
    )

    print(f"  [3d] RandomizedSearchCV ({N_ITER} combos × {CV}-fold) …")
    search = RandomizedSearchCV(
        base,
        param_distributions=PARAM_DIST_3D,
        n_iter=N_ITER,
        cv=cv_strat,
        scoring="accuracy",
        n_jobs=-1,
        random_state=7,
        verbose=1,
    )
    search.fit(X_tr_s, y_train)

    best = search.best_estimator_
    test_acc = best.score(X_te_s, y_test)
    cv_score = search.best_score_

    print(f"\n  [3d] test_acc={test_acc*100:.2f}%  cv={cv_score*100:.2f}%")
    print(f"  [3d] best params: {search.best_params_}")

    # Compare with existing model
    existing_params_path = MODEL_DIR / "best_params.json"
    existing_acc = 0.0
    if existing_params_path.exists():
        try:
            ep = json.loads(existing_params_path.read_text())
            existing_acc = ep.get("3d", {}).get("test_acc", 0.0)
        except Exception:
            pass

    print(f"\n  Existing 3d accuracy : {existing_acc:.2f}%")
    print(f"  New 3d accuracy      : {test_acc*100:.2f}%")

    if test_acc * 100 > existing_acc:
        print("  ✅ New model is better — saving.")
        with open(MODEL_DIR / "gov_model_3d.pkl", "wb") as f:
            pickle.dump(best, f)
        with open(MODEL_DIR / "scaler_3d.pkl", "wb") as f:
            pickle.dump(scaler, f)

        # Update best_params.json
        existing = {}
        if existing_params_path.exists():
            try:
                existing = json.loads(existing_params_path.read_text())
            except Exception:
                pass
        existing["3d"] = {
            "params":   search.best_params_,
            "test_acc": round(test_acc * 100, 2),
            "cv_score": round(cv_score * 100, 2),
        }
        existing_params_path.write_text(json.dumps(existing, indent=2))

        # Update feature importance
        imp = best.feature_importances_
        ranked = sorted(
            zip(FEATURE_COLS, imp.tolist()),
            key=lambda x: x[1], reverse=True,
        )
        fi_path = MODEL_DIR / "feature_importance.json"
        fi = {}
        if fi_path.exists():
            try:
                fi = json.loads(fi_path.read_text())
            except Exception:
                pass
        fi["3d"] = [{"feature": f, "importance": round(v, 4)} for f, v in ranked]
        fi_path.write_text(json.dumps(fi, indent=2))

        print(f"\n  Top 10 features for 3d:")
        for item in fi["3d"][:10]:
            print(f"    {item['feature']:40s} {item['importance']:.4f}")
    else:
        print("  ⚠️  New model did not beat existing — keeping old model.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
