import datetime
import json
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from app.database.session import Base

class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(String(36), primary_key=True, index=True)
    extension_id = Column(String(100), index=True, nullable=True)
    extension_name = Column(String(255), nullable=True)
    
    v1_version = Column(String(50), nullable=False)
    v2_version = Column(String(50), nullable=False)
    
    v1_hash = Column(String(64), nullable=False)
    v2_hash = Column(String(64), nullable=False)
    
    risk_score = Column(Float, nullable=False)
    risk_classification = Column(String(20), nullable=False) # Low, Moderate, High, Critical
    confidence_score = Column(Float, nullable=False, default=1.0)
    
    permission_drift_count = Column(Integer, default=0)
    host_scope_expanded = Column(Integer, default=0) # 1 if expanded, 0 otherwise
    
    findings_json = Column(Text, nullable=False) # Serialized findings JSON
    feature_vector_json = Column(Text, nullable=False) # Serialized feature vector
    recommendation = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    def set_findings(self, data: dict):
        self.findings_json = json.dumps(data)

    def get_findings(self) -> dict:
        return json.loads(self.findings_json) if self.findings_json else {}

    def set_feature_vector(self, data: dict):
        self.feature_vector_json = json.dumps(data)

    def get_feature_vector(self) -> dict:
        return json.loads(self.feature_vector_json) if self.feature_vector_json else {}
