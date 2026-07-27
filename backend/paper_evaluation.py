"""
paper_evaluation.py — Paper-Ready ML Evaluation for Predovex
Computes real accuracy metrics on the 4,992 labeled events.

Run from backend/ directory:
    source venv/bin/activate && python paper_evaluation.py

Outputs paper_evaluation_results.json (loaded by correlation_tracker for live stats).
"""
import json
import math
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    precision_score, recall_score, confusion_matrix,
)
from scipy.stats import chi2

DATA_FILE    = Path("correlation_data.json")
RESULTS_FILE = Path("paper_evaluation_results.json")

# Core features (shared across all horizons)
FEATURE_COLS = [
    # Event type flags
    "event_type_foia", "event_type_contract", "event_type_regulatory",
    "event_type_sec_filing", "event_type_fda_action",
    # NLP signal (VADER-derived, replaces hardcoded keyword score)
    "signal_score", "vader_positive", "vader_negative",
    # Contract size
    "contract_amount_normalized",
    # Timeline features — short-window (7/30d)
    "days_since_last_event", "company_gov_sensitivity",
    "event_count_30d", "total_gov_spending_30d", "avg_signal_score_30d",
    # Timeline features — long-window (60/90d) for better 7d/30d prediction
    "event_count_60d", "total_gov_spending_60d", "avg_signal_score_60d",
    "event_count_90d", "ticker_event_frequency",
    # FOIA pipeline signal
    "foia_before_contract_90d",
    # Contract z-score vs ticker average
    "contract_amount_zscore",
    # Temporal
    "day_of_week", "month", "quarter", "is_month_end", "events_last_7d",
    # Market context (real SPY momentum + VIX fear gauge)
    "stock_momentum_3d", "market_momentum_3d", "relative_momentum",
    "market_regime", "stock_volatility_30d", "vix_level",
    # Consecutive signal direction
    "consecutive_positive_returns",
]

# Keyword sets for the VADER-style baseline
BULLISH_KW = {
    "approved", "award", "awarded", "contract", "grant", "success",
    "growth", "expanded", "increased", "profit", "favorable", "milestone",
    "won", "partnership", "acquisition", "investment", "funding", "upgrade",
}
BEARISH_KW = {
    "rejected", "investigation", "violation", "fine", "penalty", "lawsuit",
    "fraud", "bankruptcy", "layoff", "recall", "suspended", "cancelled",
    "failed", "breach", "default", "risk", "loss", "probe", "sanction",
    "downgrade", "warning",
}


# ── 1. Load and clean events ──────────────────────────────────────────────────

def load_events():
    with open(DATA_FILE) as f:
        data = json.load(f)

    clean = []
    for e in data["events"]:
        date_str = e.get("event_date", "")
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str[:19])
        except Exception:
            continue

        # All return horizons must be valid finite numbers
        vals = [
            e.get("return_1d"), e.get("return_3d"),
            e.get("return_7d"), e.get("return_30d"),
        ]
        if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in vals):
            continue

        e["_dt"] = dt
        clean.append(e)

    return clean


# ── 2. Feature engineering ─────────────────────────────────────────────────────

