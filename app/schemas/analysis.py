from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime

class AnalysisRequest(BaseModel):
    label: Optional[str] = None

class FindingSchema(BaseModel):
    title: str
    category: str # permissions, host_access, background, dynamic_code, etc.
    severity: str # Low, Moderate, High, Critical
    impact: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    evidence: str
    recommendation: str
    confidence: float = 1.0

class AnalysisResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    extension_id: Optional[str] = None
    extension_name: Optional[str] = None
    v1_version: str
    v2_version: str
    v1_hash: str
    v2_hash: str
    risk_score: float
    risk_classification: str
    confidence_score: float
    permission_drift_count: int
    host_scope_expanded: int
    findings: List[FindingSchema]
    feature_vector: Dict[str, Any]
    score_breakdown: Dict[str, Any] = {}
    confidence_breakdown: Dict[str, Any] = {}
    recommendation: str
    created_at: datetime
