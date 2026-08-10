import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.analysis import AnalysisRecord
from app.services.analysis_service import AnalysisService
from app.core.security import SecurityException
from app.schemas.analysis import AnalysisResponseSchema

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    recent = db.query(AnalysisRecord).order_by(AnalysisRecord.created_at.desc()).limit(10).all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"recent_analyses": recent, "error": None}
    )

@router.post("/analyze", response_class=HTMLResponse)
async def analyze_versions(
    request: Request,
    v1_file: UploadFile = File(...),
    v2_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    temp_dir = tempfile.mkdtemp()
    v1_path = os.path.join(temp_dir, "v1.zip")
    v2_path = os.path.join(temp_dir, "v2.zip")

    try:
        with open(v1_path, "wb") as f:
            shutil.copyfileobj(v1_file.file, f)

        with open(v2_path, "wb") as f:
            shutil.copyfileobj(v2_file.file, f)

        record = AnalysisService.run_differential_analysis(db, v1_path, v2_path)
        return RedirectResponse(url=f"/report/{record.id}", status_code=303)

    except SecurityException as se:
        recent = db.query(AnalysisRecord).order_by(AnalysisRecord.created_at.desc()).limit(10).all()
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"recent_analyses": recent, "error": f"Security Validation Error: {str(se)}"},
            status_code=400
        )
    except Exception as e:
        recent = db.query(AnalysisRecord).order_by(AnalysisRecord.created_at.desc()).limit(10).all()
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"recent_analyses": recent, "error": f"Analysis Execution Error: {str(e)}"},
            status_code=500
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.get("/report/{analysis_id}", response_class=HTMLResponse)
def get_report(analysis_id: str, request: Request, db: Session = Depends(get_db)):
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis record not found")

    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={
            "record": record,
            "findings_data": record.get_findings(),
            "feature_vector": record.get_feature_vector()
        }
    )

@router.get("/api/v1/analysis/{analysis_id}", response_model=AnalysisResponseSchema)
def get_analysis_json(analysis_id: str, db: Session = Depends(get_db)):
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis record not found")
    
    findings_data = record.get_findings()
    return AnalysisResponseSchema(
        id=record.id,
        extension_id=record.extension_id,
        extension_name=record.extension_name,
        v1_version=record.v1_version,
        v2_version=record.v2_version,
        v1_hash=record.v1_hash,
        v2_hash=record.v2_hash,
        risk_score=record.risk_score,
        risk_classification=record.risk_classification,
        confidence_score=record.confidence_score,
        permission_drift_count=record.permission_drift_count,
        host_scope_expanded=record.host_scope_expanded,
        findings=findings_data.get("findings", []),
        feature_vector=record.get_feature_vector(),
        score_breakdown=findings_data.get("score_breakdown", {}),
        confidence_breakdown=findings_data.get("confidence_breakdown", {}),
        recommendation=record.recommendation,
        created_at=record.created_at
    )