def engineer_features(events):
    events.sort(key=lambda e: (e.get("ticker", ""), e["_dt"]))

    by_ticker = defaultdict(list)
    for e in events:
        by_ticker[e.get("ticker", "UNKNOWN")].append(e)

    # Company gov-sensitivity: normalised avg |30d return| per ticker
    ticker_sensitivity = {}
    ticker_mean_award  = {}
    ticker_std_award   = {}
    ticker_event_freq  = {}  # events-per-year

    date_min = min(e["_dt"] for e in events)
    date_max = max(e["_dt"] for e in events)
    total_years = max((date_max - date_min).days / 365.0, 1.0)

    for ticker, tevents in by_ticker.items():
        abs_rets = [abs(e.get("return_30d", 0) or 0) for e in tevents]
        ticker_sensitivity[ticker] = min(np.mean(abs_rets) / 10.0, 1.0) if abs_rets else 0.5

        awards = [e.get("Award Amount") or 0 for e in tevents]
        ticker_mean_award[ticker] = float(np.mean(awards)) if awards else 0.0
        ticker_std_award[ticker]  = float(np.std(awards))  if len(awards) > 1 else 1.0

        ticker_event_freq[ticker] = len(tevents) / total_years

    rows = []
    for ticker, tevents in by_ticker.items():
        for i, e in enumerate(tevents):
            dt    = e["_dt"]
            etype = e.get("event_type", "").lower()

            prev  = tevents[:i]
            win7  = [x for x in prev if (dt - x["_dt"]).days <= 7]
            win30 = [x for x in prev if (dt - x["_dt"]).days <= 30]
            win60 = [x for x in prev if (dt - x["_dt"]).days <= 60]
            win90 = [x for x in prev if (dt - x["_dt"]).days <= 90]

            days_since = (dt - tevents[i - 1]["_dt"]).days if i > 0 else 90

            def spending(window):
                return sum(
                    (x.get("Award Amount") or 0)
                    for x in window
                    if x.get("event_type", "").lower() == "contract"
                )

            def avg_signal(window):
                scores = [(x.get("signal") or {}).get("signal_score", 60) for x in window]
                return float(np.mean(scores)) if scores else 60.0

            # FOIA-before-contract: was there a FOIA event in the 90d before this contract?
            foia_bc = 0
            if "contract" in etype:
                foia_bc = int(any(
                    "foia" in x.get("event_type", "").lower() for x in win90
                ))

            # Contract amount z-score vs ticker history
            award = e.get("Award Amount") or 0
            mu    = ticker_mean_award.get(ticker, 0.0)
            sigma = ticker_std_award.get(ticker, 1.0) or 1.0
            contract_zscore = (award - mu) / sigma

            # Past 30d returns for volatility
            past_r1 = [x.get("return_1d", 0) or 0 for x in win30]
            volatility = float(np.std(past_r1)) if len(past_r1) > 1 else 1.5

            # Consecutive positive 1d returns leading up to this event
            consec_pos = 0
            for x in reversed(win7):
                if (x.get("return_1d") or 0) > 0:
                    consec_pos += 1
                else:
                    break

            sig_dict     = e.get("signal") or {}
            signal_score = sig_dict.get("signal_score", 50)
            vader_pos    = sig_dict.get("vader_positive", 0.0)
            vader_neg    = sig_dict.get("vader_negative", 0.0)
            vix_level    = e.get("vix_level") or 20.0   # historical VIX avg ~20
            quarter      = (dt.month - 1) // 3 + 1

            row = {
                # Event type flags
                "event_type_foia":       1 if "foia"       in etype else 0,
                "event_type_contract":   1 if "contract"   in etype else 0,
                "event_type_regulatory": 1 if "regulatory" in etype else 0,
                "event_type_sec_filing": 1 if "sec"        in etype else 0,
                "event_type_fda_action": 1 if "fda"        in etype else 0,
                # NLP signal (VADER-derived, not hardcoded)
                "signal_score":                signal_score,
                "vader_positive":              vader_pos,
                "vader_negative":              vader_neg,
                # Contract size
                "contract_amount_normalized":  min(award / 1e9, 1.0),
                "contract_amount_zscore":      float(np.clip(contract_zscore, -5, 5)),
                # Short-window timeline features
                "days_since_last_event":       min(days_since, 180),
                "company_gov_sensitivity":     ticker_sensitivity.get(ticker, 0.5),
                "event_count_30d":             len(win30),
                "total_gov_spending_30d":      min(spending(win30) / 1e9, 5.0),
                "avg_signal_score_30d":        avg_signal(win30),
                # Long-window timeline features (help 7d/30d horizons)
                "event_count_60d":             len(win60),
                "total_gov_spending_60d":      min(spending(win60) / 1e9, 10.0),
                "avg_signal_score_60d":        avg_signal(win60),
                "event_count_90d":             len(win90),
                "ticker_event_frequency":      min(ticker_event_freq.get(ticker, 1.0) / 50.0, 1.0),
                # FOIA pipeline
                "foia_before_contract_90d":    foia_bc,
                # Temporal
                "day_of_week":                 dt.weekday(),
                "month":                       dt.month,
                "quarter":                     quarter,
                "is_month_end":                1 if dt.day >= 25 else 0,
                "events_last_7d":              len(win7),
                # Market context (real SPY momentum + VIX fear gauge)
                "stock_momentum_3d":           e.get("stock_momentum_3d", 0.0) or 0.0,
                "market_momentum_3d":          e.get("market_momentum_3d", 0.0) or 0.0,
                "relative_momentum":           e.get("relative_momentum", 0.0) or 0.0,
                "market_regime":               e.get("market_regime", 1) or 1,
                "stock_volatility_30d":        volatility,
                "vix_level":                   vix_level,
                # Momentum signal
                "consecutive_positive_returns": consec_pos,
                # Classification labels (all 4 horizons)
                "label_1d":  1 if (e.get("return_1d")  or 0) > 0 else 0,
                "label_3d":  1 if (e.get("return_3d")  or 0) > 0 else 0,
                "label_7d":  1 if (e.get("return_7d")  or 0) > 0 else 0,
                "label_30d": 1 if (e.get("return_30d") or 0) > 0 else 0,
                # For keyword baseline
                "event_title": e.get("event_title", ""),
                "ticker":      ticker,
            }
            rows.append(row)

    return pd.DataFrame(rows)


