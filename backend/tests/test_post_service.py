"""
Test suite for LinkedIn post service
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from app.services.post_service import LinkedInPostService
from app.models import LinkedInPostRequest, PostGoal


@pytest.fixture
def post_service():
    """Create post service instance"""
    return LinkedInPostService()


@pytest.fixture
def sample_post_request():
    """Create sample post request"""
    return LinkedInPostRequest(
        topic="The future of AI in business",
        industry="Technology",
        target_audience="Tech leaders and entrepreneurs",
        post_goal=PostGoal.DRIVE_ENGAGEMENT,
        influencer_style="Simon Sinek",
        hashtags_count=5
    )


@pytest.mark.asyncio
async def test_generate_post_with_influencer_style(post_service, sample_post_request):
    """Test post generation with pre-selected influencer style"""
    with patch.object(post_service.llm_client, 'generate', new_callable=AsyncMock) as mock_generate:
        with patch.object(post_service.llm_client, 'generate_json', new_callable=AsyncMock) as mock_generate_json:
            # Mock responses
            mock_generate.return_value = """Why do we embrace AI?

Not for the technology itself, but for what it enables us to become.

When we understand our 'why', the 'how' becomes clear.

What's your why for adopting AI?"""
            
            mock_generate_json.return_value = [
                "#AI", "#Leadership", "#Innovation", "#Technology", "#Future"
            ]
            
            result = await post_service.generate_post(sample_post_request)
            
            assert result.post_id is not None
            assert "Why" in result.content
            assert len(result.hashtags) == 5
            assert result.style_analysis is not None


@pytest.mark.asyncio
async def test_generate_post_with_custom_author(post_service):
    """Test post generation with custom author style"""
    request = LinkedInPostRequest(
        topic="Remote work",
        industry="Technology",
        target_audience="Managers",
        post_goal=PostGoal.BUILD_THOUGHT_LEADERSHIP,
        influencer_style="custom",
        custom_author_name="Satya Nadella",
        hashtags_count=3
    )
    
    with patch.object(post_service.llm_client, 'generate', new_callable=AsyncMock) as mock_generate:
        with patch.object(post_service.llm_client, 'generate_json', new_callable=AsyncMock) as mock_generate_json:
            mock_generate.return_value = "Empowering every person and organization..."
            mock_generate_json.return_value = ["#RemoteWork", "#Leadership", "#Future"]
            
            result = await post_service.generate_post(request)
            
            assert "Satya Nadella" in result.style_analysis
            assert len(result.hashtags) == 3


def test_parse_post_components(post_service):
    """Test parsing post into components"""
    content = """🚀 This is the hook!

This is the main body of the post.
It contains valuable insights.

What's your take on this? Share your thoughts below!"""
    
    hook, body, cta = post_service._parse_post_components(content)
    
    assert "hook" in hook
    assert "valuable insights" in body
    assert "Share your thoughts" in cta


@pytest.mark.asyncio
async def test_generate_hashtags(post_service):
    """Test hashtag generation"""
    with patch.object(post_service.llm_client, 'generate_json', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = {
            "hashtags": ["#AI", "#Technology", "#Innovation"]
        }
        
        hashtags = await post_service._generate_hashtags("AI", "Technology", 3)
        
        assert len(hashtags) == 3
        assert all(tag.startswith('#') for tag in hashtags)


@pytest.mark.asyncio
async def test_generate_influencer_style_post(post_service, sample_post_request):
    """Test generating post with specific influencer style"""
    with patch.object(post_service.llm_client, 'generate', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "Start with why. The technology is just the tool..."
        
        result = await post_service._generate_influencer_style_post(sample_post_request)
        
        assert "Start with why" in result
        mock_generate.assert_called_once()


@pytest.mark.asyncio
async def test_generate_default_post(post_service):
    """Test generating post with default style"""
    request = LinkedInPostRequest(
        topic="Cloud computing",
        industry="Technology",
        target_audience="IT professionals",
        post_goal=PostGoal.GENERATE_LEADS,
        influencer_style="default",
        hashtags_count=5
    )
    
    with patch.object(post_service.llm_client, 'generate', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "Professional post about cloud computing..."
        
        result = await post_service._generate_default_post(request)
        
        assert "cloud computing" in result.lower()








@pytest.mark.asyncio
async def test_search_author_content(post_service):
    """Test searching for author content"""
    author_name = "Gary Vaynerchuk"
    
    results = await post_service.search_author_content(author_name)
    
    assert isinstance(results, list)
    assert len(results) > 0


def test_influencer_styles_defined(post_service):
    """Test that influencer styles are properly defined"""
    assert len(post_service.INFLUENCER_STYLES) >= 6
    assert "Gary Vaynerchuk" in post_service.INFLUENCER_STYLES
    assert "Simon Sinek" in post_service.INFLUENCER_STYLES
    
    for style_name, style_info in post_service.INFLUENCER_STYLES.items():
        assert "description" in style_info
        assert "characteristics" in style_info
        assert "tone" in style_info