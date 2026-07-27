"""
Government Event → Stock Prediction ML Model (Multi-Horizon)
Patent-Critical: FOIA/Contract/Regulatory Event Impact Prediction
Supports 1-Day, 3-Day, 7-Day, and 30-Day Prediction Horizons.

Model: XGBoost (primary) with SMOTE oversampling for minority class.
Hyperparameters are discovered via RandomizedSearchCV and saved to
models/best_params.json — no hardcoded values in training or inference.
Falls back to GradientBoostingClassifier if xgboost is unavailable.
"""
import json
import pickle
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBClassifier
    _HAS_XGB = True
except ImportError:
    _HAS_XGB = False

try:
    from imblearn.over_sampling import SMOTE
    _HAS_SMOTE = True
except ImportError:
    _HAS_SMOTE = False

# Must stay in sync with paper_evaluation.py FEATURE_COLS
FEATURE_COLS = [
    "event_type_foia", "event_type_contract", "event_type_regulatory",
    "event_type_sec_filing", "event_type_fda_action", "event_type_gdelt",
    "signal_score", "vader_positive", "vader_negative",
    "contract_amount_normalized",
    "days_since_last_event", "company_gov_sensitivity",
    "event_count_30d", "total_gov_spending_30d", "avg_signal_score_30d",
    "event_count_60d", "total_gov_spending_60d", "avg_signal_score_60d",
    "event_count_90d", "ticker_event_frequency",
    "foia_before_contract_90d",
    "contract_amount_zscore",
    "day_of_week", "month", "quarter", "is_month_end", "events_last_7d",
    "stock_momentum_3d", "market_momentum_3d", "relative_momentum",
    "market_regime", "stock_volatility_30d", "vix_level",
    "consecutive_positive_returns",
    # New features (v2)
    "high_vix",           # 1 if VIX > 25 — fear regime flag
    "title_length_norm",  # event title word count / 30 — proxy for significance
    "foia_count_90d",     # FOIA-specific event count in 90d window
    # Fundamentals (v3) — from yfinance quarterly data
    "pe_ratio",           # trailing 12-month P/E at event date (0 if unavailable)
    "revenue_growth_yoy", # YoY quarterly revenue growth % (0 if unavailable)
    "earnings_surprise",  # most recent earnings surprise % before event (0 if unavailable)
]

# XGBoost search space
PARAM_DIST_XGB = {
    "n_estimators":     [100, 200, 300, 400, 500, 700, 1000],
    "max_depth":        [3, 4, 5, 6, 7, 8],
    "learning_rate":    [0.01, 0.03, 0.05, 0.08, 0.1, 0.15, 0.2],
    "subsample":        [0.6, 0.7, 0.8, 0.9, 1.0],
    "colsample_bytree": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "min_child_weight": [1, 2, 3, 5, 8, 10],
    "reg_alpha":        [0, 0.01, 0.1, 0.5, 1.0],
    "reg_lambda":       [0.5, 1.0, 1.5, 2.0, 3.0],
    "gamma":            [0, 0.05, 0.1, 0.3, 0.5],
}

# GBM fallback search space
PARAM_DIST_GBM = {
    "n_estimators":     [100, 150, 200, 300, 400, 500, 600],
    "max_depth":        [3, 4, 5, 6, 7],
    "learning_rate":    [0.01, 0.03, 0.05, 0.08, 0.1, 0.15, 0.2],
    "subsample":        [0.6, 0.7, 0.8, 0.9, 1.0],
    "min_samples_leaf": [5, 8, 10, 15, 20, 30, 40],
    "max_features":     ["sqrt", "log2", 0.5, 0.7, None],
}

# Features whose dataset medians are used as inference defaults
_STAT_FEATURES = [
    "signal_score", "vader_positive", "vader_negative",
    "contract_amount_normalized",
    "days_since_last_event", "company_gov_sensitivity",
    "event_count_30d", "total_gov_spending_30d", "avg_signal_score_30d",
    "event_count_60d", "total_gov_spending_60d", "avg_signal_score_60d",
    "event_count_90d", "ticker_event_frequency",
    "stock_volatility_30d", "vix_level",
    "events_last_7d", "consecutive_positive_returns",
    "pe_ratio", "revenue_growth_yoy", "earnings_surprise",
]


