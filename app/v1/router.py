from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.v1.schemas import AnalysisResponse
from app.v1.service import DocumentAnalysisService, get_document_analysis_service

router = APIRouter(prefix="/v1", tags=["v1"])


@router.post("/analyse-document", response_model=AnalysisResponse)
async def analyse_document(
    file: Annotated[UploadFile, File(...)],
    query: Annotated[str, Form(...)],
    service: Annotated[DocumentAnalysisService, Depends(get_document_analysis_service)],
) -> AnalysisResponse:
    file_bytes = await file.read()

    try:
        return await service.analyse_document(
            file_bytes=file_bytes,
            filename=file.filename or "uploaded_document.txt",
            content_type=file.content_type,
            query=query,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
