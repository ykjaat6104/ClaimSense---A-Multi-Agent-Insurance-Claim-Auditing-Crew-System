import re
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_username, get_db
from app.config import get_settings
from app.db import crud
from app.db.models import claim_summary_dict, claim_to_public_dict
from app.schemas.api import AdjusterActionRequest, ClaimUploadResponse, ProcessResponse
from app.services.jobs import run_claim_pipeline_job
from app.services.report_docx import build_docx_report

router = APIRouter()

_MAX_BYTES = 25 * 1024 * 1024


def _sanitize_filename(name: str) -> str:
    base = Path(name).name
    return re.sub(r"[^\w.\-]", "_", base)[:180] or "upload.bin"


async def _read_limited(upload: UploadFile) -> bytes:
    data = await upload.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail=f"File {upload.filename!r} exceeds 25 MB limit")
    return data


def _derive_ui_step(logs: list[str], status: str) -> str:
    if status == "completed":
        return "done"
    if status == "failed":
        return "error"
    if not logs:
        return "queued"
    last = logs[-1]
    if "FAILED" in last:
        return "error"
    if "Extracting document" in last:
        return "extract"
    if "Structuring" in last:
        return "structure"
    if "Matching policy" in last or "Retrieved" in last:
        return "policy"
    if "Running risk" in last:
        return "risk"
    if "Generating report" in last or "Analysis complete" in last:
        return "report"
    return "working"


def _enqueue_analysis(db: Session, claim_id: uuid.UUID) -> ProcessResponse:
    claim = crud.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status == "processing":
        return ProcessResponse(
            claim_id=str(claim.id), status=claim.status, message="Analysis already in progress."
        )
    if claim.status == "completed":
        return ProcessResponse(
            claim_id=str(claim.id), status=claim.status, message="This claim has already been analyzed."
        )
    claim.error_message = None
    claim.status = "processing"
    db.add(claim)
    db.commit()
    return ProcessResponse(
        claim_id=str(claim_id), status="processing", message="Analysis started."
    )


@router.post("/upload-claim", response_model=ClaimUploadResponse)
async def upload_claim(
    claim: UploadFile = File(..., description="Claim form (PDF/image/text)"),
    invoice: UploadFile = File(..., description="Invoice or repair estimate"),
    policy: UploadFile = File(..., description="Policy document"),
    past_claims: UploadFile | None = File(None, description="Optional past claims CSV"),
    evidence_1: UploadFile | None = File(None, description="Optional evidence document"),
    evidence_2: UploadFile | None = File(None),
    evidence_3: UploadFile | None = File(None),
    evidence_4: UploadFile | None = File(None),
    evidence_5: UploadFile | None = File(None),
    other_1: UploadFile | None = File(None, description="Optional extra document"),
    other_2: UploadFile | None = File(None),
    other_3: UploadFile | None = File(None),
    other_4: UploadFile | None = File(None),
    other_5: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> ClaimUploadResponse:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".csv", ".webp", ".tif", ".tiff"}
    for f, label in ((claim, "claim"), (invoice, "invoice"), (policy, "policy")):
        suf = Path(f.filename or "").suffix.lower()
        if suf and suf not in allowed:
            raise HTTPException(status_code=400, detail=f"{label}: unsupported type {suf}")

    cid = uuid.uuid4()
    base = settings.upload_dir / str(cid)
    pcsv: str | None = None
    ev_paths: list[str] = []
    other_paths: list[str] = []
    try:
        c_bytes = await _read_limited(claim)
        i_bytes = await _read_limited(invoice)
        p_bytes = await _read_limited(policy)
        cp = crud.save_upload(base / f"claim_{_sanitize_filename(claim.filename or 'claim')}", c_bytes)
        ip = crud.save_upload(base / f"invoice_{_sanitize_filename(invoice.filename or 'invoice')}", i_bytes)
        pp = crud.save_upload(base / f"policy_{_sanitize_filename(policy.filename or 'policy')}", p_bytes)
        if past_claims and past_claims.filename:
            suf = Path(past_claims.filename).suffix.lower()
            if suf not in {".csv", ".txt"}:
                raise HTTPException(status_code=400, detail="Past claims file must be .csv or .txt")
            raw = await _read_limited(past_claims)
            pcsv = crud.save_upload(
                base / f"past_claims_{_sanitize_filename(past_claims.filename)}", raw
            )
        for idx, ev in enumerate(
            (evidence_1, evidence_2, evidence_3, evidence_4, evidence_5), start=1
        ):
            if ev and ev.filename:
                suf = Path(ev.filename).suffix.lower()
                if suf and suf not in allowed:
                    raise HTTPException(
                        status_code=400, detail=f"evidence_{idx}: unsupported type {suf}"
                    )
                raw_ev = await _read_limited(ev)
                ev_paths.append(
                    crud.save_upload(
                        base / f"evidence_{idx}_{_sanitize_filename(ev.filename)}", raw_ev
                    )
                )
        for idx, ot in enumerate(
            (other_1, other_2, other_3, other_4, other_5), start=1
        ):
            if ot and ot.filename:
                suf = Path(ot.filename).suffix.lower()
                if suf and suf not in allowed:
                    raise HTTPException(
                        status_code=400, detail=f"other_{idx}: unsupported type {suf}"
                    )
                raw_ot = await _read_limited(ot)
                other_paths.append(
                    crud.save_upload(
                        base / f"other_{idx}_{_sanitize_filename(ot.filename)}", raw_ot
                    )
                )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to store uploads: {e}") from e

    c = crud.create_claim(
        db,
        claim_id=cid,
        claim_path=cp,
        invoice_path=ip,
        policy_path=pp,
        past_claims_csv_path=pcsv,
        evidence_file_paths=ev_paths if ev_paths else None,
        other_file_paths=other_paths if other_paths else None,
    )
    return ClaimUploadResponse(claim_id=str(c.id), status=c.status)


