"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class PostGoal(str, Enum):
    """LinkedIn post goals"""
    DRIVE_ENGAGEMENT = "Drive Engagement"
    GENERATE_LEADS = "Generate Leads"
    BUILD_THOUGHT_LEADERSHIP = "Build Thought Leadership"


class EmailTone(str, Enum):
    """Email tone options"""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    FORMAL = "formal"
    ENTHUSIASTIC = "enthusiastic"


class ColdEmailRequest(BaseModel):
    """Request model for cold email generation"""
    user_resume_text: str = Field(..., description="Full text of user's resume")
    recipient_name: str = Field(..., description="Name of the email recipient")
    recipient_role: str = Field(..., description="Job title/role of the recipient")
    company_website_url: HttpUrl = Field(..., description="URL of the company website")
    company_tone: EmailTone = Field(..., description="Desired tone for the email")
    email_goal: str = Field(..., description="Primary goal of the email")
    pain_point: Optional[str] = Field(None, description="Specific pain point to address")
    sender_name: str = Field(..., description="Name of the sender")
    sender_email: EmailStr = Field(..., description="Email address of the sender")
    sender_linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL of the sender (optional)")
    job_posting_url: Optional[str] = Field(None, description="URL of the job posting to tailor the email to (optional)")


class ColdEmailResponse(BaseModel):
    """Response model for cold email generation"""
    email_id: str = Field(..., description="Unique identifier for the email")
    subject: str = Field(..., description="Generated email subject line")
    body: str = Field(..., description="Generated email body with tracking pixel")
    value_propositions: List[str] = Field(..., description="List of value propositions")
    tone_analysis: str = Field(..., description="Analysis of the company's tone")
    tracking_pixel_url: str = Field(..., description="URL for the tracking pixel")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LinkedInPostRequest(BaseModel):
    """Request model for LinkedIn post generation"""
    topic: str = Field(..., description="Topic of the LinkedIn post")
    industry: str = Field(..., description="Target industry")
    target_audience: str = Field(..., description="Description of target audience")
    post_goal: PostGoal = Field(..., description="Goal of the post")
    influencer_style: str = Field(..., description="Pre-selected or custom style")
    custom_author_name: Optional[str] = Field(None, description="Name for custom style emulation")
    generate_image: bool = Field(default=False, description="Whether to generate an image for the post")
    reference_urls: List[str] = Field(default_factory=list, description="Optional URLs to articles for reference or inspiration (max 3)")


class LinkedInPostResponse(BaseModel):
    """Response model for LinkedIn post generation"""
    post_id: str = Field(..., description="Unique identifier for the post")
    content: str = Field(..., description="Generated post content")
    hook: str = Field(..., description="Attention-grabbing opening")
    body: str = Field(..., description="Main content of the post")
    call_to_action: str = Field(..., description="Call to action")
    hashtags: List[str] = Field(..., description="Recommended hashtags")
    estimated_reading_time: int = Field(..., description="Estimated reading time in seconds")
    style_analysis: Optional[str] = Field(None, description="Analysis of the emulated style")
    image_url: Optional[str] = Field(None, description="Generated image URL")
    image_type: Optional[str] = Field(None, description="Type of generated image")
    image_prompt: Optional[str] = Field(None, description="Prompt used for image generation")
    image_relevance_score: Optional[float] = Field(None, description="Relevance score of image to post")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmailTrackingEvent(BaseModel):
    """Model for email tracking events"""
    email_id: str = Field(..., description="ID of the tracked email")
    event_type: str = Field(..., description="Type of tracking event (open, click)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(None, description="IP address of the event")
    user_agent: Optional[str] = Field(None, description="User agent string")




class WebScrapingResult(BaseModel):
    """Model for web scraping results"""
    url: str = Field(..., description="Scraped URL")
    success: bool = Field(..., description="Whether scraping was successful")
    content: Optional[str] = Field(None, description="Extracted text content")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ResumeParsingResult(BaseModel):
    """Model for resume parsing results"""
    success: bool = Field(..., description="Whether parsing was successful")
    text_content: Optional[str] = Field(None, description="Extracted text from resume")
    skills: List[str] = Field(default_factory=list, description="Identified skills")
    experience_years: Optional[int] = Field(None, description="Years of experience")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class HealthCheckResponse(BaseModel):
    """Model for API health check response"""
    status: str = Field("healthy", description="API health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, bool] = Field(default_factory=dict, description="Status of sub-services")


class ErrorResponse(BaseModel):
    """Model for error responses"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuthorStyleUploadResponse(BaseModel):
    """Response model for author style Excel upload"""
    success: bool = Field(..., description="Whether upload was successful")
    processed_count: int = Field(0, description="Number of posts processed")
    skipped_count: int = Field(0, description="Number of rows skipped")
    authors_added: List[str] = Field(default_factory=list, description="List of authors added")
    total_authors: int = Field(0, description="Total authors in database")
    message: str = Field(..., description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")


class AuthorStyleSummary(BaseModel):
    """Model for author style summary"""
    author_id: str = Field(..., description="Unique author identifier")
    author_name: str = Field(..., description="Author name")
    post_count: int = Field(..., description="Number of posts")
    style_summary: str = Field(..., description="Summary of writing style")
    created_at: str = Field(..., description="When author was added")
    sample_post: Optional[str] = Field(None, description="Sample post excerpt")


class AuthorPost(BaseModel):
    """Model for individual author post"""
    post_id: str = Field(..., description="Unique post identifier")
    content: str = Field(..., description="Full post content")
    summary: str = Field(..., description="Post summary/type")
    link: Optional[str] = Field(None, description="LinkedIn post URL")
    date: Optional[str] = Field(None, description="Post date")
    engagement: Optional[Dict[str, int]] = Field(None, description="Engagement metrics")
    word_count: int = Field(..., description="Word count")
    character_count: int = Field(..., description="Character count")


class AuthorStyleDetail(BaseModel):
    """Model for detailed author style with all posts"""
    author_id: str = Field(..., description="Unique author identifier")
    author_name: str = Field(..., description="Author name")
    posts: List[AuthorPost] = Field(..., description="All posts by author")
    created_at: str = Field(..., description="When author was added")
    post_count: int = Field(..., description="Total number of posts")
    style_summary: str = Field(..., description="Summary of writing style")