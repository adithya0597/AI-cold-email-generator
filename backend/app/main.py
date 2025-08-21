"""
FastAPI main application file
"""

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from typing import Optional, List
import os
from datetime import datetime
import logging

from .models import (
    ColdEmailRequest, ColdEmailResponse,
    LinkedInPostRequest, LinkedInPostResponse,
    EmailTrackingEvent,
    HealthCheckResponse, ErrorResponse,
    AuthorStyleUploadResponse, AuthorStyleSummary, AuthorStyleDetail
)
from .services.email_service import EmailService
from .services.post_service import LinkedInPostService
from .services.author_styles_service import AuthorStylesService
from .core.llm_clients import LLMClient
from .core.web_scraper import WebScraper
# from .monitoring.alerts import alert_manager  # Unused import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Content Generation Suite",
    description="Generate personalized cold emails and LinkedIn posts with AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
email_service = EmailService()
linkedin_service = LinkedInPostService()
author_styles_service = AuthorStylesService()
web_scraper = WebScraper()
llm_client = LLMClient()


@app.get("/", include_in_schema=False)
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check the health status of the API and its services"""
    services_status = {
        "llm": await llm_client.check_health(),
        "web_scraper": True,
        "email_service": True,
        "linkedin_service": True
    }
    
    return HealthCheckResponse(
        status="healthy" if all(services_status.values()) else "degraded",
        version="1.0.0",
        services=services_status
    )


@app.post("/api/generate-email", response_model=ColdEmailResponse)
async def generate_cold_email(request: ColdEmailRequest):
    """
    Generate a personalized cold email based on resume and company data
    """
    try:
        logger.info(f"Generating cold email for {request.recipient_name} at {request.company_website_url}")
        
        import asyncio
        
        # Prepare scraping tasks
        scraping_tasks = [
            web_scraper.scrape_website(str(request.company_website_url))
        ]
        
        # Add sender's LinkedIn scraping if URL provided
        if request.sender_linkedin_url:
            logger.info(f"Scraping sender's LinkedIn profile: {request.sender_linkedin_url}")
            scraping_tasks.append(web_scraper.scrape_website(request.sender_linkedin_url))
        
        # Add job posting scraping if URL provided
        if request.job_posting_url:
            logger.info(f"Scraping job posting: {request.job_posting_url}")
            scraping_tasks.append(web_scraper.scrape_website(request.job_posting_url))
        
        # Run all scraping tasks in parallel
        scraping_results = await asyncio.gather(*scraping_tasks, return_exceptions=True)
        
        # Process company data
        company_data = scraping_results[0]
        if isinstance(company_data, Exception) or not company_data.success:
            error_msg = str(company_data) if isinstance(company_data, Exception) else company_data.error_message
            raise HTTPException(status_code=400, detail=f"Failed to scrape website: {error_msg}")
        
        # Process sender's LinkedIn data if available
        sender_linkedin_text = None
        job_posting_content = None
        
        # Check for LinkedIn data (index 1 if exists)
        if request.sender_linkedin_url and len(scraping_results) > 1:
            linkedin_data = scraping_results[1]
            if not isinstance(linkedin_data, Exception) and linkedin_data.success:
                sender_linkedin_text = linkedin_data.content
                logger.info("Successfully scraped sender's LinkedIn profile")
            else:
                logger.warning(f"Failed to scrape sender's LinkedIn profile")
        
        # Check for job posting data (last index if exists)
        if request.job_posting_url:
            job_index = 2 if request.sender_linkedin_url else 1
            if len(scraping_results) > job_index:
                job_data = scraping_results[job_index]
                if not isinstance(job_data, Exception) and job_data.success:
                    job_posting_content = job_data.content
                    logger.info("Successfully scraped job posting")
                    # Analyze job posting for better targeting
                    job_analysis = await email_service.analyze_job_posting(job_posting_content)
                    logger.info(f"Job posting analysis: {job_analysis.get('role_title', 'Unknown')}")
                else:
                    logger.warning(f"Failed to scrape job posting")
        
        # Generate email with value propositions
        email_response = await email_service.generate_cold_email(
            request=request,
            company_text=company_data.content,
            sender_linkedin_text=sender_linkedin_text,
            job_posting_content=job_posting_content
        )
        
        return email_response
        
    except Exception as e:
        logger.error(f"Error generating cold email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-post", response_model=LinkedInPostResponse)
async def generate_linkedin_post(request: LinkedInPostRequest):
    """
    Generate a LinkedIn post in specified style
    """
    try:
        logger.info(f"Generating LinkedIn post on topic: {request.topic}")
        
        # Generate post based on request
        post_response = await linkedin_service.generate_post(request)
        
        return post_response
        
    except Exception as e:
        logger.error(f"Error generating LinkedIn post: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    """
    Parse resume from PDF or DOCX file
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.pdf', '.docx', '.doc')):
            raise HTTPException(status_code=400, detail="File must be PDF or DOCX format")
        
        # Read file content
        content = await file.read()
        
        # Parse resume
        result = await email_service.parse_resume(content, file.filename)
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing resume: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/track/email/{email_id}/pixel.gif")
async def track_email_open(email_id: str, background_tasks: BackgroundTasks):
    """
    Email tracking pixel endpoint
    """
    try:
        # Record the tracking event in background
        background_tasks.add_task(
            email_service.record_email_open,
            email_id=email_id,
            timestamp=datetime.utcnow()
        )
        
        # Return 1x1 transparent GIF
        pixel = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        return Response(content=pixel, media_type="image/gif")
        
    except Exception as e:
        logger.error(f"Error tracking email: {str(e)}")
        # Still return pixel even if tracking fails
        pixel = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        return Response(content=pixel, media_type="image/gif")