@router.post("/claims/{claim_id}/process", response_model=ProcessResponse)
def process_claim_async(
    claim_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> ProcessResponse:
    r = _enqueue_analysis(db, claim_id)
    if r.status == "processing" and r.message == "Analysis started.":
        background_tasks.add_task(run_claim_pipeline_job, str(claim_id))
    return r


@router.post("/process-claim/{claim_id}", response_model=ProcessResponse)
def process_claim_legacy(
    claim_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> ProcessResponse:
    return process_claim_async(claim_id, background_tasks, db, _username)


@router.get("/claims/{claim_id}/status")
def claim_status(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> dict:
    c = crud.get_claim(db, claim_id)
    if not c:
        raise HTTPException(status_code=404, detail="Claim not found")
    logs = list(c.processing_logs or [])
    return {
        "id": str(c.id),
        "status": c.status,
        "processing_logs": logs,
        "ui_step": _derive_ui_step(logs, c.status),
        "error_message": c.error_message,
    }


@router.get("/claims")
def list_claims(
    search: str | None = None,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> list[dict]:
    rows = crud.list_claims(db, limit=100, search=search)
    return [claim_summary_dict(c) for c in rows]


@router.get("/claims/compare")
def compare_claims(
    ids: str,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> list[dict]:
    parts = [p.strip() for p in ids.split(",") if p.strip()][:6]
    out: list[dict] = []
    for s in parts:
        try:
            uid = uuid.UUID(s)
        except ValueError:
            continue
        c = crud.get_claim(db, uid)
        if c:
            out.append(claim_summary_dict(c))
    return out


@router.get("/claims/{claim_id}")
def get_claim_detail(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> JSONResponse:
    c = crud.get_claim(db, claim_id)
    if not c:
        raise HTTPException(status_code=404, detail="Claim not found")
    return JSONResponse(claim_to_public_dict(c))


@router.get("/get-report/{claim_id}")
def legacy_get_report(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> JSONResponse:
    return get_claim_detail(claim_id, db, _username)


@router.get("/claims/{claim_id}/docx")
def get_claim_docx(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> FileResponse:
    c = crud.get_claim(db, claim_id)
    if not c:
        raise HTTPException(status_code=404, detail="Claim not found")
    if c.status != "completed":
        raise HTTPException(status_code=400, detail="Claim analysis must be completed first.")
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    dest = reports_dir / f"{claim_id}_report.docx"
    if not dest.is_file():
        build_docx_report(c, dest)
    return FileResponse(str(dest), filename=f"claimsense_report_{claim_id}.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.get("/claims/{claim_id}/pdf")
def get_claim_pdf(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> FileResponse:
    c = crud.get_claim(db, claim_id)
    if not c:
        raise HTTPException(status_code=404, detail="Claim not found")
    if not c.report_pdf_path or not Path(c.report_pdf_path).is_file():
        raise HTTPException(
            status_code=404,
            detail="PDF not ready yet. Wait until status is completed or check error_message.",
        )
    path = Path(c.report_pdf_path)
    return FileResponse(path, filename=f"claimsense_report_{claim_id}.pdf", media_type="application/pdf")


@router.get("/get-report/{claim_id}/pdf")
def legacy_get_pdf(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> FileResponse:
    return get_claim_pdf(claim_id, db, _username)


@router.post("/claims/{claim_id}/adjuster-action")
def adjuster_action(
    claim_id: uuid.UUID,
    body: AdjusterActionRequest,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> dict:
    c = crud.get_claim(db, claim_id)
    if not c:
        raise HTTPException(status_code=404, detail="Claim not found")
    mapping = {
        "approve": "ADJUSTER_APPROVE",
        "reject": "ADJUSTER_REJECT",
        "manual_review": "ADJUSTER_MANUAL_REVIEW",
    }
    crud.set_adjuster_action(db, c, mapping[body.action])
    db.refresh(c)
    return {"ok": True, "claim_id": str(c.id), "adjuster_action": c.adjuster_action}
