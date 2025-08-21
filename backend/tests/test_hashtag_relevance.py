"""
Test Suite for Topic-Specific Hashtag Generation
"""

import pytest
import logging
from app.services.web_search_service import WebSearchService

logger = logging.getLogger(__name__)


class TestTopicSpecificHashtags:
    """Test that hashtags are relevant to the specific topic"""
    
    @pytest.fixture
    def search_service(self):
        return WebSearchService()
    
    def test_extract_topic_keywords(self, search_service):
        """Test keyword extraction from topics"""
        
        # Test case 1: AI in Healthcare
        keywords = search_service._extract_topic_keywords("AI in Healthcare")
        assert "healthcare" in keywords
        assert "artificialintelligence" in keywords
        assert "in" not in keywords  # Stop word should be removed
        
        # Test case 2: Remote Team Management
        keywords = search_service._extract_topic_keywords("Remote Team Management")
        assert "remote" in keywords
        assert "team" in keywords
        assert "management" in keywords
        
        # Test case 3: Machine Learning for Sales
        keywords = search_service._extract_topic_keywords("Machine Learning for Sales")
        assert "machine" in keywords
        assert "learning" in keywords
        assert "machinelearning" in keywords  # Compound term
        assert "sales" in keywords
    
    def test_hashtag_relevance_calculation(self, search_service):
        """Test relevance scoring for hashtags"""
        
        topic = "AI in Healthcare"
        keywords = ["healthcare", "artificialintelligence", "ai"]
        
        # Highly relevant hashtag
        score1 = search_service._calculate_hashtag_relevance(
            "#AIHealthcare", topic, keywords
        )
        assert score1 > 0.8  # Should be highly relevant
        
        # Partially relevant hashtag
        score2 = search_service._calculate_hashtag_relevance(
            "#Healthcare", topic, keywords
        )
        assert 0.3 < score2 < 0.8  # Should be moderately relevant
        
        # Irrelevant hashtag
        score3 = search_service._calculate_hashtag_relevance(
            "#Marketing", topic, keywords
        )
        assert score3 < 0.3  # Should be low relevance
    
    def test_generate_topic_hashtags(self, search_service):
        """Test direct hashtag generation from topic"""
        
        topic = "Sustainable Supply Chain Management"
        keywords = ["sustainable", "supply", "chain", "management"]
        industry = "Logistics"
        
        generated = search_service._generate_topic_hashtags(topic, keywords, industry)
        
        # Should include topic as hashtag
        assert "#SustainableSupplyChainManagement" in generated
        
        # Should include keyword hashtags
        assert "#Sustainable" in generated
        assert "#Supply" in generated
        
        # Should include industry+topic combination
        assert any("Logistics" in tag for tag in generated)
    
    def test_topic_specific_fallback(self, search_service):
        """Test fallback hashtags are topic-specific"""
        
        # Test AI topic
        fallback_ai = search_service._get_topic_specific_fallback(
            "AI in Manufacturing", "Manufacturing"
        )
        assert "#ArtificialIntelligence" in fallback_ai
        assert "#AI" in fallback_ai
        assert "#Manufacturing" in fallback_ai
        
        # Test Remote Work topic
        fallback_remote = search_service._get_topic_specific_fallback(
            "Remote Work Best Practices", "Technology"
        )
        assert "#RemoteWork" in fallback_remote
        assert "#WorkFromHome" in fallback_remote
        
        # Test Cybersecurity topic
        fallback_cyber = search_service._get_topic_specific_fallback(
            "Cybersecurity Threats in 2024", "Technology"
        )
        assert "#Cybersecurity" in fallback_cyber
        assert "#InfoSec" in fallback_cyber
    
    @pytest.mark.asyncio
    async def test_search_trending_hashtags_relevance(self, search_service):
        """Test that searched hashtags are relevant to topic"""
        
        # Test with specific topic
        topic = "Blockchain in Supply Chain"
        industry = "Logistics"
        
        async with search_service:
            hashtags = await search_service.search_trending_hashtags(topic, industry)
        
        # Check that hashtags are relevant
        assert len(hashtags) > 0
        
        # At least some hashtags should contain topic keywords
        topic_keywords = ["blockchain", "supply", "chain"]
        relevant_count = sum(
            1 for tag in hashtags 
            if any(keyword in tag.lower() for keyword in topic_keywords)
        )
        
        # At least 30% should be directly relevant
        assert relevant_count >= len(hashtags) * 0.3
    
    @pytest.mark.asyncio
    async def test_different_topics_get_different_hashtags(self, search_service):
        """Test that different topics generate different hashtags"""
        
        async with search_service:
            # Get hashtags for two different topics
            hashtags_ai = await search_service.search_trending_hashtags(
                "AI in Healthcare", "Healthcare"
            )
            hashtags_remote = await search_service.search_trending_hashtags(
                "Remote Work Culture", "Technology"
            )
        
        # Convert to sets for comparison
        set_ai = set(hashtags_ai)
        set_remote = set(hashtags_remote)
        
        # Should have different hashtags
        assert set_ai != set_remote
        
        # Overlap should be minimal (less than 30%)
        overlap = len(set_ai & set_remote)
        assert overlap < len(set_ai) * 0.3
        
        # AI hashtags should contain AI-related terms
        ai_relevant = any("#AI" in tag or "Intelligence" in tag for tag in hashtags_ai)
        assert ai_relevant
        
        # Remote hashtags should contain remote-related terms
        remote_relevant = any("Remote" in tag or "Work" in tag for tag in hashtags_remote)
        assert remote_relevant