class GovernmentEventPredictor:
    def __init__(self, model_dir: str = "models"):
        self.model_dir     = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.horizons      = ["1d", "3d", "7d", "30d"]
        self.models        = {}
        self.scalers       = {}
        self.feature_names = FEATURE_COLS

        self._best_params       = {}   # {horizon: {param: value}}
        self._dataset_stats     = {}   # {feature: median_value}
        self._feature_importance = {}  # {horizon: [{feature, importance}]}

        self._load_all_models()
        self._load_best_params()
        self._load_dataset_stats()
        self._load_feature_importance()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_all_models(self):
        for h in self.horizons:
            m_path = self.model_dir / f"gov_model_{h}.pkl"
            s_path = self.model_dir / f"scaler_{h}.pkl"
            if m_path.exists() and s_path.exists():
                try:
                    with open(m_path, "rb") as f:
                        self.models[h] = pickle.load(f)
                    with open(s_path, "rb") as f:
                        self.scalers[h] = pickle.load(f)
                    print(f"✓ Loaded {h} model.")
                except Exception as e:
                    print(f"⚠ Could not load {h} model: {e}")

    def _save_model(self, horizon: str):
        if horizon in self.models and horizon in self.scalers:
            with open(self.model_dir / f"gov_model_{horizon}.pkl", "wb") as f:
                pickle.dump(self.models[horizon], f)
            with open(self.model_dir / f"scaler_{horizon}.pkl", "wb") as f:
                pickle.dump(self.scalers[horizon], f)

    def _save_best_params(self, horizon: str, params: Dict, test_acc: float, cv_score: float):
        self._best_params[horizon] = {"params": params, "test_acc": test_acc, "cv_score": cv_score}
        path = self.model_dir / "best_params.json"
        existing = {}
        if path.exists():
            try:
                existing = json.loads(path.read_text())
            except Exception:
                pass
        existing[horizon] = self._best_params[horizon]
        path.write_text(json.dumps(existing, indent=2))

    def _load_best_params(self):
        path = self.model_dir / "best_params.json"
        if path.exists():
            try:
                self._best_params = json.loads(path.read_text())
            except Exception:
                pass

    def _save_dataset_stats(self, df: pd.DataFrame):
        stats = {}
        for col in _STAT_FEATURES:
            if col in df.columns:
                val = df[col].median()
                if pd.notna(val):
                    stats[col] = round(float(val), 6)
        path = self.model_dir / "dataset_stats.json"
        path.write_text(json.dumps(stats, indent=2))
        self._dataset_stats = stats
        print(f"  ✓ Dataset stats saved ({len(stats)} feature medians).")

    def _load_dataset_stats(self):
        path = self.model_dir / "dataset_stats.json"
        if path.exists():
            try:
                self._dataset_stats = json.loads(path.read_text())
            except Exception:
                pass

    def _save_feature_importance(self):
        path = self.model_dir / "feature_importance.json"
        path.write_text(json.dumps(self._feature_importance, indent=2))

    def _load_feature_importance(self):
        path = self.model_dir / "feature_importance.json"
        if path.exists():
            try:
                self._feature_importance = json.loads(path.read_text())
            except Exception:
                pass

    # ── Feature engineering ───────────────────────────────────────────────────

    def prepare_data(self, correlation_data: Dict, horizon: str) -> Optional[pd.DataFrame]:
        events = correlation_data.get("events", [])
        if not events:
            return None

        target_col = f"return_{horizon}"

        parsed = []
        for e in events:
            if e.get(target_col) is None:
                continue
            date_str = e.get("event_date", "")
            if not date_str:
                continue
            try:
                dt = datetime.fromisoformat(date_str[:19])
            except Exception:
                continue
            e = dict(e)
            e["_dt"] = dt
            parsed.append(e)

        if not parsed:
            return None

        parsed.sort(key=lambda x: (x.get("ticker", ""), x["_dt"]))

        by_ticker = defaultdict(list)
        for e in parsed:
            by_ticker[e.get("ticker", "UNKNOWN")].append(e)

        ticker_sensitivity = {}
        ticker_mean_award  = {}
        ticker_std_award   = {}
        ticker_event_freq  = {}

        date_min = min(e["_dt"] for e in parsed)
        date_max = max(e["_dt"] for e in parsed)
        total_years = max((date_max - date_min).days / 365.0, 1.0)

        for ticker, tevents in by_ticker.items():
            abs_rets = [abs(x.get(target_col, 0) or 0) for x in tevents]
            ticker_sensitivity[ticker] = min(np.mean(abs_rets) / 10.0, 1.0) if abs_rets else 0.5

            awards = [x.get("Award Amount") or 0 for x in tevents]
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

                foia_bc = 0
                foia_count_90d = 0
                if "contract" in etype:
                    foia_bc = int(any(
                        "foia" in x.get("event_type", "").lower() for x in win90
                    ))
                foia_count_90d = sum(
                    1 for x in win90
                    if "foia" in x.get("event_type", "").lower()
                )

                award = e.get("Award Amount") or 0
                mu    = ticker_mean_award.get(ticker, 0.0)
                sigma = ticker_std_award.get(ticker, 1.0) or 1.0
                contract_zscore = float(np.clip((award - mu) / sigma, -5, 5))

                past_r1    = [x.get("return_1d", 0) or 0 for x in win30]
                volatility = float(np.std(past_r1)) if len(past_r1) > 1 else 1.5

                consec_pos = 0
                for x in reversed(win7):
                    if (x.get("return_1d") or 0) > 0:
                        consec_pos += 1
                    else:
                        break

                sig_dict     = e.get("signal") or {}
                signal_score = sig_dict.get("signal_score", 50)
                # Handle both signal formats (vader_positive direct, or absent)
                vader_pos    = sig_dict.get("vader_positive") or sig_dict.get("vader_pos", 0.0) or 0.0
                vader_neg    = sig_dict.get("vader_negative") or sig_dict.get("vader_neg", 0.0) or 0.0
                vix_level    = e.get("vix_level") or 20.0
                quarter      = (dt.month - 1) // 3 + 1

                # New v2 features
                high_vix         = 1 if vix_level > 25 else 0
                title            = e.get("event_title", "") or ""
                title_length_norm = min(len(title.split()) / 30.0, 1.0)

                row = {
                    "event_type_foia":            1 if "foia"       in etype else 0,
                    "event_type_contract":         1 if "contract"   in etype else 0,
                    "event_type_regulatory":       1 if "regulatory" in etype else 0,
                    "event_type_sec_filing":       1 if "sec"        in etype else 0,
                    "event_type_fda_action":       1 if "fda"        in etype else 0,
                    "event_type_gdelt":            1 if "gdelt"      in etype else 0,
                    "signal_score":                signal_score,
                    "vader_positive":              vader_pos,
                    "vader_negative":              vader_neg,
                    "contract_amount_normalized":  min(award / 1e9, 1.0),
                    "contract_amount_zscore":      contract_zscore,
                    "days_since_last_event":       min(days_since, 180),
                    "company_gov_sensitivity":     ticker_sensitivity.get(ticker, 0.5),
                    "event_count_30d":             len(win30),
                    "total_gov_spending_30d":      min(spending(win30) / 1e9, 5.0),
                    "avg_signal_score_30d":        avg_signal(win30),
                    "event_count_60d":             len(win60),
                    "total_gov_spending_60d":      min(spending(win60) / 1e9, 10.0),
                    "avg_signal_score_60d":        avg_signal(win60),
                    "event_count_90d":             len(win90),
                    "ticker_event_frequency":      min(ticker_event_freq.get(ticker, 1.0) / 50.0, 1.0),
                    "foia_before_contract_90d":    foia_bc,
                    "day_of_week":                 dt.weekday(),
                    "month":                       dt.month,
                    "quarter":                     quarter,
                    "is_month_end":                1 if dt.day >= 25 else 0,
                    "events_last_7d":              len(win7),
                    "stock_momentum_3d":           e.get("stock_momentum_3d", 0.0) or 0.0,
                    "market_momentum_3d":          e.get("market_momentum_3d", 0.0) or 0.0,
                    "relative_momentum":           e.get("relative_momentum", 0.0) or 0.0,
                    "market_regime":               e.get("market_regime", 1) or 1,
                    "stock_volatility_30d":        volatility,
                    "vix_level":                   vix_level,
                    "consecutive_positive_returns": consec_pos,
                    "high_vix":                    high_vix,
                    "title_length_norm":           title_length_norm,
                    "foia_count_90d":              foia_count_90d,
                    # Fundamentals v3
                    "pe_ratio":            float(e.get("pe_ratio") or 0),
                    "revenue_growth_yoy":  float(e.get("revenue_growth_yoy") or 0),
                    "earnings_surprise":   float(e.get("earnings_surprise") or 0),
                    "label": 1 if (e.get(target_col) or 0) > 0 else 0,
                }
                rows.append(row)

        return pd.DataFrame(rows) if rows else None

    # ── Training ──────────────────────────────────────────────────────────────

    def train_model(self, correlation_data: Dict, n_iter: int = 40, cv: int = 4) -> Dict:
        """
        Train one XGBoost (or GBM fallback) per horizon via RandomizedSearchCV.
        SMOTE oversampling is applied to balance minority class when n_train < 800.
        n_iter  — random hyperparameter combinations to try (default 40)
        cv      — stratified CV folds inside the search (default 4)
        """
        model_label = "XGBoost" if _HAS_XGB else "GradientBoosting"
        print(f"  Using model: {model_label}  SMOTE: {'yes' if _HAS_SMOTE else 'no'}")

        results  = {}
        ref_df   = None

        for h in self.horizons:
            print(f"\n  [{h}] Preparing data …")
            df = self.prepare_data(correlation_data, h)
            if df is None or len(df) < 20:
                results[h] = "insufficient_data"
                continue

            if ref_df is None:
                ref_df = df

            X = df[self.feature_names].fillna(0).values.astype(float)
            y = df["label"].values.astype(int)

            class_counts = np.bincount(y)
            minority_ratio = class_counts.min() / max(class_counts.max(), 1)
            print(f"  [{h}] {len(df)} samples  class balance: {class_counts}  "
                  f"minority ratio: {minority_ratio:.2f}")

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # SMOTE: balance training set when minority class < 40% and n_train ≥ 60
            if (_HAS_SMOTE and minority_ratio < 0.40 and len(X_train) >= 60):
                k = min(5, class_counts.min() - 1)
                if k >= 1:
                    try:
                        sm = SMOTE(random_state=42, k_neighbors=k)
                        X_train, y_train = sm.fit_resample(X_train, y_train)
                        print(f"  [{h}] SMOTE applied → {len(X_train)} training samples")
                    except Exception as smote_err:
                        print(f"  [{h}] SMOTE skipped: {smote_err}")

            scaler  = StandardScaler()
            X_tr_s  = scaler.fit_transform(X_train)
            X_te_s  = scaler.transform(X_test)

            cv_strat = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)

            if _HAS_XGB:
                base_estimator = XGBClassifier(
                    random_state=42,
                    eval_metric="logloss",
                    verbosity=0,
                    use_label_encoder=False,
                )
                param_dist = PARAM_DIST_XGB
            else:
                base_estimator = GradientBoostingClassifier(random_state=42)
                param_dist = PARAM_DIST_GBM

            print(f"  [{h}] RandomizedSearchCV ({n_iter} combos × {cv}-fold) …")
            search = RandomizedSearchCV(
                base_estimator,
                param_distributions=param_dist,
                n_iter=n_iter,
                cv=cv_strat,
                scoring="accuracy",
                n_jobs=-1,
                random_state=42,
                verbose=0,
            )
            search.fit(X_tr_s, y_train)

            best_model = search.best_estimator_
            test_acc   = best_model.score(X_te_s, y_test)
            cv_score   = search.best_score_

            self.models[h]  = best_model
            self.scalers[h] = scaler
            self._save_model(h)
            self._save_best_params(
                h, search.best_params_,
                round(test_acc * 100, 2),
                round(cv_score * 100, 2),
            )

            importances = best_model.feature_importances_
            ranked = sorted(
                zip(self.feature_names, importances.tolist()),
                key=lambda x: x[1], reverse=True,
            )
            self._feature_importance[h] = [
                {"feature": f, "importance": round(v, 4)} for f, v in ranked
            ]
            self._save_feature_importance()

            results[h] = {
                "accuracy":    round(test_acc * 100, 2),
                "cv_score":    round(cv_score * 100, 2),
                "samples":     len(df),
                "model":       model_label,
                "best_params": search.best_params_,
            }
            print(f"  ✓ {h}: test={round(test_acc*100,2)}%  cv={round(cv_score*100,2)}%  "
                  f"on {len(df)} events")
            print(f"    params: {search.best_params_}")

        if ref_df is not None:
            self._save_dataset_stats(ref_df)

        return results

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict_impact(self, event_features: Dict) -> Dict:
        preds = {}
        try:
            features = [float(event_features.get(n, 0) or 0) for n in self.feature_names]
            X = np.array([features])

            for h in self.horizons:
                if h in self.models:
                    Xs   = self.scalers[h].transform(X)
                    p    = self.models[h].predict(Xs)[0]
                    prob = self.models[h].predict_proba(Xs)[0]

                    # Top 5 feature drivers for this horizon
                    imp = self.models[h].feature_importances_
                    top_idx = np.argsort(imp)[::-1][:5]
                    top_drivers = [
                        {
                            "feature": self.feature_names[i],
                            "importance": round(float(imp[i]), 4),
                            "value": round(float(features[i]), 4),
                        }
                        for i in top_idx
                    ]

                    preds[h] = {
                        "direction":   "UP" if p == 1 else "DOWN",
                        "confidence":  round(float(max(prob)), 3),
                        "top_drivers": top_drivers,
                    }
                else:
                    preds[h] = {"direction": "UNKNOWN", "confidence": 0.0, "top_drivers": []}
        except Exception as e:
            print(f"Prediction error: {e}")

        return preds

    def predict_anchored(self, ticker: str, all_events: list) -> Dict:
        """
        Predict using the most recent real event for this ticker.
        Reconstructs the full feature vector (rolling windows, NLP, market context)
        from actual stored values — no medians used as defaults.
        Returns prediction dict plus anchor_event {title, date, event_type}.
        Falls back to predict_for_ticker with medians if no events exist.
        """
        ticker_events = [
            e for e in all_events
            if e.get("ticker") == ticker and e.get("event_date")
        ]
        if not ticker_events:
            result = self.predict_for_ticker(ticker, "sec_filing")
            result["anchor_event"] = None
            return result

        # Parse and sort chronologically
        def _parse_dt(e):
            try:
                return datetime.fromisoformat(e["event_date"][:19])
            except Exception:
                return datetime.min

        ticker_events = sorted(ticker_events, key=_parse_dt)
        latest = ticker_events[-1]
        dt = _parse_dt(latest)

        # Rolling windows from prior events
        prev  = ticker_events[:-1]
        win7  = [x for x in prev if (dt - _parse_dt(x)).days <= 7]
        win30 = [x for x in prev if (dt - _parse_dt(x)).days <= 30]
        win60 = [x for x in prev if (dt - _parse_dt(x)).days <= 60]
        win90 = [x for x in prev if (dt - _parse_dt(x)).days <= 90]

        days_since = (dt - _parse_dt(prev[-1])).days if prev else 90
        days_since = min(days_since, 180)

        def spending(window):
            return sum(
                (x.get("Award Amount") or 0)
                for x in window
                if x.get("event_type", "").lower() == "contract"
            )

        def avg_signal(window):
            scores = [(x.get("signal") or {}).get("signal_score", 60) for x in window]
            return float(np.mean(scores)) if scores else 60.0

        # Ticker-level stats across all its events
        awards     = [x.get("Award Amount") or 0 for x in ticker_events]
        abs_rets   = [abs(x.get("return_1d") or 0) for x in ticker_events]
        mu_award   = float(np.mean(awards)) if awards else 0.0
        sig_award  = float(np.std(awards))  if len(awards) > 1 else 1.0
        sensitivity = min(np.mean(abs_rets) / 10.0, 1.0) if abs_rets else 0.5

        date_min = _parse_dt(ticker_events[0])
        date_max = _parse_dt(ticker_events[-1])
        total_years = max((date_max - date_min).days / 365.0, 1.0)
        event_freq  = min(len(ticker_events) / total_years / 50.0, 1.0)

        award  = latest.get("Award Amount") or 0
        zscore = float(np.clip((award - mu_award) / (sig_award or 1.0), -5, 5))

        past_r1    = [x.get("return_1d", 0) or 0 for x in win30]
        volatility = float(np.std(past_r1)) if len(past_r1) > 1 else 1.5

        consec_pos = 0
        for x in reversed(win7):
            if (x.get("return_1d") or 0) > 0:
                consec_pos += 1
            else:
                break

        etype    = latest.get("event_type", "sec_filing").lower()
        sig_dict = latest.get("signal") or {}
        foia_bc  = 0
        if "contract" in etype:
            foia_bc = int(any("foia" in x.get("event_type", "").lower() for x in win90))

        vix_val  = latest.get("vix_level") or self._dataset_stats.get("vix_level", 20.0)
        title_lv = (latest.get("event_title", "") or "")
        foia_c90 = sum(1 for x in win90 if "foia" in x.get("event_type", "").lower())

        features = {
            "event_type_foia":              1 if "foia"       in etype else 0,
            "event_type_contract":          1 if "contract"   in etype else 0,
            "event_type_regulatory":        1 if "regulatory" in etype else 0,
            "event_type_sec_filing":        1 if "sec"        in etype else 0,
            "event_type_fda_action":        1 if "fda"        in etype else 0,
            "event_type_gdelt":             1 if "gdelt"      in etype else 0,
            "signal_score":                 sig_dict.get("signal_score", 50),
            "vader_positive":               sig_dict.get("vader_positive") or sig_dict.get("vader_pos", 0.0) or 0.0,
            "vader_negative":               sig_dict.get("vader_negative") or sig_dict.get("vader_neg", 0.0) or 0.0,
            "contract_amount_normalized":   min(award / 1e9, 1.0),
            "contract_amount_zscore":       zscore,
            "days_since_last_event":        days_since,
            "company_gov_sensitivity":      sensitivity,
            "event_count_30d":              len(win30),
            "total_gov_spending_30d":       min(spending(win30) / 1e9, 5.0),
            "avg_signal_score_30d":         avg_signal(win30),
            "event_count_60d":              len(win60),
            "total_gov_spending_60d":       min(spending(win60) / 1e9, 10.0),
            "avg_signal_score_60d":         avg_signal(win60),
            "event_count_90d":              len(win90),
            "ticker_event_frequency":       event_freq,
            "foia_before_contract_90d":     foia_bc,
            "day_of_week":                  dt.weekday(),
            "month":                        dt.month,
            "quarter":                      (dt.month - 1) // 3 + 1,
            "is_month_end":                 1 if dt.day >= 25 else 0,
            "events_last_7d":               len(win7),
            "stock_momentum_3d":            latest.get("stock_momentum_3d", 0.0) or 0.0,
            "market_momentum_3d":           latest.get("market_momentum_3d", 0.0) or 0.0,
            "relative_momentum":            latest.get("relative_momentum", 0.0) or 0.0,
            "market_regime":                latest.get("market_regime", 1) or 1,
            "stock_volatility_30d":         volatility,
            "vix_level":                    vix_val,
            "consecutive_positive_returns": consec_pos,
            "high_vix":                     1 if vix_val > 25 else 0,
            "title_length_norm":            min(len(title_lv.split()) / 30.0, 1.0),
            "foia_count_90d":               foia_c90,
        }

        result = self.predict_impact(features)
        result["anchor_event"] = {
            "title":      (latest.get("event_title") or latest.get("title") or etype)[:80],
            "date":       dt.strftime("%b %d, %Y"),
            "event_type": etype,
        }
        return result

    def predict_for_ticker(self, ticker: str, event_type: str, signal_score: int = None) -> Dict:
        """
        Build a feature vector using dataset medians as defaults (no hardcoded values).
        All numeric defaults come from _dataset_stats populated during training.
        """
        now = datetime.now()
        s   = self._dataset_stats   # median values from the training set

        # Use dataset median signal score if caller did not specify
        if signal_score is None:
            signal_score = int(s.get("signal_score", 60))

        vix_default = s.get("vix_level", 20.0)
        features = {n: 0 for n in self.feature_names}
        features.update({
            # Event type flags
            "event_type_foia":            1 if "foia"       in event_type.lower() else 0,
            "event_type_contract":        1 if "contract"   in event_type.lower() else 0,
            "event_type_regulatory":      1 if "regulatory" in event_type.lower() else 0,
            "event_type_sec_filing":      1 if "sec"        in event_type.lower() else 0,
            "event_type_fda_action":      1 if "fda"        in event_type.lower() else 0,
            "event_type_gdelt":           1 if "gdelt"      in event_type.lower() else 0,
            # NLP signals — from dataset medians
            "signal_score":               signal_score,
            "vader_positive":             s.get("vader_positive",            0.083),
            "vader_negative":             s.get("vader_negative",            0.038),
            # Contract size — from dataset medians
            "contract_amount_normalized": s.get("contract_amount_normalized", 0.0),
            "contract_amount_zscore":     0.0,
            # Temporal context — from dataset medians
            "days_since_last_event":      s.get("days_since_last_event",     30),
            "company_gov_sensitivity":    s.get("company_gov_sensitivity",   0.5),
            # Rolling window counts & spending — from dataset medians
            "event_count_30d":            s.get("event_count_30d",           1),
            "total_gov_spending_30d":     s.get("total_gov_spending_30d",    0.0),
            "avg_signal_score_30d":       s.get("avg_signal_score_30d",      55.0),
            "event_count_60d":            s.get("event_count_60d",           2),
            "total_gov_spending_60d":     s.get("total_gov_spending_60d",    0.0),
            "avg_signal_score_60d":       s.get("avg_signal_score_60d",      55.0),
            "event_count_90d":            s.get("event_count_90d",           3),
            "ticker_event_frequency":     s.get("ticker_event_frequency",    0.1),
            "foia_before_contract_90d":   0,
            # Calendar — real current date
            "day_of_week":                now.weekday(),
            "month":                      now.month,
            "quarter":                    (now.month - 1) // 3 + 1,
            "is_month_end":               1 if now.day >= 25 else 0,
            "events_last_7d":             s.get("events_last_7d",            1),
            # Market context — neutral (no live fetch at inference time)
            "stock_momentum_3d":          0.0,
            "market_momentum_3d":         0.0,
            "relative_momentum":          0.0,
            "market_regime":              1,
            "stock_volatility_30d":       s.get("stock_volatility_30d",      1.5),
            "vix_level":                  vix_default,
            "consecutive_positive_returns": s.get("consecutive_positive_returns", 0),
            # New v2 features
            "high_vix":                   1 if vix_default > 25 else 0,
            "title_length_norm":          s.get("title_length_norm", 0.2),
            "foia_count_90d":             s.get("foia_count_90d", 0),
        })
        return self.predict_impact(features)

    def get_model_status(self) -> Dict:
        status = {}
        for h in self.horizons:
            entry = {"loaded": h in self.models}
            if h in self._best_params:
                entry["test_acc"]  = self._best_params[h].get("test_acc")
                entry["cv_score"]  = self._best_params[h].get("cv_score")
                entry["params"]    = self._best_params[h].get("params", {})
            status[h] = entry
        return status


# Singleton
gov_event_predictor = GovernmentEventPredictor()