# ── 3. Keyword baseline ───────────────────────────────────────────────────────

def keyword_predict(title: str) -> int:
    words = set(title.lower().split())
    bull = len(words & BULLISH_KW)
    bear = len(words & BEARISH_KW)
    return 1 if bull >= bear else 0


# ── 4. Evaluate one horizon ───────────────────────────────────────────────────

def evaluate_horizon(df: pd.DataFrame, horizon: str) -> dict:
    label_col = f"label_{horizon}"
    X = df[FEATURE_COLS].values.astype(float)
    y = df[label_col].values.astype(int)

    majority_class = int(np.bincount(y).argmax())
    positive_pct   = float(y.mean()) * 100

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    y_true_all = []
    y_rf_all   = []
    y_gbm_all  = []
    y_maj_all  = []
    y_kw_all   = []

    for fold, (train_idx, test_idx) in enumerate(skf.split(X, y)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        scaler   = StandardScaler()
        X_tr_s   = scaler.fit_transform(X_train)
        X_te_s   = scaler.transform(X_test)

        # Random Forest
        rf = RandomForestClassifier(
            n_estimators=500, max_depth=6, min_samples_leaf=8,
            random_state=42, class_weight="balanced",
        )
        rf.fit(X_tr_s, y_train)
        y_rf_pred = rf.predict(X_te_s)

        # Gradient Boosting (better at capturing long-range patterns)
        gbm = GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=10, random_state=42,
        )
        gbm.fit(X_tr_s, y_train)
        y_gbm_pred = gbm.predict(X_te_s)

        y_true_all.extend(y_test.tolist())
        y_rf_all.extend(y_rf_pred.tolist())
        y_gbm_all.extend(y_gbm_pred.tolist())
        y_maj_all.extend([majority_class] * len(y_test))
        y_kw_all.extend([keyword_predict(df.iloc[i]["event_title"]) for i in test_idx])

    y_true = np.array(y_true_all)
    y_rf   = np.array(y_rf_all)
    y_gbm  = np.array(y_gbm_all)
    y_maj  = np.array(y_maj_all)
    y_kw   = np.array(y_kw_all)

    # ── RF classification metrics ──────────────────────────────────────────
    rf_acc  = accuracy_score(y_true, y_rf)
    rf_f1   = f1_score(y_true, y_rf, average="weighted")
    rf_prec = precision_score(y_true, y_rf, average="weighted", zero_division=0)
    rf_rec  = recall_score(y_true, y_rf, average="weighted", zero_division=0)
    cm_rf   = confusion_matrix(y_true, y_rf).tolist()

    # ── GBM classification metrics ─────────────────────────────────────────
    gbm_acc  = accuracy_score(y_true, y_gbm)
    gbm_f1   = f1_score(y_true, y_gbm, average="weighted")
    gbm_prec = precision_score(y_true, y_gbm, average="weighted", zero_division=0)
    gbm_rec  = recall_score(y_true, y_gbm, average="weighted", zero_division=0)
    cm_gbm   = confusion_matrix(y_true, y_gbm).tolist()

    # ── AUC from 80/20 split (needs predict_proba) ─────────────────────────
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    sc_full = StandardScaler()
    X_tr_s2 = sc_full.fit_transform(X_tr)
    X_te_s2 = sc_full.transform(X_te)

    rf_full = RandomForestClassifier(
        n_estimators=500, max_depth=6, min_samples_leaf=8,
        random_state=42, class_weight="balanced",
    )
    rf_full.fit(X_tr_s2, y_tr)
    rf_probas = rf_full.predict_proba(X_te_s2)[:, 1]
    rf_auc    = roc_auc_score(y_te, rf_probas)

    gbm_full = GradientBoostingClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, min_samples_leaf=10, random_state=42,
    )
    gbm_full.fit(X_tr_s2, y_tr)
    gbm_probas = gbm_full.predict_proba(X_te_s2)[:, 1]
    gbm_auc    = roc_auc_score(y_te, gbm_probas)

    # Best model (by CV accuracy)
    best_model = "random_forest" if rf_acc >= gbm_acc else "gradient_boosting"
    best_preds = y_rf if rf_acc >= gbm_acc else y_gbm

    # Feature importances (RF)
    importances  = dict(zip(FEATURE_COLS, rf_full.feature_importances_.tolist()))
    top_features = sorted(importances.items(), key=lambda x: -x[1])[:10]

    # ── Baseline metrics ───────────────────────────────────────────────────
    maj_acc = accuracy_score(y_true, y_maj)
    kw_acc  = accuracy_score(y_true, y_kw)

    # ── McNemar's test: best model vs majority-class baseline ─────────────
    def mcnemar(y_pred, y_baseline, y_true):
        pred_right = (y_pred == y_true)
        base_right = (y_baseline == y_true)
        b = int(np.sum(pred_right  & ~base_right))
        c = int(np.sum(~pred_right & base_right))
        if b + c >= 25:
            stat  = (abs(b - c) - 1) ** 2 / (b + c)
            p_val = float(1 - chi2.cdf(stat, df=1))
        else:
            stat, p_val = None, None
        return b, c, stat, p_val

    b_rf, c_rf, stat_rf, p_rf = mcnemar(y_rf,  y_maj, y_true)
    b_gbm, c_gbm, stat_gbm, p_gbm = mcnemar(y_gbm, y_maj, y_true)

    # Also compare RF vs GBM (to show models are complementary)
    b_vs, c_vs, stat_vs, p_vs = mcnemar(y_rf, y_gbm, y_true)

    def sig_block(b, c, stat, p_val, label):
        return {
            "test":  f"McNemar ({label} vs majority-class baseline)",
            "b_model_only": b,
            "c_maj_only":   c,
            "statistic":    round(stat, 4) if stat is not None else None,
            "p_value":      round(p_val, 6) if p_val is not None else None,
            "significant_at_0.05": (p_val < 0.05) if p_val is not None else None,
        }

    return {
        "horizon":    horizon,
        "n_samples":  int(len(y)),
        "best_model": best_model,
        "class_distribution": {
            "positive_pct":   round(positive_pct, 1),
            "majority_class": "UP" if majority_class == 1 else "DOWN",
        },
        "random_forest": {
            "accuracy":           round(rf_acc * 100, 2),
            "f1_weighted":        round(float(rf_f1), 4),
            "precision_weighted": round(float(rf_prec), 4),
            "recall_weighted":    round(float(rf_rec), 4),
            "auc_roc":            round(float(rf_auc), 4),
            "confusion_matrix":   cm_rf,
        },
        "gradient_boosting": {
            "accuracy":           round(gbm_acc * 100, 2),
            "f1_weighted":        round(float(gbm_f1), 4),
            "precision_weighted": round(float(gbm_prec), 4),
            "recall_weighted":    round(float(gbm_rec), 4),
            "auc_roc":            round(float(gbm_auc), 4),
            "confusion_matrix":   cm_gbm,
        },
        "baselines": {
            "majority_class_accuracy":   round(maj_acc * 100, 2),
            "keyword_baseline_accuracy": round(kw_acc  * 100, 2),
            "random_baseline_accuracy":  50.0,
        },
        "lift_over_majority": round((max(rf_acc, gbm_acc) - maj_acc) * 100, 2),
        "lift_over_random":   round((max(rf_acc, gbm_acc) - 0.5)    * 100, 2),
        "statistical_significance": {
            "random_forest":      sig_block(b_rf,  c_rf,  stat_rf,  p_rf,  "RF"),
            "gradient_boosting":  sig_block(b_gbm, c_gbm, stat_gbm, p_gbm, "GBM"),
        },
        "top_10_features": [
            {"feature": k, "importance": round(v, 4)} for k, v in top_features
        ],
    }


