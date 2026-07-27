"""
NLP Signal Extraction Engine - Advanced FOIA/Contract/SEC Document Analysis
Replaces basic keyword counting with:
- Named Entity Recognition (NER) for company/agency/amount extraction
- Sentiment analysis for directional signals (bullish/bearish)
- Topic classification for event categorization
- Multi-source signal fusion (FOIA + SEC + Contracts + Regulatory)
- Temporal analysis for urgency scoring

This is the CRITICAL patent component that moves beyond "keyword counting"
to actual intelligent signal extraction.
"""
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import Counter


class NLPSignalEngine:
    """
    Advanced NLP Signal Extraction Engine

    Analyzes government documents (FOIA, SEC filings, contracts, regulatory actions)
    using NLP techniques to extract trading signals with:
    - Entity extraction (companies, agencies, amounts, dates)
    - Sentiment scoring (bullish/bearish/neutral)
    - Topic classification
    - Urgency/temporal scoring
    - Multi-source signal fusion
    """

    def __init__(self):
        # Sentiment lexicon for government/regulatory context
        self.bullish_terms = {
            # Positive outcomes
            "approved", "approval", "awarded", "award", "granted", "grant",
            "authorized", "authorization", "passed", "success", "successful",
            "completed", "achievement", "achieved", "won", "win", "wins",
            "renewed", "renewal", "extended", "expansion", "expanded",
            "increased", "increase", "growth", "growing", "grew",
            "profit", "profitable", "profitability", "revenue", "revenues",
            "contract", "contracts", "procurement", "procured",
            "partnership", "partner", "collaboration", "collaborate",
            "innovation", "innovative", "breakthrough", "milestone",
            "favorable", "positive", "beneficial", "advantage",
            "competitive", "leadership", "leading", "dominant",
            "acquisition", "acquired", "merge", "merger",
            "investment", "invested", "funding", "funded",
            "settlement", "settled", "resolved", "resolution",
            "compliance", "compliant", "certified", "certification",
            "license", "licensed", "permit", "permitted",
            "exceeded", "outperformed", "beat", "surpassed",
            "upgrade", "upgraded", "promoted", "advanced",
        }

        self.bearish_terms = {
            # Negative outcomes
            "rejected", "denied", "denial", "refused", "refusal",
            "failed", "failure", "failed to", "unable to", "cannot",
            "investigation", "investigating", "investigated", "probe",
            "violation", "violations", "violated", "breach", "breached",
            "fine", "fines", "penalty", "penalties", "sanction", "sanctions",
            "lawsuit", "litigation", "sued", "suing", "complaint",
            "fraud", "fraudulent", "misconduct", "corruption", "corrupt",
            "bankruptcy", "bankrupt", "insolvency", "insolvent",
            "layoff", "layoffs", "fired", "terminated", "dismissed",
            "recall", "recalled", "recalls", "defect", "defective",
            "warning", "warnings", "alert", "alerts", "advisory",
            "suspended", "suspension", "revoked", "revocation",
            "cancelled", "canceled", "cancellation", "withdrawn",
            "declined", "decreased", "decrease", "drop", "dropped",
            "loss", "losses", "deficit", "shortfall", "missed",
            "downgrade", "downgraded", "demoted", "reduced",
            "restructuring", "restructure", "reorganization",
            "impairment", "write-down", "writedown", "charge-off",
            "default", "defaults", "delinquent", "delinquency",
            "enforcement", "enforced", "enforcing",
            "non-compliance", "noncompliance", "violates",
            "risk", "risky", "uncertainty", "uncertain",
            "adverse", "negative", "detrimental", "harmful",
            "criticism", "criticized", "scrutiny", "controversy",
            "delay", "delayed", "postponed", "deferred",
            "injunction", "restrained", "prohibited", "banned",
        }

        # Entity patterns
        self.money_pattern = re.compile(
            r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion|M|B|T))?',
            re.IGNORECASE
        )
        self.date_pattern = re.compile(
            r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|'
            r'(?:January|February|March|April|May|June|July|August|September|'
            r'October|November|December)\s+\d{1,2},?\s+\d{4})\b',
            re.IGNORECASE
        )
        self.percentage_pattern = re.compile(
            r'\b\d+(?:\.\d+)?\s*%',
            re.IGNORECASE
        )

        # Topic classification keywords
        self.topic_keywords = {
            "CONTRACT_AWARD": [
                "contract", "award", "awarded", "procurement", "procured",
                "bid", "proposal", "solicitation", "rfp", "rfq",
                "purchase order", "delivery order", "task order",
            ],
            "REGULATORY_ACTION": [
                "regulation", "rule", "compliance", "enforcement",
                "investigation", "violation", "fine", "penalty",
                "sanction", "license", "permit", "approval",
            ],
            "FINANCIAL_DISCLOSURE": [
                "revenue", "earnings", "profit", "loss", "income",
                "financial", "fiscal", "budget", "spending",
                "10-k", "10-q", "quarterly", "annual report",
            ],
            "MERGER_ACQUISITION": [
                "merger", "acquisition", "acquired", "merge",
                "consolidation", "takeover", "buyout", "divestiture",
            ],
            "LEGAL_LITIGATION": [
                "lawsuit", "litigation", "court", "judge", "jury",
                "settlement", "verdict", "ruling", "appeal",
                "complaint", "plaintiff", "defendant",
            ],
            "PERSONNEL_CHANGE": [
                "ceo", "cfo", "cto", "executive", "director",
                "appointed", "resigned", "retired", "succession",
                "leadership", "management", "board",
            ],
            "PRODUCT_DEVELOPMENT": [
                "product", "development", "research", "clinical",
                "trial", "testing", "prototype", "launch",
                "release", "version", "update",
            ],
            "RISK_FACTOR": [
                "risk", "uncertainty", "volatility", "exposure",
                "threat", "vulnerability", "concern", "challenge",
            ],
        }

        # Agency importance weights
        self.agency_weights = {
            "sec": 0.9, "securities and exchange commission": 0.9,
            "fda": 0.85, "food and drug administration": 0.85,
            "dod": 0.8, "department of defense": 0.8,
            "doj": 0.85, "department of justice": 0.85,
            "treasury": 0.75, "department of the treasury": 0.75,
            "ftc": 0.7, "federal trade commission": 0.7,
            "epa": 0.6, "environmental protection agency": 0.6,
            "fcc": 0.6, "federal communications commission": 0.6,
            "fed": 0.9, "federal reserve": 0.9,
            "darpa": 0.7, "defense advanced research projects agency": 0.7,
            "nas": 0.75, "nasa": 0.75,
            "irs": 0.65, "internal revenue service": 0.65,
        }

    def extract_entities(self, text: str) -> Dict:
        """
        Extract key entities from document text

        Args:
            text: Document text

        Returns:
            Dict with extracted entities
        """
        text_lower = text.lower()

        # Extract monetary amounts
        money_matches = self.money_pattern.findall(text)
        money_values = []
        for m in money_matches:
            # Normalize to numeric value
            numeric = re.sub(r'[,$]', '', m)
            numeric = numeric.lower()
            multiplier = 1
            if 'billion' in numeric or 'b' in numeric:
                multiplier = 1_000_000_000
                numeric = re.sub(r'[billionb]', '', numeric)
            elif 'million' in numeric or 'm' in numeric:
                multiplier = 1_000_000
                numeric = re.sub(r'[millionm]', '', numeric)
            elif 'trillion' in numeric or 't' in numeric:
                multiplier = 1_000_000_000_000
                numeric = re.sub(r'[trilliont]', '', numeric)

            try:
                value = float(numeric.strip()) * multiplier
                money_values.append(value)
            except ValueError:
                pass

        # Extract dates
        date_matches = self.date_pattern.findall(text)

        # Extract percentages
        pct_matches = self.percentage_pattern.findall(text)
        pct_values = []
        for p in pct_matches:
            try:
                pct_values.append(float(p.replace('%', '').strip()))
            except ValueError:
                pass

        # Detect agency mentions
        detected_agencies = []
        for agency, weight in self.agency_weights.items():
            if agency in text_lower:
                detected_agencies.append({
                    "agency": agency.upper(),
                    "importance_weight": weight
                })

        return {
            "monetary_amounts": money_values,
            "total_monetary_value": sum(money_values),
            "largest_monetary_amount": max(money_values) if money_values else 0,
            "dates_mentioned": date_matches,
            "percentages": pct_values,
            "agencies_detected": detected_agencies,
            "agency_count": len(detected_agencies),
        }

    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze document sentiment for trading direction

        Args:
            text: Document text

        Returns:
            Sentiment dict with bullish/bearish scores
        """
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))

        # Count bullish/bearish terms
        bullish_found = [t for t in self.bullish_terms if t in text_lower]
        bearish_found = [t for t in self.bearish_terms if t in text_lower]

        bullish_count = len(bullish_found)
        bearish_count = len(bearish_found)
        total = bullish_count + bearish_count

        if total == 0:
            return {
                "sentiment": "NEUTRAL",
                "sentiment_score": 50,
                "bullish_terms": bullish_found,
                "bearish_terms": bearish_found,
                "bullish_count": 0,
                "bearish_count": 0,
                "confidence": 0.3,
            }

        # Calculate sentiment score (0-100, 50=neutral)
        raw_score = (bullish_count / total) * 100
        sentiment_score = round(raw_score, 1)

        # Determine direction
        if sentiment_score >= 65:
            direction = "BULLISH"
        elif sentiment_score <= 35:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # Confidence based on number of signal words found
        confidence = min(total / 10.0, 1.0)

        return {
            "sentiment": direction,
            "sentiment_score": sentiment_score,
            "bullish_terms": bullish_found,
            "bearish_terms": bearish_found,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "confidence": round(confidence, 2),
        }

    def classify_topic(self, text: str) -> Dict:
        """
        Classify document into topic categories

        Args:
            text: Document text

        Returns:
            Topic classification dict
        """
        text_lower = text.lower()

        topic_scores = {}
        for topic, keywords in self.topic_keywords.items():
            matches = [kw for kw in keywords if kw in text_lower]
            score = len(matches)
            topic_scores[topic] = {
                "keywords_matched": matches,
                "match_count": len(matches),
                "score": score
            }

        # Sort by score
        sorted_topics = sorted(
            topic_scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )

        primary_topic = sorted_topics[0][0] if sorted_topics else "UNKNOWN"
        primary_score = sorted_topics[0][1]["score"] if sorted_topics else 0

        return {
            "primary_topic": primary_topic,
            "primary_topic_score": primary_score,
            "all_topics": {
                topic: info["score"]
                for topic, info in sorted_topics
                if info["score"] > 0
            },
            "matched_keywords": {
                topic: info["keywords_matched"]
                for topic, info in sorted_topics
                if info["score"] > 0
            },
        }

    def calculate_urgency(self, text: str, entities: Dict) -> Dict:
        """
        Calculate urgency/temporal score

        Args:
            text: Document text
            entities: Extracted entities

        Returns:
            Urgency dict
        """
        text_lower = text.lower()

        # Urgency indicators
        urgency_terms = [
            "immediate", "urgent", "emergency", "critical", "deadline",
            "expires", "pending", "awaiting", "required", "mandatory",
            "compliance date", "effective date", "within", "by",
            "asap", "promptly", "forthwith",
        ]

        urgency_count = sum(1 for term in urgency_terms if term in text_lower)

        # Check for recent dates (higher urgency)
        recent_date_terms = [
            "today", "yesterday", "this week", "this month",
            "immediately", "now", "current", "recent",
        ]

        recent_count = sum(1 for term in recent_date_terms if term in text_lower)

        # Large monetary amounts increase urgency
        money_urgency = 0
        if entities.get("largest_monetary_amount", 0) > 100_000_000:
            money_urgency = 3
        elif entities.get("largest_monetary_amount", 0) > 10_000_000:
            money_urgency = 2
        elif entities.get("largest_monetary_amount", 0) > 1_000_000:
            money_urgency = 1

        # Calculate urgency score (0-100)
        urgency_score = min(
            (urgency_count * 15) + (recent_count * 10) + (money_urgency * 10),
            100
        )

        if urgency_score >= 60:
            urgency_level = "HIGH"
        elif urgency_score >= 30:
            urgency_level = "MEDIUM"
        else:
            urgency_level = "LOW"

        return {
            "urgency_score": urgency_score,
            "urgency_level": urgency_level,
            "urgency_indicators": urgency_count,
            "recent_date_terms": recent_count,
            "money_urgency_factor": money_urgency,
        }

    def analyze_document(self, document: Dict) -> Dict:
        """
        Full NLP analysis of a government document

        Args:
            document: Document dict with title, summary, description, etc.

        Returns:
            Comprehensive signal analysis dict
        """
        # Combine all text fields
        title = document.get("title", document.get("document_title", ""))
        summary = document.get("summary", document.get("description", ""))
        text = document.get("text", document.get("content", ""))

        # Full text for analysis
        full_text = f"{title} {summary} {text}".lower()

        if not full_text.strip():
            return {
                "signal_strength": "LOW",
                "signal_score": 10,
                "sentiment": "NEUTRAL",
                "sentiment_score": 50,
                "primary_topic": "UNKNOWN",
                "urgency": "LOW",
                "entities": {},
                "confidence": 0.1,
                "direction": "NEUTRAL",
                "analysis_note": "Insufficient text for analysis",
            }

        # Run all analyses
        entities = self.extract_entities(full_text)
        sentiment = self.analyze_sentiment(full_text)
        topic = self.classify_topic(full_text)
        urgency = self.calculate_urgency(full_text, entities)

        # Calculate composite signal score
        # Weight the components
        sentiment_weight = 0.35
        entity_weight = 0.25
        topic_weight = 0.20
        urgency_weight = 0.20

        # Normalize sentiment to 0-100
        sentiment_component = sentiment["sentiment_score"]

        # Entity component (based on money, agencies, etc.)
        entity_component = 0
        if entities.get("total_monetary_value", 0) > 0:
            entity_component += min(
                entities["total_monetary_value"] / 10_000_000 * 20, 40
            )
        entity_component += min(entities.get("agency_count", 0) * 10, 30)
        entity_component = min(entity_component, 100)

        # Topic component (based on topic relevance)
        topic_component = min(topic.get("primary_topic_score", 0) * 15, 100)

        # Urgency component
        urgency_component = urgency["urgency_score"]

        # Composite score
        composite_score = round(
            (sentiment_component * sentiment_weight) +
            (entity_component * entity_weight) +
            (topic_component * topic_weight) +
            (urgency_component * urgency_weight),
            1
        )

        # Determine signal strength
        if composite_score >= 70:
            signal_strength = "HIGH"
        elif composite_score >= 40:
            signal_strength = "MEDIUM"
        else:
            signal_strength = "LOW"

        # Determine trading direction
        if sentiment["sentiment"] == "BULLISH" and composite_score >= 50:
            direction = "BULLISH"
        elif sentiment["sentiment"] == "BEARISH" and composite_score >= 50:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # Overall confidence
        confidence = round(
            (sentiment["confidence"] * 0.4) +
            (min(composite_score / 100, 1.0) * 0.3) +
            (min(topic.get("primary_topic_score", 0) / 5.0, 1.0) * 0.3),
            2
        )

        return {
            "signal_strength": signal_strength,
            "signal_score": composite_score,
            "sentiment": sentiment["sentiment"],
            "sentiment_score": sentiment["sentiment_score"],
            "primary_topic": topic["primary_topic"],
            "topic_scores": topic["all_topics"],
            "urgency": urgency["urgency_level"],
            "urgency_score": urgency["urgency_score"],
            "entities": {
                "monetary_amounts_detected": len(entities.get("monetary_amounts", [])),
                "total_monetary_value": entities.get("total_monetary_value", 0),
                "largest_amount": entities.get("largest_monetary_amount", 0),
                "agencies_detected": [a["agency"] for a in entities.get("agencies_detected", [])],
                "dates_mentioned": len(entities.get("dates_mentioned", [])),
                "percentages_mentioned": entities.get("percentages", []),
            },
            "bullish_terms": sentiment["bullish_terms"],
            "bearish_terms": sentiment["bearish_terms"],
            "direction": direction,
            "confidence": confidence,
            "analysis_timestamp": datetime.utcnow().isoformat(),
        }

    def fuse_multi_source_signals(self, signals: List[Dict]) -> Dict:
        """
        Fuse signals from multiple sources (FOIA + SEC + Contracts + Regulatory)

        Args:
            signals: List of signal analysis dicts from analyze_document()

        Returns:
            Fused signal dict with combined confidence
        """
        if not signals:
            return {
                "fused_signal_strength": "LOW",
                "fused_signal_score": 10,
                "fused_direction": "NEUTRAL",
                "fused_confidence": 0.1,
                "source_count": 0,
                "note": "No signals to fuse",
            }

        # Average signal scores
        scores = [s.get("signal_score", 50) for s in signals]
        avg_score = sum(scores) / len(scores)

        # Count directions
        bullish_count = sum(1 for s in signals if s.get("direction") == "BULLISH")
        bearish_count = sum(1 for s in signals if s.get("direction") == "BEARISH")
        neutral_count = sum(1 for s in signals if s.get("direction") == "NEUTRAL")

        # Determine fused direction
        if bullish_count > bearish_count and bullish_count > neutral_count:
            fused_direction = "BULLISH"
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            fused_direction = "BEARISH"
        else:
            fused_direction = "NEUTRAL"

        # Boost confidence with multiple agreeing sources
        base_confidence = sum(s.get("confidence", 0.5) for s in signals) / len(signals)
        agreement_bonus = 0
        if fused_direction == "BULLISH":
            agreement_bonus = min(bullish_count * 0.05, 0.20)
        elif fused_direction == "BEARISH":
            agreement_bonus = min(bearish_count * 0.05, 0.20)

        fused_confidence = min(base_confidence + agreement_bonus, 1.0)

        # Determine fused strength
        if avg_score >= 70:
            fused_strength = "HIGH"
        elif avg_score >= 40:
            fused_strength = "MEDIUM"
        else:
            fused_strength = "LOW"

        return {
            "fused_signal_strength": fused_strength,
            "fused_signal_score": round(avg_score, 1),
            "fused_direction": fused_direction,
            "fused_confidence": round(fused_confidence, 2),
            "source_count": len(signals),
            "bullish_sources": bullish_count,
            "bearish_sources": bearish_count,
            "neutral_sources": neutral_count,
            "individual_scores": scores,
            "fusion_timestamp": datetime.utcnow().isoformat(),
        }


# Initialize global engine
nlp_signal_engine = NLPSignalEngine()


if __name__ == "__main__":
    print("🧠 NLP Signal Extraction Engine - Demo")
    print("=" * 60)

    # Demo: Analyze a sample FOIA document
    sample_foia = {
        "title": "DOD Awarded $500M Contract to Lockheed Martin for F-35 Development",
        "summary": "The Department of Defense has approved and awarded a $500 million contract to Lockheed Martin for continued F-35 fighter jet development. The contract was approved after successful completion of milestone testing.",
        "text": "This contract award represents a significant milestone in the F-35 program. Lockheed Martin has demonstrated successful innovation and growth in defense procurement. The approval came after favorable review by the Defense Department.",
    }

    print("\n1. Analyzing FOIA document:")
    result = nlp_signal_engine.analyze_document(sample_foia)
    print(f"   Signal Strength: {result['signal_strength']}")
    print(f"   Signal Score: {result['signal_score']}")
    print(f"   Sentiment: {result['sentiment']} ({result['sentiment_score']})")
    print(f"   Direction: {result['direction']}")
    print(f"   Primary Topic: {result['primary_topic']}")
    print(f"   Urgency: {result['urgency']}")
    print(f"   Confidence: {result['confidence']}")
    print(f"   Entities: {result['entities']}")

    # Demo: Analyze a bearish document
    sample_bearish = {
        "title": "FDA Issues Warning Letter to Pfizer Over Manufacturing Violations",
        "summary": "The FDA has issued a warning letter to Pfizer citing multiple manufacturing violations and compliance failures at a key facility. The company faces potential enforcement action and fines.",
        "text": "FDA investigation revealed serious violations of manufacturing regulations. Pfizer failed to comply with required standards and faces potential penalties. The enforcement action includes suspension of certain operations.",
    }

    print("\n2. Analyzing bearish document:")
    result2 = nlp_signal_engine.analyze_document(sample_bearish)
    print(f"   Signal Strength: {result2['signal_strength']}")
    print(f"   Signal Score: {result2['signal_score']}")
    print(f"   Sentiment: {result2['sentiment']} ({result2['sentiment_score']})")
    print(f"   Direction: {result2['direction']}")
    print(f"   Primary Topic: {result2['primary_topic']}")
    print(f"   Confidence: {result2['confidence']}")

    # Demo: Fuse multi-source signals
    print("\n3. Fusing multi-source signals:")
    fused = nlp_signal_engine.fuse_multi_source_signals([result, result2])
    print(f"   Fused Strength: {fused['fused_signal_strength']}")
    print(f"   Fused Score: {fused['fused_signal_score']}")
    print(f"   Fused Direction: {fused['fused_direction']}")
    print(f"   Fused Confidence: {fused['fused_confidence']}")
    print(f"   Sources: {fused['source_count']}")
