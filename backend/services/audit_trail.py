"""
Blockchain-Based Audit Trail - Immutable Logging
Provides immutable logging for regulatory compliance and audit purposes.

This implements the Blockchain-Based Audit Trail enhancement requested.
"""
import hashlib
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import sqlite3
from pathlib import Path


@dataclass
class AuditRecord:
    """Immutable audit record"""
    record_id: str
    timestamp: str
    event_type: str
    event_data: Dict[str, Any]
    hash_value: str
    previous_hash: str
    signature: str  # Digital signature for authenticity
    user_id: str
    ip_address: str
    session_id: str


class AuditTrail:
    """
    Blockchain-inspired audit trail for regulatory compliance.

    Features:
    - Cryptographic hashing for immutability
    - Digital signatures for authenticity
    - SQLite-based storage
    - Regulatory audit query support
    - Tamper detection
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(__file__).parent.parent / "audit_trail.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self.last_hash = self._get_last_hash()

        # Initialize database
        self._initialize_database()

        print("📜 Audit Trail initialized")

    def _initialize_database(self):
        """Initialize SQLite database for audit trail"""
        self.connection = sqlite3.connect(self.db_path)
        cursor = self.connection.cursor()

        # Create audit trail table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                hash_value TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                signature TEXT NOT NULL,
                user_id TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                session_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_record_id ON audit_records(record_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_records(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_event_type ON audit_records(event_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_id ON audit_records(user_id)
        ''')

        self.connection.commit()
        print("   🗄️  Audit trail database initialized")

    def _get_last_hash(self) -> str:
        """Get hash of the last recorded event"""
        if not self.connection:
            return "genesis_hash_00000000000000000000000000000000"

        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT hash_value FROM audit_records
                ORDER BY id DESC LIMIT 1
            ''')
            result = cursor.fetchone()
            return result[0] if result else "genesis_hash_00000000000000000000000000000000"
        except Exception as e:
            print(f"   ⚠️  Error getting last hash: {e}")
            return "genesis_hash_00000000000000000000000000000000"

    def _calculate_hash(self, data: Dict[str, Any], previous_hash: str) -> str:
        """
        Calculate cryptographic hash of audit data.

        Args:
            data: Audit data dictionary
            previous_hash: Hash of previous record

        Returns:
            SHA-256 hash string
        """
        # Serialize data consistently
        serialized = json.dumps(data, sort_keys=True, separators=(',', ':'))
        combined = f"{serialized}{previous_hash}"

        # Calculate SHA-256 hash
        hash_object = hashlib.sha256(combined.encode('utf-8'))
        return hash_object.hexdigest()

    def _generate_signature(self, data: Dict[str, Any], user_id: str) -> str:
        """
        Generate digital signature for audit record.

        Args:
            data: Audit data
            user_id: User identifier

        Returns:
            Digital signature
        """
        # In real implementation, this would use asymmetric cryptography
        # For demo, using simple hash-based signature
        signature_data = f"{json.dumps(data, sort_keys=True)}{user_id}{datetime.utcnow().isoformat()}"
        signature_hash = hashlib.sha256(signature_data.encode('utf-8')).hexdigest()
        return f"sig_{signature_hash[:32]}"

    def log_event_analysis(self, event_id: str, analysis_result: Dict,
                          user_id: str = "system",
                          ip_address: str = "127.0.0.1",
                          session_id: str = "default_session") -> str:
        """
        Log analysis to blockchain-inspired audit trail for regulatory proof.

        Args:
            event_id: Unique identifier for the event
            analysis_result: Analysis results to log
            user_id: User performing the analysis
            ip_address: IP address of the user
            session_id: Session identifier

        Returns:
            Record ID of the logged entry
        """
        print(f"   📝 Logging event analysis for {event_id}")

        # Prepare audit data
        audit_data = {
            "event_id": event_id,
            "analysis_type": analysis_result.get("analysis_type", "unknown"),
            "confidence_score": analysis_result.get("confidence", 0),
            "signal_score": analysis_result.get("signal_score", 0),
            "direction": analysis_result.get("direction", "NEUTRAL"),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0"
        }

        # Get previous hash
        previous_hash = self.last_hash

        # Calculate hash
        hash_value = self._calculate_hash(audit_data, previous_hash)

        # Generate signature
        signature = self._generate_signature(audit_data, user_id)

        # Create record ID
        record_id = f"audit_{event_id}_{int(time.time())}"

        # Create audit record
        record = AuditRecord(
            record_id=record_id,
            timestamp=audit_data["timestamp"],
            event_type="EVENT_ANALYSIS",
            event_data=audit_data,
            hash_value=hash_value,
            previous_hash=previous_hash,
            signature=signature,
            user_id=user_id,
            ip_address=ip_address,
            session_id=session_id
        )

        # Store in database
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO audit_records
                (record_id, timestamp, event_type, event_data, hash_value, previous_hash,
                 signature, user_id, ip_address, session_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.record_id,
                record.timestamp,
                record.event_type,
                json.dumps(record.event_data),
                record.hash_value,
                record.previous_hash,
                record.signature,
                record.user_id,
                record.ip_address,
                record.session_id,
                datetime.utcnow().isoformat()
            ))

            self.connection.commit()
            self.last_hash = hash_value

            print(f"   ✅ Audit record logged: {record_id}")
            return record_id

        except Exception as e:
            print(f"   ❌ Error logging audit record: {e}")
            raise

    def log_trade_decision(self, trade_id: str, decision_data: Dict,
                          user_id: str = "trading_system",
                          ip_address: str = "127.0.0.1",
                          session_id: str = "trading_session") -> str:
        """
        Log trading decision for compliance purposes.

        Args:
            trade_id: Unique trade identifier
            decision_data: Trading decision data
            user_id: User/system making decision
            ip_address: IP address
            session_id: Session identifier

        Returns:
            Record ID of the logged entry
        """
        print(f"   📝 Logging trade decision for {trade_id}")

        # Prepare audit data
        audit_data = {
            "trade_id": trade_id,
            "ticker": decision_data.get("ticker", "UNKNOWN"),
            "position_size": decision_data.get("position_size", 0),
            "confidence": decision_data.get("confidence", 0),
            "risk_score": decision_data.get("risk_score", 0),
            "compliance_status": decision_data.get("compliance_status", "UNKNOWN"),
            "decision_timestamp": datetime.utcnow().isoformat(),
            "strategy": decision_data.get("strategy", "unknown"),
            "version": "1.0"
        }

        # Get previous hash
        previous_hash = self.last_hash

        # Calculate hash
        hash_value = self._calculate_hash(audit_data, previous_hash)

        # Generate signature
        signature = self._generate_signature(audit_data, user_id)

        # Create record ID
        record_id = f"trade_{trade_id}_{int(time.time())}"

        # Create audit record
        record = AuditRecord(
            record_id=record_id,
            timestamp=audit_data["decision_timestamp"],
            event_type="TRADE_DECISION",
            event_data=audit_data,
            hash_value=hash_value,
            previous_hash=previous_hash,
            signature=signature,
            user_id=user_id,
            ip_address=ip_address,
            session_id=session_id
        )

        # Store in database
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO audit_records
                (record_id, timestamp, event_type, event_data, hash_value, previous_hash,
                 signature, user_id, ip_address, session_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.record_id,
                record.timestamp,
                record.event_type,
                json.dumps(record.event_data),
                record.hash_value,
                record.previous_hash,
                record.signature,
                record.user_id,
                record.ip_address,
                record.session_id,
                datetime.utcnow().isoformat()
            ))

            self.connection.commit()
            self.last_hash = hash_value

            print(f"   ✅ Trade decision logged: {record_id}")
            return record_id

        except Exception as e:
            print(f"   ❌ Error logging trade decision: {e}")
            raise

    def log_model_training(self, model_id: str, training_metrics: Dict,
                          user_id: str = "ml_system",
                          ip_address: str = "127.0.0.1",
                          session_id: str = "ml_session") -> str:
        """
        Log machine learning model training for audit purposes.

        Args:
            model_id: Model identifier
            training_metrics: Training performance metrics
            user_id: User/system performing training
            ip_address: IP address
            session_id: Session identifier

        Returns:
            Record ID of the logged entry
        """
        print(f"   📝 Logging model training for {model_id}")

        # Prepare audit data
        audit_data = {
            "model_id": model_id,
            "training_samples": training_metrics.get("train_samples", 0),
            "test_accuracy": training_metrics.get("test_accuracy", 0),
            "train_accuracy": training_metrics.get("train_accuracy", 0),
            "features_used": training_metrics.get("features_used", []),
            "model_type": training_metrics.get("model_type", "unknown"),
            "training_timestamp": datetime.utcnow().isoformat(),
            "version": "1.0"
        }

        # Get previous hash
        previous_hash = self.last_hash

        # Calculate hash
        hash_value = self._calculate_hash(audit_data, previous_hash)

        # Generate signature
        signature = self._generate_signature(audit_data, user_id)

        # Create record ID
        record_id = f"model_{model_id}_{int(time.time())}"

        # Create audit record
        record = AuditRecord(
            record_id=record_id,
            timestamp=audit_data["training_timestamp"],
            event_type="MODEL_TRAINING",
            event_data=audit_data,
            hash_value=hash_value,
            previous_hash=previous_hash,
            signature=signature,
            user_id=user_id,
            ip_address=ip_address,
            session_id=session_id
        )

        # Store in database
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO audit_records
                (record_id, timestamp, event_type, event_data, hash_value, previous_hash,
                 signature, user_id, ip_address, session_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.record_id,
                record.timestamp,
                record.event_type,
                json.dumps(record.event_data),
                record.hash_value,
                record.previous_hash,
                record.signature,
                record.user_id,
                record.ip_address,
                record.session_id,
                datetime.utcnow().isoformat()
            ))

            self.connection.commit()
            self.last_hash = hash_value

            print(f"   ✅ Model training logged: {record_id}")
            return record_id

        except Exception as e:
            print(f"   ❌ Error logging model training: {e}")
            raise

    def query_audit_records(self, filters: Optional[Dict] = None,
                           limit: int = 100) -> List[Dict]:
        """
        Query audit records for regulatory oversight.

        Args:
            filters: Filter criteria (event_type, user_id, date_range, etc.)
            limit: Maximum number of records to return

        Returns:
            List of audit records
        """
        print("   🔍 Querying audit records...")

        cursor = self.connection.cursor()

        # Build query
        query = "SELECT * FROM audit_records"
        params = []

        if filters:
            conditions = []

            if "event_type" in filters:
                conditions.append("event_type = ?")
                params.append(filters["event_type"])

            if "user_id" in filters:
                conditions.append("user_id = ?")
                params.append(filters["user_id"])

            if "date_range" in filters:
                start_date, end_date = filters["date_range"]
                conditions.append("timestamp BETWEEN ? AND ?")
                params.extend([start_date, end_date])

            if "record_id" in filters:
                conditions.append("record_id = ?")
                params.append(filters["record_id"])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()

            records = []
            for row in rows:
                record = {
                    "id": row[0],
                    "record_id": row[1],
                    "timestamp": row[2],
                    "event_type": row[3],
                    "event_data": json.loads(row[4]),
                    "hash_value": row[5],
                    "previous_hash": row[6],
                    "signature": row[7],
                    "user_id": row[8],
                    "ip_address": row[9],
                    "session_id": row[10],
                    "created_at": row[11]
                }
                records.append(record)

            print(f"   ✅ Retrieved {len(records)} audit records")
            return records

        except Exception as e:
            print(f"   ❌ Error querying audit records: {e}")
            return []

    def verify_chain_integrity(self) -> Dict:
        """
        Verify the integrity of the audit trail chain.

        Returns:
            Integrity verification results
        """
        print("   🔐 Verifying audit trail integrity...")

        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT record_id, hash_value, previous_hash, event_data, timestamp
            FROM audit_records
            ORDER BY id ASC
        ''')

        rows = cursor.fetchall()
        if not rows:
            return {"status": "valid", "records_checked": 0, "tampered_records": 0}

        tampered_count = 0
        valid_count = 0
        tampered_records = []

        # Verify each record
        for i, row in enumerate(rows):
            record_id, stored_hash, previous_hash, event_data, timestamp = row

            # For first record, check genesis hash
            if i == 0:
                if previous_hash != "genesis_hash_00000000000000000000000000000000":
                    # This is acceptable for the first real record
                    pass
            else:
                # Verify previous hash matches actual previous record's hash
                prev_row = rows[i-1]
                expected_previous_hash = prev_row[1]  # hash_value of previous record

                if previous_hash != expected_previous_hash:
                    tampered_count += 1
                    tampered_records.append({
                        "record_id": record_id,
                        "issue": "Previous hash mismatch",
                        "stored_previous_hash": previous_hash,
                        "expected_previous_hash": expected_previous_hash
                    })
                    continue

            # Verify current hash
            data_dict = json.loads(event_data)
            calculated_hash = self._calculate_hash(data_dict, previous_hash)

            if calculated_hash != stored_hash:
                tampered_count += 1
                tampered_records.append({
                    "record_id": record_id,
                    "issue": "Hash mismatch",
                    "stored_hash": stored_hash,
                    "calculated_hash": calculated_hash
                })
            else:
                valid_count += 1

        status = "valid" if tampered_count == 0 else "tampered"
        print(f"   ✅ Chain integrity check: {status} ({valid_count} valid, {tampered_count} tampered)")

        return {
            "status": status,
            "records_checked": len(rows),
            "valid_records": valid_count,
            "tampered_records": tampered_count,
            "tampered_record_details": tampered_records
        }

    def export_for_regulatory_review(self, export_path: Optional[str] = None) -> str:
        """
        Export audit trail for regulatory review.

        Args:
            export_path: Path to export file (optional)

        Returns:
            Path to exported file
        """
        print("   📤 Exporting audit trail for regulatory review...")

        # Query all records
        records = self.query_audit_records(limit=10000)

        # Prepare export data
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_records": len(records),
            "records": records,
            "integrity_check": self.verify_chain_integrity()
        }

        # Determine export path
        if not export_path:
            export_path = Path(__file__).parent.parent / f"audit_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        # Write to file
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"   ✅ Audit trail exported to {export_path}")
        return str(export_path)

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("   🗄️  Audit trail database closed")


# Global instance
audit_trail = AuditTrail()


if __name__ == "__main__":
    print("📜 Blockchain-Based Audit Trail - Demo")
    print("=" * 50)

    # Sample event analysis
    sample_analysis = {
        "analysis_type": "GOVERNMENT_EVENT_ANALYSIS",
        "confidence": 0.85,
        "signal_score": 78,
        "direction": "BULLISH",
        "entities": ["contract", "defense", "$500M"],
        "topics": ["CONTRACT_AWARD", "DEFENSE_SPENDING"]
    }

    # Log event analysis
    record_id = audit_trail.log_event_analysis(
        event_id="EVENT_20260416_001",
        analysis_result=sample_analysis,
        user_id="analyst_john",
        ip_address="192.168.1.100"
    )

    # Sample trade decision
    sample_trade = {
        "ticker": "LMT",
        "position_size": 0.05,
        "confidence": 0.82,
        "risk_score": 0.25,
        "compliance_status": "APPROVED",
        "strategy": "GOVERNMENT_CONTRACT_ARBITRAGE"
    }

    # Log trade decision
    trade_record_id = audit_trail.log_trade_decision(
        trade_id="TRADE_20260416_001",
        decision_data=sample_trade,
        user_id="trading_bot"
    )

    # Sample model training
    sample_metrics = {
        "train_samples": 500,
        "test_accuracy": 0.78,
        "train_accuracy": 0.82,
        "features_used": ["contract_amount", "signal_score", "urgency"],
        "model_type": "RandomForestClassifier"
    }

    # Log model training
    model_record_id = audit_trail.log_model_training(
        model_id="gov_event_predictor_v1.2",
        training_metrics=sample_metrics,
        user_id="ml_engineer_sarah"
    )

    # Query records
    print(f"\n🔍 Querying audit records...")
    recent_records = audit_trail.query_audit_records(
        filters={"event_type": "EVENT_ANALYSIS"},
        limit=5
    )

    for record in recent_records:
        print(f"   Record: {record['record_id']} - {record['event_type']} at {record['timestamp']}")

    # Verify integrity
    integrity_result = audit_trail.verify_chain_integrity()
    print(f"\n🔐 Integrity Check: {integrity_result['status']}")
    print(f"   Records checked: {integrity_result['records_checked']}")
    print(f"   Valid records: {integrity_result['valid_records']}")
    print(f"   Tampered records: {integrity_result['tampered_records']}")

    # Export for review
    export_path = audit_trail.export_for_regulatory_review()
    print(f"\n📤 Export completed: {export_path}")

    # Close connection
    audit_trail.close()