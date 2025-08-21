"""
Test suite for email service
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

from app.services.email_service import EmailService
from app.models import ColdEmailRequest, EmailTone


@pytest.fixture
def email_service():
    """Create email service instance"""
    return EmailService()


@pytest.fixture
def sample_email_request():
    """Create sample email request"""
    return ColdEmailRequest(
        user_resume_text="Software engineer with 5 years experience in Python and React",
        recipient_name="John Smith",
        recipient_role="CTO",
        company_website_url="https://example.com",
        company_tone=EmailTone.PROFESSIONAL,
        email_goal="Schedule a meeting",
        pain_point="Scaling engineering team",
        sender_name="Jane Doe",
        sender_email="jane@example.com"
    )


@pytest.mark.asyncio
async def test_generate_cold_email(email_service, sample_email_request):
    """Test cold email generation"""
    company_text = "Example Corp is a leading technology company focused on AI solutions."
    
    with patch.object(email_service.llm_client, 'generate', new_callable=AsyncMock) as mock_generate:
        with patch.object(email_service.llm_client, 'generate_json', new_callable=AsyncMock) as mock_generate_json:
            # Mock LLM responses
            mock_generate.side_effect = [
                "Professional tone with focus on innovation",  # tone analysis
                "Innovative Partnership Opportunity",  # subject
                "Dear John,\n\nI noticed Example Corp's impressive work..."  # body
            ]
            mock_generate_json.return_value = {
                "propositions": [
                    "Reduce development time by 40%",
                    "Scale your team efficiently",
                    "Implement best practices"
                ]
            }
            
            result = await email_service.generate_cold_email(sample_email_request, company_text)
            
            assert result.email_id is not None
            assert result.subject == "Innovative Partnership Opportunity"
            assert "Dear John" in result.body
            assert len(result.value_propositions) == 3
            assert result.tracking_pixel_url is not None


@pytest.mark.asyncio
async def test_analyze_company_tone(email_service):
    """Test company tone analysis"""
    company_text = "We are passionate about innovation and disrupting the industry."
    desired_tone = "professional"
    
    with patch.object(email_service.llm_client, 'generate', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "The company uses energetic, forward-thinking language."
        
        result = await email_service._analyze_company_tone(company_text, desired_tone)
        
        assert "energetic" in result
        assert mock_generate.called


@pytest.mark.asyncio
async def test_synthesize_value_propositions(email_service):
    """Test value proposition synthesis"""
    resume_text = "10 years experience in cloud architecture"
    company_text = "Looking to migrate to cloud infrastructure"
    pain_point = "Current infrastructure is not scalable"
    
    with patch.object(email_service.llm_client, 'generate_json', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = {
            "propositions": [
                "Design scalable cloud architecture",
                "Reduce infrastructure costs by 50%",
                "Implement DevOps best practices"
            ]
        }
        
        result = await email_service._synthesize_value_propositions(
            resume_text, company_text, pain_point
        )
        
        assert len(result) == 3
        assert "scalable" in result[0]


def test_add_tracking_pixel(email_service):
    """Test adding tracking pixel to email"""
    body = "<html><body>Email content</body></html>"
    tracking_url = "http://example.com/track/123"
    
    result = email_service._add_tracking_pixel(body, tracking_url)
    
    assert tracking_url in result
    assert '<img src="' in result
    assert 'width="1" height="1"' in result


def test_extract_skills(email_service):
    """Test skill extraction from resume"""
    text = "Skills: Python, JavaScript, Docker, Kubernetes, Machine Learning"
    
    skills = email_service._extract_skills(text)
    
    assert "Python" in skills
    assert "Docker" in skills
    assert "Machine Learning" in skills


def test_extract_experience_years(email_service):
    """Test experience years extraction"""
    text = "Software Engineer with 8 years of experience in building scalable systems"
    
    years = email_service._extract_experience_years(text)
    
    assert years == 8


@pytest.mark.asyncio
async def test_parse_resume_pdf(email_service):
    """Test PDF resume parsing"""
    # Create mock PDF content
    mock_pdf_content = b"mock pdf content"
    
    with patch.object(email_service, '_parse_pdf') as mock_parse:
        mock_parse.return_value = "Extracted text from PDF"
        
        result = await email_service.parse_resume(mock_pdf_content, "resume.pdf")
        
        assert result.success
        assert result.text_content == "Extracted text from PDF"


@pytest.mark.asyncio
async def test_record_email_open(email_service):
    """Test recording email open event"""
    email_id = "test-123"
    timestamp = datetime.utcnow()
    
    await email_service.record_email_open(email_id, timestamp)
    
    # Check that event was recorded
    events = [e for e in email_service.tracking_events if e['email_id'] == email_id]
    assert len(events) == 1
    assert events[0]['event_type'] == 'open'


@pytest.mark.asyncio
async def test_get_email_stats(email_service):
    """Test getting email statistics"""
    email_id = "test-456"
    
    # Add some tracking events
    email_service.tracking_events = [
        {"email_id": email_id, "event_type": "open", "timestamp": "2024-01-01T10:00:00"},
        {"email_id": email_id, "event_type": "open", "timestamp": "2024-01-01T11:00:00"},
    ]
    
    stats = await email_service.get_email_stats(email_id)
    
    assert stats['email_id'] == email_id
    assert stats['total_opens'] == 2
    assert stats['first_open'] == "2024-01-01T10:00:00"
    assert stats['last_open'] == "2024-01-01T11:00:00"


@pytest.mark.asyncio
async def test_generate_subject(email_service):
    """Test email subject generation"""
    with patch.object(email_service.llm_client, 'generate', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "Partnership Opportunity with Example Corp"
        
        subject = await email_service._generate_subject(
            "John Smith",
            "CTO",
            "Reduce costs by 40%",
            "Schedule meeting"
        )
        
        assert subject == "Partnership Opportunity with Example Corp"
        assert mock_generate.called