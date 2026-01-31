"""
FastAPI application factory for the JobPilot platform.

Uses an app-factory pattern so that configuration, middleware, and routers
are composed in a single ``create_app()`` call.  The module-level ``app``
variable is the ASGI entry-point used by ``uvicorn app.main:app``.
"""

from __future__ import annotations

import logging
from typing import Dict

from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from typing import List
from datetime import datetime

from app.config import settings
from app.api.v1.router import api_router
from app.middleware.rate_limit import RateLimitMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""

    application = FastAPI(
        title="JobPilot API",
        description="AI-powered career agent platform -- cold emails, LinkedIn posts, and more",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ---- CORS ----------------------------------------------------------
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Rate limiting ---------------------------------------------------
    application.add_middleware(RateLimitMiddleware)

    # ---- Versioned API router ------------------------------------------
    application.include_router(api_router)

    # ---- Global exception handlers -------------------------------------
    _register_exception_handlers(application)

    # ---- Legacy routes -------------------------------------------------
    # Keep all existing pre-v1 routes so nothing breaks during migration.
    _register_legacy_routes(application)

    return application


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

def _register_exception_handlers(application: FastAPI) -> None:
    """Attach global exception handlers for consistent error responses."""

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTPException",
                "message": exc.detail,
                "detail": {"status_code": exc.status_code},
            },
        )

    @application.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "detail": {"error": str(exc)} if settings.APP_ENV == "development" else {},
            },
        )


# ---------------------------------------------------------------------------
# Legacy (pre-v1) routes -- will be migrated to /api/v1/ incrementally
# ---------------------------------------------------------------------------

