"""Background pipeline runner (own DB session per job)."""

from __future__ import annotations

import uuid

from app.db import crud
from app.db.session import new_db_session
from app.services.claim_pipeline import process_claim


def run_claim_pipeline_job(claim_id: str) -> None:
    db = new_db_session()
    try:
        uid = uuid.UUID(claim_id)
        claim = crud.get_claim(db, uid)
        if claim is None:
            return
        process_claim(db, uid)
    except Exception as e:  # noqa: BLE001
        try:
            uid = uuid.UUID(claim_id)
            claim = crud.get_claim(db, uid)
            if claim:
                claim.status = "failed"
                claim.error_message = str(e)
                db.add(claim)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