class TestHashtagExamples:
    """Test specific examples to ensure quality"""
    
    @pytest.fixture
    def search_service(self):
        return WebSearchService()
    
    @pytest.mark.asyncio
    async def test_example_ai_healthcare(self, search_service):
        """Example: AI in Healthcare should generate healthcare AI hashtags"""
        
        topic = "AI in Healthcare"
        industry = "Healthcare Technology"
        
        async with search_service:
            hashtags = await search_service.search_trending_hashtags(topic, industry)
        
        # Log example hashtags for debugging
        logger.debug(f"\nExample hashtags for '{topic}':")
        for tag in hashtags[:10]:
            logger.debug(f"  {tag}")
        
        # Should include specific combinations
        expected_patterns = [
            "AIHealthcare", "HealthcareAI", "MedicalAI", 
            "HealthTech", "AIinMedicine", "DigitalHealth"
        ]
        
        matches = sum(
            1 for pattern in expected_patterns
            if any(pattern.lower() in tag.lower() for tag in hashtags)
        )
        
        assert matches >= 2  # At least 2 expected patterns should appear
    
    @pytest.mark.asyncio
    async def test_example_remote_team_management(self, search_service):
        """Example: Remote Team Management should generate specific management hashtags"""
        
        topic = "Remote Team Management"
        industry = "Business Management"
        
        async with search_service:
            hashtags = await search_service.search_trending_hashtags(topic, industry)
        
        # Log example hashtags for debugging
        logger.debug(f"\nExample hashtags for '{topic}':")
        for tag in hashtags[:10]:
            logger.debug(f"  {tag}")
        
        # Should include specific combinations
        expected_patterns = [
            "RemoteTeam", "TeamManagement", "RemoteManagement",
            "RemoteWork", "VirtualTeams", "RemoteLeadership"
        ]
        
        matches = sum(
            1 for pattern in expected_patterns
            if any(pattern.lower() in tag.lower() for tag in hashtags)
        )
        
        assert matches >= 2  # At least 2 expected patterns should appear
    
    @pytest.mark.asyncio
    async def test_example_sustainable_finance(self, search_service):
        """Example: Sustainable Finance should generate ESG and green finance hashtags"""
        
        topic = "Sustainable Finance and ESG Investing"
        industry = "Financial Services"
        
        async with search_service:
            hashtags = await search_service.search_trending_hashtags(topic, industry)
        
        # Log example hashtags for debugging
        logger.debug(f"\nExample hashtags for '{topic}':")
        for tag in hashtags[:10]:
            logger.debug(f"  {tag}")
        
        # Should include specific combinations
        expected_patterns = [
            "SustainableFinance", "ESG", "ESGInvesting",
            "GreenFinance", "ImpactInvesting", "ResponsibleInvesting"
        ]
        
        matches = sum(
            1 for pattern in expected_patterns
            if any(pattern.lower() in tag.lower() for tag in hashtags)
        )
        
        assert matches >= 2  # At least 2 expected patterns should appear


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--asyncio-mode=auto"])