def _register_legacy_routes(application: FastAPI) -> None:
    """Register all original routes so the existing frontend keeps working."""

    # Lazy-import services to avoid circular imports and keep create_app() fast
    from app.models import (
        ColdEmailRequest, ColdEmailResponse,
        LinkedInPostRequest, LinkedInPostResponse,
        HealthCheckResponse, ErrorResponse,
        AuthorStyleUploadResponse, AuthorStyleSummary, AuthorStyleDetail,
    )
    from app.services.email_service import EmailService
    from app.services.post_service import LinkedInPostService
    from app.services.author_styles_service import AuthorStylesService
    from app.core.llm_clients import LLMClient
    from app.core.web_scraper import WebScraper

    email_service = EmailService()
    linkedin_service = LinkedInPostService()
    author_styles_service = AuthorStylesService()
    web_scraper = WebScraper()
    llm_client = LLMClient()

    # -- root redirect ---------------------------------------------------

    @application.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    # -- legacy health ---------------------------------------------------

    @application.get("/health", response_model=HealthCheckResponse, tags=["legacy"])
    async def legacy_health_check():
        services_status = {
            "llm": await llm_client.check_health(),
            "web_scraper": True,
            "email_service": True,
            "linkedin_service": True,
        }
        return HealthCheckResponse(
            status="healthy" if all(services_status.values()) else "degraded",
            version="1.0.0",
            services=services_status,
        )

    # -- email generation ------------------------------------------------

    @application.post("/api/generate-email", response_model=ColdEmailResponse, tags=["legacy"])
    async def generate_cold_email(request: ColdEmailRequest):
        try:
            logger.info("Generating cold email for %s at %s", request.recipient_name, request.company_website_url)

            import asyncio

            scraping_tasks = [web_scraper.scrape_website(str(request.company_website_url))]
            if request.sender_linkedin_url:
                scraping_tasks.append(web_scraper.scrape_website(request.sender_linkedin_url))
            if request.job_posting_url:
                scraping_tasks.append(web_scraper.scrape_website(request.job_posting_url))

            scraping_results = await asyncio.gather(*scraping_tasks, return_exceptions=True)

            company_data = scraping_results[0]
            if isinstance(company_data, Exception) or not company_data.success:
                error_msg = str(company_data) if isinstance(company_data, Exception) else company_data.error_message
                raise HTTPException(status_code=400, detail=f"Failed to scrape website: {error_msg}")

            sender_linkedin_text = None
            job_posting_content = None

            if request.sender_linkedin_url and len(scraping_results) > 1:
                linkedin_data = scraping_results[1]
                if not isinstance(linkedin_data, Exception) and linkedin_data.success:
                    sender_linkedin_text = linkedin_data.content

            if request.job_posting_url:
                job_index = 2 if request.sender_linkedin_url else 1
                if len(scraping_results) > job_index:
                    job_data = scraping_results[job_index]
                    if not isinstance(job_data, Exception) and job_data.success:
                        job_posting_content = job_data.content
                        await email_service.analyze_job_posting(job_posting_content)

            email_response = await email_service.generate_cold_email(
                request=request,
                company_text=company_data.content,
                sender_linkedin_text=sender_linkedin_text,
                job_posting_content=job_posting_content,
            )
            return email_response
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error generating cold email: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    # -- LinkedIn post generation ----------------------------------------

    @application.post("/api/generate-post", response_model=LinkedInPostResponse, tags=["legacy"])
    async def generate_linkedin_post(request: LinkedInPostRequest):
        try:
            return await linkedin_service.generate_post(request)
        except Exception as e:
            logger.error("Error generating LinkedIn post: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    # -- resume parsing --------------------------------------------------

    @application.post("/api/parse-resume", tags=["legacy"])
    async def parse_resume(file: UploadFile = File(...)):
        try:
            if not file.filename.endswith((".pdf", ".docx", ".doc")):
                raise HTTPException(status_code=400, detail="File must be PDF or DOCX format")
            content = await file.read()
            return await email_service.parse_resume(content, file.filename)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error parsing resume: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    # -- email tracking --------------------------------------------------

    @application.get("/api/track/email/{email_id}/pixel.gif", tags=["legacy"])
    async def track_email_open(email_id: str, background_tasks: BackgroundTasks):
        pixel = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
            b"\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00"
            b"\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02"
            b"\x44\x01\x00\x3b"
        )
        try:
            background_tasks.add_task(
                email_service.record_email_open,
                email_id=email_id,
                timestamp=datetime.utcnow(),
            )
        except Exception:
            pass
        return Response(content=pixel, media_type="image/gif")

    @application.get("/api/email/{email_id}/stats", tags=["legacy"])
    async def get_email_stats(email_id: str):
        try:
            return await email_service.get_email_stats(email_id)
        except Exception as e:
            logger.error("Error getting email stats: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    # -- URL scraping utility --------------------------------------------

    @application.post("/api/scrape-url", tags=["legacy"])
    async def scrape_url(url: str):
        try:
            return await web_scraper.scrape_website(url)
        except Exception as e:
            logger.error("Error scraping URL: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    # -- author styles ---------------------------------------------------

    @application.post("/api/upload-author-styles", response_model=AuthorStyleUploadResponse, tags=["legacy"])
    async def upload_author_styles(file: UploadFile = File(...)):
        try:
            if not file.filename.endswith((".xlsx", ".xls")):
                raise HTTPException(status_code=400, detail="File must be Excel format (.xlsx or .xls)")
            content = await file.read()
            result = await author_styles_service.process_excel_upload(content, file.filename)
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result.get("error", "Failed to process file"))
            return AuthorStyleUploadResponse(**result)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error uploading author styles: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @application.get("/api/author-styles", response_model=List[AuthorStyleSummary], tags=["legacy"])
    async def get_author_styles():
        try:
            return await author_styles_service.get_all_author_styles()
        except Exception as e:
            logger.error("Error getting author styles: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @application.get("/api/author-styles/{author_name}", response_model=AuthorStyleDetail, tags=["legacy"])
    async def get_author_details(author_name: str):
        try:
            author_data = await author_styles_service.get_author_posts(author_name)
            if not author_data:
                raise HTTPException(status_code=404, detail=f"Author '{author_name}' not found")
            return author_data
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error getting author details: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @application.delete("/api/author-styles/{author_id}", tags=["legacy"])
    async def delete_author_style(author_id: str):
        try:
            success = await author_styles_service.delete_author_style(author_id)
            if not success:
                raise HTTPException(status_code=404, detail="Author not found")
            return {"message": "Author style deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error deleting author style: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @application.get("/api/author-styles/search/{query}", tags=["legacy"])
    async def search_author_styles(query: str):
        try:
            return await author_styles_service.search_authors(query)
        except Exception as e:
            logger.error("Error searching author styles: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @application.get("/api/export-author-styles", tags=["legacy"])
    async def export_author_styles():
        try:
            excel_data = author_styles_service.export_author_database()
            return Response(
                content=excel_data,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=author_styles_export.xlsx"},
            )
        except Exception as e:
            logger.error("Error exporting author styles: %s", e)
            raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Module-level ASGI app  (uvicorn app.main:app)
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
