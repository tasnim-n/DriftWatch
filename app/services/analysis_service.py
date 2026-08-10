import os
import uuid
import zipfile
import shutil
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.core.security import SecureExtractor
from app.core.config import settings
from analyzers.drift_engine import DriftEngine
from risk_engine.scoring import RiskScorer
from risk_engine.explanations import ExplanationGenerator
from app.models.analysis import AnalysisRecord

class AnalysisService:

    @classmethod
    def run_differential_analysis(cls, db: Session, v1_zip_path: str, v2_zip_path: str, label: str = None) -> AnalysisRecord:
        analysis_id = str(uuid.uuid4())
        
        v1_extract_dir = os.path.join(settings.EXTRACTED_DIR, f"{analysis_id}_v1")
        v2_extract_dir = os.path.join(settings.EXTRACTED_DIR, f"{analysis_id}_v2")

        try:
            # Step 1: Secure extraction & unpacking
            v1_info = SecureExtractor.validate_and_extract_zip(v1_zip_path, v1_extract_dir)
            v2_info = SecureExtractor.validate_and_extract_zip(v2_zip_path, v2_extract_dir)

            # Step 2: Calculate behavioral drift vector D_t
            drift_data = DriftEngine.compute_behavioral_drift(v1_extract_dir, v2_extract_dir)

            # Step 3: Compute risk score & classification
            risk_summary = RiskScorer.calculate_risk_score(drift_data)

            # Step 4: Generate findings & explanations
            findings = ExplanationGenerator.generate_findings(drift_data, risk_summary)
            recommendation = ExplanationGenerator.generate_overall_recommendation(
                risk_summary["risk_classification"],
                findings
            )

            # Step 5: Save record in DB
            record = AnalysisRecord(
                id=analysis_id,
                extension_name=drift_data["extension_name"],
                v1_version=drift_data["v1_version"],
                v2_version=drift_data["v2_version"],
                v1_hash=v1_info["archive_hash"],
                v2_hash=v2_info["archive_hash"],
                risk_score=risk_summary["risk_score"],
                risk_classification=risk_summary["risk_classification"],
                confidence_score=risk_summary["confidence_score"],
                permission_drift_count=len(drift_data["perm_diff"]["added_permissions"]),
                host_scope_expanded=1 if drift_data["host_diff"]["is_expanded"] else 0,
                recommendation=recommendation
            )

            record.set_findings({
                "findings": findings,
                "triggered_rules": risk_summary["triggered_rules"],
                "score_breakdown": risk_summary["score_breakdown"],
                "confidence_breakdown": risk_summary["confidence_breakdown"],
                "raw_score_before_cap": risk_summary["raw_score_before_cap"],
                "analyzer_errors": drift_data.get("analyzer_errors", {}),
            })
            feature_vector = dict(drift_data["drift_vector"])
            feature_vector["analyzer_errors"] = drift_data.get("analyzer_errors", {})
            record.set_feature_vector(feature_vector)

            db.add(record)
            db.commit()
            db.refresh(record)

            return record

        finally:
            # Step 6: Cleanup temporary extraction workspaces
            SecureExtractor.cleanup_directory(v1_extract_dir)
            SecureExtractor.cleanup_directory(v2_extract_dir)
