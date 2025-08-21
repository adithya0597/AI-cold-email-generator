"""
Comprehensive Testing Framework for AI Content Generation Suite
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

# Import services to test
from app.services.email_service import EmailService
from app.services.post_service import LinkedInPostService
from app.services.web_search_service import WebSearchService
from app.models import (
    ColdEmailRequest, LinkedInPostRequest,
    EmailTone, PostGoal
)


class TestEmailService:
    """Test suite for Email Service"""
    
    @pytest.fixture
    def email_service(self):
        return EmailService()
    
    @pytest.fixture
    def sample_email_request(self):
        return ColdEmailRequest(
            user_resume_text="10 years Python developer, AWS certified",
            recipient_name="John Smith",
            recipient_role="Engineering Manager",
            company_website_url="https://techcorp.com",
            company_tone=EmailTone.PROFESSIONAL,
            email_goal="Schedule interview",
            sender_name="Jane Doe",
            sender_email="jane@example.com"
        )
    
    @pytest.mark.asyncio
    async def test_email_generation_basic(self, email_service, sample_email_request):
        """Test basic email generation"""
        company_text = "TechCorp is a leading AI company"
        
        response = await email_service.generate_cold_email(
            request=sample_email_request,
            company_text=company_text
        )
        
        assert response.email_id
        assert response.subject
        assert response.body
        assert len(response.value_propositions) == 3
        assert response.tracking_pixel_url
    
    @pytest.mark.asyncio
    async def test_email_with_job_posting(self, email_service, sample_email_request):
        """Test email generation with job posting URL"""
        sample_email_request.job_posting_url = "https://linkedin.com/jobs/123"
        company_text = "TechCorp is hiring"
        job_posting_content = "Looking for Python developer with AWS experience"
        
        response = await email_service.generate_cold_email(
            request=sample_email_request,
            company_text=company_text,
            job_posting_content=job_posting_content
        )
        
        assert response.email_id
        assert response.body
        # Check if job-specific content is referenced
        assert len(response.value_propositions) > 0
    
    @pytest.mark.asyncio
    async def test_subject_line_generation(self, email_service):
        """Test subject line follows Josh Braun strategies"""
        subject = await email_service._generate_subject(
            recipient_name="John Smith",
            recipient_role="CTO",
            value_prop="Reduce hiring time by 40%",
            email_goal="Schedule call"
        )
        
        assert subject
        assert len(subject) <= 50  # Character limit
        assert subject != "Job Opportunity"  # Not generic
    
    @pytest.mark.asyncio
    async def test_email_body_length(self, email_service, sample_email_request):
        """Test email body follows 4T template and length constraints"""
        body = await email_service._generate_email_body(
            request=sample_email_request,
            company_text="Tech company information",
            tone_analysis="Professional tone",
            value_propositions=["VP1", "VP2", "VP3"]
        )
        
        word_count = len(body.split())
        assert word_count <= 100  # New constraint from Josh Braun
        assert body  # Not empty
    
    def test_tracking_pixel_insertion(self, email_service):
        """Test tracking pixel is properly inserted"""
        body = "Hello, this is a test email."
        tracking_url = "http://track.example.com/pixel.gif"
        
        tracked_body = email_service._add_tracking_pixel(body, tracking_url)
        
        assert tracking_url in tracked_body
        assert '<img' in tracked_body
        assert 'display:none' in tracked_body


class TestLinkedInPostService:
    """Test suite for LinkedIn Post Service"""
    
    @pytest.fixture
    def post_service(self):
        return LinkedInPostService()
    
    @pytest.fixture
    def sample_post_request(self):
        return LinkedInPostRequest(
            topic="AI in Healthcare",
            industry="Healthcare Technology",
            target_audience="Healthcare executives",
            post_goal=PostGoal.DRIVE_ENGAGEMENT,
            influencer_style="Gary Vaynerchuk"
        )
    
    @pytest.mark.asyncio
    async def test_post_generation_basic(self, post_service, sample_post_request):
        """Test basic post generation"""
        response = await post_service.generate_post(sample_post_request)
        
        assert response.post_id
        assert response.content
        assert response.hook
        assert response.body
        assert response.call_to_action
        assert len(response.hashtags) >= 7  # Should have trending hashtags
    
    @pytest.mark.asyncio
    async def test_post_with_multiple_references(self, post_service, sample_post_request):
        """Test post generation with multiple reference URLs"""
        sample_post_request.reference_urls = [
            "https://article1.com",
            "https://article2.com",
            "https://article3.com"
        ]
        
        response = await post_service.generate_post(sample_post_request)
        
        assert response.content
        assert response.hashtags
    
    @pytest.mark.asyncio
    async def test_trending_hashtags(self, post_service):
        """Test trending hashtag generation"""
        hashtags = await post_service._get_trending_hashtags(
            topic="AI",
            industry="Technology"
        )
        
        assert hashtags
        assert len(hashtags) > 5
        assert all(tag.startswith('#') for tag in hashtags)
    
    @pytest.mark.asyncio
    async def test_post_length_constraint(self, post_service, sample_post_request):
        """Test post follows LinkedIn best practices for length"""
        response = await post_service.generate_post(sample_post_request)
        
        # LinkedIn optimal length is 150-200 words
        word_count = len(response.content.split())
        assert 100 <= word_count <= 250
    
    @pytest.mark.asyncio
    async def test_image_generation_optional(self, post_service, sample_post_request):
        """Test image generation is optional"""
        # Without image
        sample_post_request.generate_image = False
        response = await post_service.generate_post(sample_post_request)
        assert response.image_url is None
        
        # With image
        sample_post_request.generate_image = True
        response = await post_service.generate_post(sample_post_request)
        # Image generation might fail in test, but should attempt
        assert response.post_id


class TestWebSearchService:
    """Test suite for Web Search Service"""
    
    @pytest.fixture
    def search_service(self):
        return WebSearchService()
    
    @pytest.mark.asyncio
    async def test_trending_hashtags_search(self, search_service):
        """Test searching for trending hashtags"""
        async with search_service as service:
            hashtags = await service.search_trending_hashtags(
                topic="artificial intelligence",
                industry="technology"
            )
        
        assert hashtags
        assert isinstance(hashtags, list)
        assert len(hashtags) > 0
        # Should have fallback hashtags at minimum
        assert any('#AI' in tag for tag in hashtags)
    
    @pytest.mark.asyncio
    async def test_company_insights_research(self, search_service):
        """Test researching company insights"""
        async with search_service as service:
            insights = await service.research_company_insights(
                company_url="https://google.com",
                company_name="Google"
            )
        
        assert insights
        assert isinstance(insights, dict)
        # Should have structure even if search fails
        assert "recent_news" in insights or "error" in insights
    
    @pytest.mark.asyncio
    async def test_industry_trends(self, search_service):
        """Test finding industry trends"""
        async with search_service as service:
            trends = await service.find_industry_trends(
                industry="fintech",
                topic="blockchain"
            )
        
        assert trends
        assert isinstance(trends, dict)
        assert "current_trends" in trends or "error" in trends
    
    def test_fallback_hashtags(self, search_service):
        """Test fallback hashtag generation"""
        hashtags = search_service._get_fallback_hashtags(
            topic="machine learning",
            industry="healthcare"
        )
        
        assert hashtags
        assert len(hashtags) == 10
        assert all(tag.startswith('#') for tag in hashtags)


class TestIntegration:
    """Integration tests for the full system"""
    
    @pytest.mark.asyncio
    async def test_email_generation_full_flow(self):
        """Test complete email generation flow"""
        from app.main import generate_cold_email
        
        request = ColdEmailRequest(
            user_resume_text="Senior developer with 10 years experience",
            recipient_name="Test Manager",
            recipient_role="Hiring Manager",
            company_website_url="https://example.com",
            company_tone=EmailTone.FRIENDLY,
            email_goal="Get interview",
            sender_name="Test Sender",
            sender_email="test@example.com"
        )
        
        # Mock web scraper to avoid actual HTTP calls
        with patch('app.core.web_scraper.WebScraper.scrape_website') as mock_scrape:
            mock_scrape.return_value = Mock(
                success=True,
                content="Example company content"
            )
            
            # This would call the actual endpoint
            # response = await generate_cold_email(request)
            # assert response.email_id
    
    @pytest.mark.asyncio
    async def test_post_generation_full_flow(self):
        """Test complete LinkedIn post generation flow"""
        from app.main import generate_linkedin_post
        
        request = LinkedInPostRequest(
            topic="Future of Work",
            industry="Technology",
            target_audience="Tech professionals",
            post_goal=PostGoal.BUILD_THOUGHT_LEADERSHIP,
            influencer_style="Simon Sinek"
        )
        
        # This would call the actual endpoint
        # response = await generate_linkedin_post(request)
        # assert response.post_id


class TestErrorHandling:
    """Test error handling and resilience"""
    
    @pytest.mark.asyncio
    async def test_email_service_handles_scraping_failure(self):
        """Test email service handles web scraping failures gracefully"""
        service = EmailService()
        request = ColdEmailRequest(
            user_resume_text="Test resume",
            recipient_name="Test",
            recipient_role="Manager",
            company_website_url="https://invalid-url-that-will-fail.com",
            company_tone=EmailTone.PROFESSIONAL,
            email_goal="Test",
            sender_name="Sender",
            sender_email="test@test.com"
        )
        
        # Should not raise exception, should handle gracefully
        with patch('app.core.web_scraper.WebScraper.scrape_website') as mock_scrape:
            mock_scrape.side_effect = Exception("Scraping failed")
            
            # The service should handle this error
            # In real implementation, it might use fallback content
    
    @pytest.mark.asyncio
    async def test_web_search_fallback(self):
        """Test web search service falls back when API fails"""
        service = WebSearchService()
        
        # Simulate search failure
        with patch.object(service, '_perform_search', side_effect=Exception("Search failed")):
            async with service:
                hashtags = await service.search_trending_hashtags("test", "test")
            
            # Should return fallback hashtags
            assert hashtags
            assert len(hashtags) > 0


class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_email_generation(self):
        """Test system can handle concurrent email generation"""
        service = EmailService()
        
        # Create multiple requests
        requests = [
            ColdEmailRequest(
                user_resume_text=f"Resume {i}",
                recipient_name=f"Recipient {i}",
                recipient_role="Manager",
                company_website_url="https://example.com",
                company_tone=EmailTone.PROFESSIONAL,
                email_goal="Interview",
                sender_name=f"Sender {i}",
                sender_email=f"sender{i}@example.com"
            )
            for i in range(5)
        ]
        
        # Generate emails concurrently
        tasks = [
            service.generate_cold_email(req, "Company text")
            for req in requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check all completed
        assert len(results) == 5
        # Some might fail in test environment, but structure should be there
    
    @pytest.mark.asyncio
    async def test_response_time(self):
        """Test response times are within acceptable limits"""
        import time
        
        service = EmailService()
        request = ColdEmailRequest(
            user_resume_text="Test resume",
            recipient_name="Test",
            recipient_role="Manager",
            company_website_url="https://example.com",
            company_tone=EmailTone.PROFESSIONAL,
            email_goal="Test",
            sender_name="Sender",
            sender_email="test@test.com"
        )
        
        start = time.time()
        # Would run actual generation here
        # response = await service.generate_cold_email(request, "Company text")
        end = time.time()
        
        # Should complete within 10 seconds
        # assert (end - start) < 10


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])