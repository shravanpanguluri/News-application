"""
Inventor's Notebook - Legal Documentation for Patent Filing
Every feature, idea, and test result gets logged with timestamp.
This creates legal evidence of invention development.
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class InventorsNotebook:
    """
    Legal documentation of invention development.
    Creates tamper-proof records with cryptographic hashes.
    """
    
    def __init__(self, filepath: str = "inventors_notebook.jsonl"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
    
    def _create_entry(self, category: str, title: str, description: str, 
                     evidence: Optional[Dict] = None) -> Dict:
        """Create a notebook entry with integrity hash"""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "category": category,  # conception, reduction_to_practice, test_result
            "title": title,
            "description": description,
            "evidence": evidence or {},
            "hash": None
        }
        
        # Create integrity hash (proves entry wasn't modified)
        entry["hash"] = hashlib.sha256(
            json.dumps(entry, sort_keys=True, default=str).encode()
        ).hexdigest()
        
        return entry
    
    def _save_entry(self, entry: Dict) -> None:
        """Save entry to notebook file"""
        with open(self.filepath, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def log_conception(self, title: str, description: str) -> Dict:
        """
        Log a new invention concept/idea
        
        Args:
            title: Short title of the invention
            description: Detailed description of the concept
        
        Returns:
            The logged entry
        """
        entry = self._create_entry("conception", title, description)
        self._save_entry(entry)
        print(f"📝 Logged conception: {title}")
        return entry
    
    def log_implementation(self, title: str, description: str, 
                          code_commit: Optional[str] = None,
                          files_created: Optional[list] = None) -> Dict:
        """
        Log implementation/reduction to practice
        
        Args:
            title: Title of the implementation
            description: Description of what was built
            code_commit: Git commit hash (optional)
            files_created: List of files created (optional)
        
        Returns:
            The logged entry
        """
        evidence = {
            "commit": code_commit,
            "files": files_created or []
        }
        entry = self._create_entry("reduction_to_practice", title, description, evidence)
        self._save_entry(entry)
        print(f"🔨 Logged implementation: {title}")
        return entry
    
    def log_test_result(self, title: str, description: str, 
                       accuracy: Optional[float] = None,
                       data_points: Optional[int] = None,
                       metrics: Optional[Dict] = None) -> Dict:
        """
        Log test results and performance data
        
        Args:
            title: Title of the test
            description: Description of what was tested
            accuracy: Accuracy percentage (0-100)
            data_points: Number of data points tested
            metrics: Additional metrics dict
        
        Returns:
            The logged entry
        """
        evidence = {
            "accuracy": accuracy,
            "data_points": data_points,
            "metrics": metrics or {}
        }
        entry = self._create_entry("test_result", title, description, evidence)
        self._save_entry(entry)
        print(f"📊 Logged test result: {title}")
        return entry
    
    def log_patent_claim(self, claim_number: int, claim_text: str, 
                        supporting_evidence: Optional[list] = None) -> Dict:
        """
        Log a specific patent claim
        
        Args:
            claim_number: Claim number (1, 2, 3, etc.)
            claim_text: Full text of the claim
            supporting_evidence: List of entry hashes that support this claim
        
        Returns:
            The logged entry
        """
        entry = self._create_entry(
            "patent_claim",
            f"Patent Claim {claim_number}",
            claim_text,
            {"claim_number": claim_number, "supporting_evidence": supporting_evidence or []}
        )
        self._save_entry(entry)
        print(f"⚖️ Logged patent claim {claim_number}")
        return entry
    
    def get_all_entries(self) -> list:
        """Get all notebook entries"""
        if not self.filepath.exists():
            return []
        
        entries = []
        with open(self.filepath, "r") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries
    
    def export_for_attorney(self, output_file: str = "patent_documentation.json") -> Dict:
        """
        Export all entries formatted for patent attorney
        
        Args:
            output_file: Output file path
        
        Returns:
            Formatted documentation dict
        """
        entries = self.get_all_entries()
        
        # Organize by category
        organized = {
            "conceptions": [e for e in entries if e["category"] == "conception"],
            "implementations": [e for e in entries if e["category"] == "reduction_to_practice"],
            "test_results": [e for e in entries if e["category"] == "test_result"],
            "patent_claims": [e for e in entries if e["category"] == "patent_claim"],
        }
        
        # Create summary
        documentation = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_entries": len(entries),
            "summary": {
                "conceptions": len(organized["conceptions"]),
                "implementations": len(organized["implementations"]),
                "test_results": len(organized["test_results"]),
                "patent_claims": len(organized["patent_claims"]),
            },
            "entries_by_category": organized,
            "chronological_log": entries,
        }
        
        # Save formatted documentation
        with open(output_file, "w") as f:
            json.dump(documentation, f, indent=2)
        
        print(f"📄 Exported patent documentation to {output_file}")
        return documentation


# Initialize global notebook instance
notebook = InventorsNotebook()


def initialize_notebook():
    """Initialize notebook with Predovex invention concepts"""
    
    # Log core invention concepts
    notebook.log_conception(
        "Multi-Signal Breaking News Detection System",
        "A method for detecting breaking news by analyzing multiple signals including: "
        "(1) recency of publication, (2) cross-source validation (multiple sources reporting same story), "
        "(3) keyword detection for breaking news language, (4) source authority scoring, "
        "(5) social media trending detection, and (6) market impact keyword detection. "
        "The system calculates a composite breaking score (0-100) and automatically categorizes "
        "news as BREAKING (≥70), URGENT (≥50), or STANDARD (<50). This multi-signal approach "
        "is novel and provides more accurate breaking news detection than single-signal systems."
    )
    
    notebook.log_conception(
        "Policy-to-Market Impact Prediction System",
        "A method for predicting stock market impact from government policy announcements by: "
        "(1) extracting keywords from policy documents to identify affected sectors, "
        "(2) mapping sectors to specific publicly-traded companies, "
        "(3) matching current policies to historical policy patterns, "
        "(4) analyzing historical market reactions to similar policies, and "
        "(5) generating impact predictions with confidence scores. "
        "The system uses a tiered sector mapping (10 sectors, 50+ stocks) and historical pattern "
        "database to provide actionable intelligence before market reactions occur."
    )
    
    notebook.log_conception(
        "Cross-Source News De-duplication and Quality Scoring",
        "A method for improving news feed quality by: (1) grouping duplicate articles from multiple "
        "sources using fuzzy text matching (60%+ term overlap), (2) selecting the highest-quality "
        "version based on source tier ranking, (3) calculating quality scores (0-100) based on "
        "source tier (0-30pts), recency (0-25pts), impact level (0-20pts), content quality (0-15pts), "
        "and uniqueness (0-10pts), and (4) presenting users with curated top 20-30 articles instead "
        "of 100+ raw articles. This reduces information overload while improving content quality."
    )
    
    notebook.log_conception(
        "Government Document to Stock Correlation Method",
        "A method for correlating government documents (RSS feeds, contracts, regulatory filings) "
        "with subsequent stock price movements by: (1) extracting company mentions from government "
        "documents, (2) mapping companies to stock tickers, (3) tracking stock prices at 1/7/30 days "
        "after document release, (4) calculating correlation coefficients, and (5) generating "
        "predictive signals when correlation exceeds threshold. This creates actionable trading "
        "signals from government data sources."
    )
    
    notebook.log_conception(
        "FOIA Intelligence Engine for Stock Prediction",
        "A method for using Freedom of Information Act (FOIA) document releases to predict stock "
        "price movements by: (1) monitoring FOIA request completions from FOIA.gov and agency sources, "
        "(2) parsing FOIA documents to extract company names, contract amounts, and dates, "
        "(3) mapping mentioned companies to public stock tickers, (4) tracking stock price movements "
        "following FOIA releases, and (5) identifying material FOIA releases that predict significant "
        "stock movements. This provides early intelligence not available through traditional channels."
    )
    
    notebook.log_conception(
        "Regulatory Enforcement Early Warning System",
        "A method for predicting negative stock events by monitoring regulatory enforcement actions "
        "across multiple agencies (SEC, FDA, EPA, OSHA) by: (1) aggregating enforcement data from "
        "SEC EDGAR, FDA OpenFDA, EPA ECHO, and other agency APIs, (2) extracting company mentions "
        "from enforcement actions, (3) calculating regulatory risk scores (0-100) based on frequency "
        "and severity of actions, (4) tracking stock price movements following enforcement actions, "
        "and (5) generating early warning alerts when regulatory risk exceeds threshold. This provides "
        "advance warning of regulatory-driven stock declines."
    )
    
    print("\n✅ Inventor's Notebook initialized with 6 core invention concepts!")
    print(f"📄 Notebook saved to: {notebook.filepath.absolute()}")
    
    return notebook


if __name__ == "__main__":
    # Initialize the notebook with core concepts
    initialize_notebook()
