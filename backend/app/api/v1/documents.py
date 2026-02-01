"""
Documents API endpoints for master resume management.

Handles upload, download, list, and soft-delete of user documents
(master resumes and tailored versions). The master resume is the
single active resume with job_id=NULL.

All endpoints require Clerk JWT authentication.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.auth.clerk import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/master-resume")
async def upload_master_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    """
    Upload a master resume (PDF/DOCX).

    Stores the file in Supabase Storage, creates a Document record
    with type=RESUME and job_id=NULL, parses structured data via
    the resume_parser service, and updates the user's Profile.

    If a previous master resume exists, it is soft-deleted (archived).
    """
    # Validate file type
    filename = file.filename or "unknown"
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Please upload a PDF or DOCX file.",
        )

    # Read and validate file size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # 1. Upload to Supabase Storage
        try:
            from app.services.storage_service import upload_file

            storage_path = await upload_file(
                user_id=user_id,
                file_bytes=file_bytes,
                filename=filename,
                content_type=file.content_type,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )
        except Exception:
            logger.error("Failed to upload to storage for user %s", user_id, exc_info=True)
            storage_path = f"{user_id}/{filename}"

        # 2. Soft-delete previous master resume(s)
        now = datetime.now(timezone.utc)
        await session.execute(
            text("""
                UPDATE documents
                SET deleted_at = :now, deletion_reason = 'archived_by_new_upload'
                WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid)
                  AND type = 'resume'
                  AND job_id IS NULL
                  AND deleted_at IS NULL
            """),
            {"now": now, "uid": user_id},
        )

        # 3. Parse resume via resume_parser
        parsed_profile = None
        try:
            from app.services.resume_parser import extract_profile_from_resume

            parsed_profile = await extract_profile_from_resume(file_bytes, filename)
        except Exception:
            logger.warning("Resume parsing failed for user %s", user_id, exc_info=True)

        # 4. Create new Document row
        doc_id = str(uuid.uuid4())
        content_data = {}
        if parsed_profile:
            content_data = parsed_profile.model_dump()

        await session.execute(
            text("""
                INSERT INTO documents (id, user_id, type, version, content, job_id, schema_version, created_at, updated_at)
                VALUES (
                    :doc_id,
                    (SELECT id FROM users WHERE clerk_id = :uid),
                    'resume',
                    1,
                    :content,
                    NULL,
                    1,
                    :now,
                    :now
                )
            """),
            {
                "doc_id": doc_id,
                "uid": user_id,
                "content": json.dumps(content_data),
                "now": now,
            },
        )

        # 5. Update Profile.resume_storage_path
        await session.execute(
            text("""
                UPDATE profiles
                SET resume_storage_path = :path
                WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid)
            """),
            {"path": storage_path, "uid": user_id},
        )

        # 6. Update Profile structured data if parsing succeeded
        if parsed_profile:
            await session.execute(
                text("""
                    UPDATE profiles
                    SET skills = :skills,
                        experience = :experience,
                        education = :education,
                        headline = :headline,
                        extraction_source = 'resume'
                    WHERE user_id = (SELECT id FROM users WHERE clerk_id = :uid)
                """),
                {
                    "skills": parsed_profile.skills,
                    "experience": json.dumps([e.model_dump() for e in parsed_profile.experience]),
                    "education": json.dumps([e.model_dump() for e in parsed_profile.education]),
                    "headline": parsed_profile.headline,
                    "uid": user_id,
                },
            )

        await session.commit()

    return {
        "document_id": doc_id,
        "storage_path": storage_path,
        "parsed": parsed_profile.model_dump() if parsed_profile else None,
    }


@router.get("/master-resume")
async def get_master_resume(
    user_id: str = Depends(get_current_user_id),
):
    """
    Return the active master resume metadata with a signed download URL.
    """
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT d.id, d.version, d.content, d.created_at, p.resume_storage_path
                FROM documents d
                JOIN users u ON d.user_id = u.id
                LEFT JOIN profiles p ON p.user_id = u.id
                WHERE u.clerk_id = :uid
                  AND d.type = 'resume'
                  AND d.job_id IS NULL
                  AND d.deleted_at IS NULL
                ORDER BY d.created_at DESC
                LIMIT 1
            """),
            {"uid": user_id},
        )
        row = result.mappings().first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No master resume found.",
        )

    # Generate signed URL
    signed_url = None
    if row["resume_storage_path"]:
        try:
            from app.services.storage_service import get_signed_url

            signed_url = await get_signed_url(row["resume_storage_path"])
        except Exception:
            logger.warning("Failed to generate signed URL for user %s", user_id, exc_info=True)

    return {
        "document_id": str(row["id"]),
        "version": row["version"],
        "content": row["content"],
        "created_at": str(row["created_at"]),
        "download_url": signed_url,
    }


@router.get("/")
async def list_documents(
    user_id: str = Depends(get_current_user_id),
    doc_type: Optional[str] = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    List all user documents (paginated, with optional type filter).
    """
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    offset = (page - 1) * page_size

    type_filter = ""
    params: dict = {"uid": user_id, "limit": page_size, "offset": offset}

    if doc_type:
        type_filter = "AND d.type = :dtype"
        params["dtype"] = doc_type

    async with AsyncSessionLocal() as session:
        # Get total count
        count_result = await session.execute(
            text(f"""
                SELECT COUNT(*) FROM documents d
                JOIN users u ON d.user_id = u.id
                WHERE u.clerk_id = :uid
                  AND d.deleted_at IS NULL
                  {type_filter}
            """),
            params,
        )
        total = count_result.scalar()

        # Get page
        result = await session.execute(
            text(f"""
                SELECT d.id, d.type, d.version, d.job_id, d.created_at
                FROM documents d
                JOIN users u ON d.user_id = u.id
                WHERE u.clerk_id = :uid
                  AND d.deleted_at IS NULL
                  {type_filter}
                ORDER BY d.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.mappings().all()

    return {
        "documents": [
            {
                "id": str(r["id"]),
                "type": r["type"],
                "version": r["version"],
                "job_id": str(r["job_id"]) if r["job_id"] else None,
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Soft-delete a document owned by the authenticated user.
    """
    from sqlalchemy import text

    from app.db.engine import AsyncSessionLocal

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                UPDATE documents
                SET deleted_at = :now, deletion_reason = 'user_deleted'
                WHERE id = :doc_id::uuid
                  AND user_id = (SELECT id FROM users WHERE clerk_id = :uid)
                  AND deleted_at IS NULL
                RETURNING id
            """),
            {"now": now, "doc_id": document_id, "uid": user_id},
        )
        updated = result.scalar_one_or_none()
        await session.commit()

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or already deleted.",
        )

    return {"message": "Document deleted", "document_id": document_id}
