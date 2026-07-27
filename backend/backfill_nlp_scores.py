"""
Backfill VADER NLP sentiment scores for all event titles.

Replaces the hardcoded signal_score=70 with a real compound sentiment
derived from the event title text.  Also stores vader_positive and
vader_negative as separate per-event fields for use as model features.

Run from backend/:
    source venv/bin/activate && python backfill_nlp_scores.py
"""
import json
from pathlib import Path
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

DATA_FILE = Path("correlation_data.json")

# Domain-specific adjustments for government/financial language
EXTRA_LEXICON = {
    "award":       1.5,
    "awarded":     1.5,
    "contract":    0.8,
    "approved":    1.8,
    "approval":    1.5,
    "violation":  -2.0,
    "fraud":      -2.5,
    "penalty":    -1.8,
    "fine":       -1.5,
    "recall":     -2.0,
    "investigation": -1.5,
    "lawsuit":    -1.8,
    "bankruptcy": -2.5,
    "layoff":     -1.5,
    "suspended":  -1.8,
    "cancelled":  -1.5,
    "terminated": -1.2,
    "probe":      -1.5,
    "sanction":   -1.8,
    "warning":    -1.2,
    "grant":       1.2,
    "partnership": 1.0,
    "acquisition": 0.8,
    "investment":  1.0,
    "funding":     1.2,
    "milestone":   1.5,
    "clearance":   1.0,
    "expansion":   1.2,
}


def main():
    analyzer = SentimentIntensityAnalyzer()
    analyzer.lexicon.update(EXTRA_LEXICON)

    data = json.load(open(DATA_FILE))
    events = data["events"]

    updated = 0
    score_dist = {"positive": 0, "neutral": 0, "negative": 0}

    for event in events:
        title = (event.get("event_title") or "").strip()
        if not title:
            title = f"{event.get('event_type', 'event')} {event.get('ticker', '')}"

        vs = analyzer.polarity_scores(title)
        compound = vs["compound"]  # -1.0 to +1.0

        # Rescale compound to 0–100 (50 = neutral)
        nlp_score = round((compound + 1.0) / 2.0 * 100.0, 2)

        if not isinstance(event.get("signal"), dict):
            event["signal"] = {}

        event["signal"]["signal_score"]        = nlp_score
        event["signal"]["nlp_sentiment_score"] = nlp_score
        event["signal"]["vader_compound"]      = round(compound, 4)
        event["signal"]["vader_positive"]      = round(vs["pos"], 4)
        event["signal"]["vader_negative"]      = round(vs["neg"], 4)
        event["signal"]["vader_neutral"]       = round(vs["neu"], 4)

        if compound > 0.05:
            score_dist["positive"] += 1
        elif compound < -0.05:
            score_dist["negative"] += 1
        else:
            score_dist["neutral"] += 1

        updated += 1

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\nNLP scores updated for {updated:,} events.")
    print(f"  Positive: {score_dist['positive']:,}  "
          f"Neutral: {score_dist['neutral']:,}  "
          f"Negative: {score_dist['negative']:,}")

    # Show representative samples per event type
    print("\nSample scores:")
    for etype in ["contract", "FOIA"]:
        sample = [e for e in events if e.get("event_type") == etype][:3]
        for e in sample:
            s = e.get("signal", {})
            print(f"  [{etype}] score={s.get('nlp_sentiment_score'):.1f} "
                  f"compound={s.get('vader_compound'):.3f}  "
                  f"title: {e.get('event_title','')[:70]}")


if __name__ == "__main__":
    main()