@app.get("/api/email/{email_id}/stats")
async def get_email_stats(email_id: str):
    """
    Get tracking statistics for a specific email
    """
    try:
        stats = await email_service.get_email_stats(email_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting email stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))






@app.post("/api/scrape-url")
async def scrape_url(url: str):
    """
    Scrape content from a given URL (utility endpoint)
    """
    try:
        result = await web_scraper.scrape_website(url)
        return result
    except Exception as e:
        logger.error(f"Error scraping URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Author Styles Endpoints
@app.post("/api/upload-author-styles", response_model=AuthorStyleUploadResponse)
async def upload_author_styles(file: UploadFile = File(...)):
    """
    Upload Excel file containing author posts for style emulation
    
    Expected columns:
    - author_name: Name of the author
    - post_content: Full text of the post
    - post_summary: Brief summary of post type/style
    - post_link: LinkedIn URL (optional)
    - post_date: Date of post (optional)
    - engagement_metrics: Engagement data (optional)
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="File must be Excel format (.xlsx or .xls)")
        
        # Read file content
        content = await file.read()
        
        # Process the Excel file
        result = await author_styles_service.process_excel_upload(content, file.filename)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to process file"))
        
        return AuthorStyleUploadResponse(**result)
        
    except Exception as e:
        logger.error(f"Error uploading author styles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/author-styles", response_model=List[AuthorStyleSummary])
async def get_author_styles():
    """
    Get all uploaded author styles
    """
    try:
        authors = await author_styles_service.get_all_author_styles()
        return authors
    except Exception as e:
        logger.error(f"Error getting author styles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/author-styles/{author_name}", response_model=AuthorStyleDetail)
async def get_author_details(author_name: str):
    """
    Get detailed information about a specific author including all posts
    """
    try:
        author_data = await author_styles_service.get_author_posts(author_name)
        if not author_data:
            raise HTTPException(status_code=404, detail=f"Author '{author_name}' not found")
        return author_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting author details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/author-styles/{author_id}")
async def delete_author_style(author_id: str):
    """
    Delete an author style from the database
    """
    try:
        success = await author_styles_service.delete_author_style(author_id)
        if not success:
            raise HTTPException(status_code=404, detail="Author not found")
        return {"message": "Author style deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting author style: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/author-styles/search/{query}")
async def search_author_styles(query: str):
    """
    Search for authors by name or style characteristics
    """
    try:
        results = await author_styles_service.search_authors(query)
        return results
    except Exception as e:
        logger.error(f"Error searching author styles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export-author-styles")
async def export_author_styles():
    """
    Export all author styles as Excel file
    """
    try:
        excel_data = author_styles_service.export_author_database()
        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=author_styles_export.xlsx"
            }
        )
    except Exception as e:
        logger.error(f"Error exporting author styles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return ErrorResponse(
        error="HTTPException",
        message=exc.detail,
        detail={"status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred",
        detail={"error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)