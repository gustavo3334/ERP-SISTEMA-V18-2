from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import require_permission
from app.models_extended import Employee, EmployeeDocumentRecord, StoredFile

router = APIRouter(prefix="/files", tags=["Arquivos e documentos"])


def allowed() -> set[str]:
    return {
        x.strip().lower()
        for x in settings.allowed_upload_extensions.split(",")
        if x.strip()
    }


@router.post(
    "/employee-document",
    dependencies=[Depends(require_permission("rh.documents.write"))],
)
async def upload(
    employee_id: str = Form(...),
    document_type: str = Form("Outro"),
    document_number: str = Form(""),
    expires_at: str = Form(""),
    notes: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not db.get(Employee, employee_id):
        raise HTTPException(404, "Colaborador não encontrado.")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed():
        raise HTTPException(422, "Tipo de arquivo não permitido.")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"Arquivo excede {settings.max_upload_mb} MB.")

    expiry = None
    if expires_at:
        try:
            expiry = date.fromisoformat(expires_at)
        except ValueError as exc:
            raise HTTPException(422, "Validade inválida.") from exc

    # A cópia oficial/persistente fica no PostgreSQL. Fora da Vercel, também
    # mantemos uma cópia local para facilitar a operação em Windows.
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target: Path | None = None
    if not settings.is_vercel:
        root = Path(settings.upload_dir).resolve()
        root.mkdir(parents=True, exist_ok=True)
        target = root / stored_name
        try:
            target.write_bytes(content)
        except OSError:
            target = None

    stored = StoredFile(
        employee_id=employee_id,
        category=document_type,
        original_name=file.filename or stored_name,
        stored_name=stored_name,
        content_type=file.content_type or "",
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
        storage_path=str(target) if target else "",
        content_blob=content,
        expires_at=expiry,
        notes=notes,
    )
    db.add(stored)
    db.flush()

    doc = EmployeeDocumentRecord(
        employee_id=employee_id,
        stored_file_id=stored.id,
        document_type=document_type,
        document_number=document_number,
        status="Recebido",
        expires_at=expiry,
        notes=notes,
    )
    db.add(doc)
    db.commit()
    return {
        "id": stored.id,
        "document_id": doc.id,
        "name": stored.original_name,
        "size": stored.size_bytes,
        "sha256": stored.sha256,
        "persistent": True,
    }


@router.get(
    "/employee/{employee_id}",
    dependencies=[Depends(require_permission("rh.documents.read"))],
)
def list_docs(employee_id: str, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(EmployeeDocumentRecord)
        .where(EmployeeDocumentRecord.employee_id == employee_id)
        .order_by(EmployeeDocumentRecord.created_at.desc())
    ).all()
    result = []
    for item in rows:
        stored = db.get(StoredFile, item.stored_file_id) if item.stored_file_id else None
        result.append(
            {
                "id": item.id,
                "document_type": item.document_type,
                "document_number": item.document_number,
                "status": item.status,
                "issue_date": item.issue_date,
                "expires_at": item.expires_at,
                "notes": item.notes,
                "file_id": stored.id if stored else None,
                "file_name": stored.original_name if stored else "",
                "size_bytes": stored.size_bytes if stored else 0,
                "persistent": bool(stored and stored.content_blob is not None),
            }
        )
    return result


@router.get(
    "/{file_id}/download",
    dependencies=[Depends(require_permission("rh.documents.read"))],
)
def download(file_id: str, db: Session = Depends(get_db)):
    stored = db.get(StoredFile, file_id)
    if not stored:
        raise HTTPException(404, "Arquivo não encontrado.")

    path = Path(stored.storage_path) if stored.storage_path else None
    if path and path.is_file():
        return FileResponse(
            path,
            filename=stored.original_name,
            media_type=stored.content_type or "application/octet-stream",
        )

    if stored.content_blob is not None:
        safe_name = quote(stored.original_name or stored.stored_name)
        return Response(
            content=stored.content_blob,
            media_type=stored.content_type or "application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
        )

    raise HTTPException(404, "Arquivo físico não encontrado e não há cópia persistente no banco.")


@router.delete(
    "/{file_id}",
    status_code=204,
    dependencies=[Depends(require_permission("rh.documents.write"))],
)
def remove(file_id: str, db: Session = Depends(get_db)):
    stored = db.get(StoredFile, file_id)
    if not stored:
        raise HTTPException(404, "Arquivo não encontrado.")
    path = Path(stored.storage_path) if stored.storage_path else None
    for item in db.scalars(
        select(EmployeeDocumentRecord).where(EmployeeDocumentRecord.stored_file_id == file_id)
    ).all():
        db.delete(item)
    db.delete(stored)
    db.commit()
    if path:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    return None