# ── 5. Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("  Predovex — Paper Evaluation Pipeline (4 horizons, 2 models)")
    print("=" * 72)

    print("\n[1/4] Loading events...")
    events = load_events()
    print(f"      {len(events):,} valid labeled events")

    print("\n[2/4] Engineering features from event timeline...")
    df = engineer_features(events)
    print(f"      {df.shape[0]:,} rows × {len(FEATURE_COLS)} features")
    print(f"      Tickers:          {df['ticker'].nunique()}")
    print(f"      Contract events:  {int(df['event_type_contract'].sum()):,}")
    print(f"      FOIA events:      {int(df['event_type_foia'].sum()):,}")

    print("\n[3/4] 5-fold stratified cross-validation (4 horizons × 2 models)...")
    results = {}
    for horizon in ["1d", "3d", "7d", "30d"]:
        print(f"\n  ── Horizon {horizon} ──")
        res = evaluate_horizon(df, horizon)
        results[horizon] = res
        rf  = res["random_forest"]
        gbm = res["gradient_boosting"]
        bl  = res["baselines"]
        sig_rf  = res["statistical_significance"]["random_forest"]
        sig_gbm = res["statistical_significance"]["gradient_boosting"]

        print(f"     Samples: {res['n_samples']:,}  |  "
              f"UP%: {res['class_distribution']['positive_pct']}%")
        print(f"     RF  Accuracy:  {rf['accuracy']}%  AUC: {rf['auc_roc']}")
        print(f"     GBM Accuracy: {gbm['accuracy']}%  AUC: {gbm['auc_roc']}")
        print(f"     Majority baseline: {bl['majority_class_accuracy']}%  "
              f"Keyword: {bl['keyword_baseline_accuracy']}%")
        print(f"     Best model:   {res['best_model']}  "
              f"Lift: +{res['lift_over_majority']} pp")
        for label, sig in [("RF", sig_rf), ("GBM", sig_gbm)]:
            if sig["p_value"] is not None:
                flag = "✓ significant" if sig["significant_at_0.05"] else "✗ not significant"
                print(f"     McNemar ({label}) p={sig['p_value']:.4f}  ({flag})")

    print("\n[4/4] Results table")
    print("=" * 88)
    print(f"{'Horizon':<8} {'RF%':>7} {'GBM%':>7} {'Maj%':>7} {'KW%':>7} "
          f"{'AUC-RF':>8} {'AUC-GBM':>9} {'p(RF)':>10} {'p(GBM)':>10}")
    print("-" * 88)
    for h, r in results.items():
        rf  = r["random_forest"]
        gbm = r["gradient_boosting"]
        bl  = r["baselines"]
        s_rf  = r["statistical_significance"]["random_forest"]
        s_gbm = r["statistical_significance"]["gradient_boosting"]
        p_rf  = f"{s_rf['p_value']:.4f}"  if s_rf["p_value"]  is not None else "N/A"
        p_gbm = f"{s_gbm['p_value']:.4f}" if s_gbm["p_value"] is not None else "N/A"
        print(f"{h:<8} {rf['accuracy']:>6.2f}% {gbm['accuracy']:>6.2f}% "
              f"{bl['majority_class_accuracy']:>6.2f}% "
              f"{bl['keyword_baseline_accuracy']:>6.2f}% "
              f"{rf['auc_roc']:>8.4f} {gbm['auc_roc']:>9.4f} "
              f"{p_rf:>10} {p_gbm:>10}")
    print("=" * 88)

    # Save full results
    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "dataset": {
            "total_events":    len(events),
            "tickers":         int(df["ticker"].nunique()),
            "date_range": {
                "start": min(e["_dt"].isoformat() for e in events),
                "end":   max(e["_dt"].isoformat() for e in events),
            },
            "event_types": {
                "contract": int(df["event_type_contract"].sum()),
                "foia":     int(df["event_type_foia"].sum()),
            },
            "feature_count": len(FEATURE_COLS),
        },
        "evaluation": results,
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Results saved → {RESULTS_FILE}")
    return output


if __name__ == "__main__":
    main()
