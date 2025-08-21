"""
Web Search Service for Real-time Information Gathering
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import os
import re

from ..core.constants import (
    SEARCH_TIMEOUT, MAX_SEARCH_RESULTS, MIN_HASHTAG_RELEVANCE,
    HASHTAG_LENGTH_LIMIT, CACHE_TTL_SECONDS
)

logger = logging.getLogger(__name__)


class WebSearchService:
    """Service for performing web searches to gather real-time information"""
    
    def __init__(self):
        self.search_api_key = os.getenv("SERP_API_KEY", "")
        self.session = None
        self.timeout = SEARCH_TIMEOUT
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    async def search_trending_hashtags(self, topic: str, industry: str) -> List[str]:
        """
        Search for real-time trending hashtags SPECIFIC to the topic
        
        Args:
            topic: The main topic of the post
            industry: The industry context
            
        Returns:
            List of trending hashtags with # prefix
        """
        try:
            # Parse topic for key concepts
            topic_keywords = self._extract_topic_keywords(topic)
            
            # Build highly specific search queries based on the actual topic
            queries = [
                f'LinkedIn hashtags "{topic}" trending 2024',
                f'best hashtags for {topic} posts LinkedIn',
                f'{" ".join(topic_keywords[:2])} hashtags viral LinkedIn',
                f'"{industry}" "{topic}" popular hashtags social media',
                f'hashtags about {topic} high engagement LinkedIn'
            ]
            
            # Add keyword-specific searches
            for keyword in topic_keywords[:3]:  # Top 3 keywords
                queries.append(f'#{keyword} related hashtags trending')
            
            all_hashtags = []
            hashtag_scores = {}  # Track relevance scores
            
            for query in queries:
                results = await self._perform_search(query)
                hashtags = self._extract_hashtags_from_results(results)
                
                # Score hashtags based on relevance to topic
                for hashtag in hashtags:
                    relevance = self._calculate_hashtag_relevance(hashtag, topic, topic_keywords)
                    if hashtag not in hashtag_scores or hashtag_scores[hashtag] < relevance:
                        hashtag_scores[hashtag] = relevance
            
            # Sort by relevance score
            sorted_hashtags = sorted(hashtag_scores.items(), key=lambda x: x[1], reverse=True)
            top_hashtags = [tag for tag, score in sorted_hashtags if score > MIN_HASHTAG_RELEVANCE]
            
            # Add topic-specific generated hashtags
            generated_hashtags = self._generate_topic_hashtags(topic, topic_keywords, industry)
            top_hashtags.extend(generated_hashtags)
            
            # Deduplicate while preserving order
            seen = set()
            unique_hashtags = []
            for tag in top_hashtags:
                if tag.lower() not in seen:
                    seen.add(tag.lower())
                    unique_hashtags.append(tag)
            
            # Add fallback only if we don't have enough relevant ones
            if len(unique_hashtags) < 5:
                fallback = self._get_topic_specific_fallback(topic, industry)
                unique_hashtags.extend(fallback)
            
            return unique_hashtags[:15]  # Return top 15 most relevant
            
        except Exception as e:
            logger.error(f"Error searching trending hashtags: {e}")
            return self._get_fallback_hashtags(topic, industry)
    
    async def research_company_insights(self, company_url: str, company_name: str = None) -> Dict[str, Any]:
        """
        Research recent company news, initiatives, and insights
        
        Args:
            company_url: Company website URL
            company_name: Optional company name for better search
            
        Returns:
            Dictionary with company insights
        """
        try:
            insights = {
                "recent_news": [],
                "initiatives": [],
                "hiring_trends": [],
                "company_culture": [],
                "recent_achievements": []
            }
            
            # Extract company name from URL if not provided
            if not company_name:
                company_name = company_url.replace("https://", "").replace("http://", "").split(".")[0]
            
            # Search queries for different aspects
            searches = {
                "recent_news": f'"{company_name}" news announcement 2024',
                "initiatives": f'"{company_name}" new initiative project launch',
                "hiring_trends": f'"{company_name}" hiring expansion team growth',
                "achievements": f'"{company_name}" award achievement milestone funding'
            }
            
            for category, query in searches.items():
                results = await self._perform_search(query)
                insights[category] = self._extract_insights(results, category)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error researching company: {e}")
            return {"error": str(e), "fallback": True}
    
    async def find_industry_trends(self, industry: str, topic: str = None) -> Dict[str, Any]:
        """
        Find current trends and hot topics in an industry
        
        Args:
            industry: The industry to research
            topic: Optional specific topic within the industry
            
        Returns:
            Dictionary with industry trends
        """
        try:
            trends = {
                "current_trends": [],
                "emerging_technologies": [],
                "industry_challenges": [],
                "thought_leaders": [],
                "hot_topics": []
            }
            
            # Build search queries
            base_query = f"{industry} industry trends 2024"
            if topic:
                base_query += f" {topic}"
            
            queries = {
                "current_trends": f"{base_query} current state",
                "emerging_tech": f"{industry} emerging technology innovation",
                "challenges": f"{industry} challenges problems solving",
                "thought_leaders": f"{industry} thought leaders influencers experts",
                "hot_topics": f"{industry} discussion debate hot topics"
            }
            
            for category, query in queries.items():
                results = await self._perform_search(query)
                trends[category] = self._extract_insights(results, category)
            
            return trends
            
        except Exception as e:
            logger.error(f"Error finding industry trends: {e}")
            return {"error": str(e), "fallback": True}
    
    async def research_competitor_strategies(self, company: str, competitors: List[str] = None) -> Dict[str, Any]:
        """
        Research competitor strategies and positioning
        
        Args:
            company: The main company
            competitors: Optional list of known competitors
            
        Returns:
            Dictionary with competitive intelligence
        """
        try:
            if not competitors:
                # Search for competitors
                search_results = await self._perform_search(f"{company} competitors alternatives vs")
                competitors = self._extract_company_names(search_results)[:5]
            
            competitive_intel = {
                "competitors": competitors,
                "strategies": {},
                "differentiators": {},
                "market_position": {}
            }
            
            for competitor in competitors[:3]:  # Limit to top 3
                intel = await self._perform_search(f"{competitor} strategy announcement product")
                competitive_intel["strategies"][competitor] = self._extract_insights(intel, "strategy")
            
            return competitive_intel
            
        except Exception as e:
            logger.error(f"Error researching competitors: {e}")
            return {"error": str(e), "fallback": True}
    
    async def _perform_search(self, query: str) -> Dict[str, Any]:
        """
        Perform actual web search using available API or scraping
        
        Args:
            query: Search query string
            
        Returns:
            Search results dictionary
        """
        try:
            # If we have SERP API key, use it
            if self.search_api_key:
                return await self._serp_api_search(query)
            
            # Otherwise, use Google search scraping
            return await self._google_search_scrape(query)
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return {"results": [], "error": str(e)}
    
    async def _serp_api_search(self, query: str) -> Dict[str, Any]:
        """Use SERP API for search"""
        # Implementation for SERP API
        # This would use a real search API service
        pass
    
    async def _google_search_scrape(self, query: str) -> Dict[str, Any]:
        """Scrape Google search results"""
        try:
            if not self.session:
                self.session = httpx.AsyncClient(timeout=self.timeout)
            
            # Build Google search URL
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            # Add headers to avoid blocking
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = await self.session.get(search_url, headers=headers)
            
            if response.status_code == 200:
                # Extract search results (simplified)
                # In production, use proper HTML parsing
                content = response.text
                return {
                    "results": self._parse_search_results(content),
                    "query": query,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            return {"results": [], "error": f"Status code: {response.status_code}"}
            
        except Exception as e:
            logger.error(f"Google search scrape failed: {e}")
            return {"results": [], "error": str(e)}
    
    def _parse_search_results(self, html_content: str) -> List[Dict[str, str]]:
        """Parse search results from HTML"""
        # Simplified parsing - in production use BeautifulSoup
        results = []
        # Extract title, URL, snippet
        # This is a placeholder - implement proper parsing
        return results
    
    def _extract_hashtags_from_results(self, results: Dict[str, Any]) -> List[str]:
        """Extract hashtags from search results"""
        hashtags = []
        
        # Look for hashtag patterns in results
        for result in results.get("results", []):
            content = result.get("snippet", "") + " " + result.get("title", "")
            # Find hashtag patterns
            found_tags = re.findall(r'#\w+', content)
            hashtags.extend(found_tags)
        
        return hashtags
    
    def _extract_insights(self, results: Dict[str, Any], category: str) -> List[str]:
        """Extract insights from search results"""
        insights = []
        
        for result in results.get("results", [])[:MAX_SEARCH_RESULTS]:
            insight = {
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "url": result.get("url", ""),
                "relevance": self._calculate_relevance(result, category)
            }
            insights.append(insight)
        
        return insights
    
    def _calculate_relevance(self, result: Dict[str, str], category: str) -> float:
        """Calculate relevance score for a search result"""
        # Simple relevance scoring
        score = 0.5
        
        # Check for category keywords
        content = (result.get("title", "") + " " + result.get("snippet", "")).lower()
        
        category_keywords = {
            "news": ["announce", "launch", "new", "update"],
            "strategy": ["strategy", "plan", "approach", "focus"],
            "achievement": ["award", "milestone", "success", "achievement"],
            "hiring": ["hiring", "recruit", "job", "team", "expand"]
        }
        
        for keyword in category_keywords.get(category, []):
            if keyword in content:
                score += 0.1
        
        return min(score, 1.0)
    
    def _extract_company_names(self, results: Dict[str, Any]) -> List[str]:
        """Extract company names from search results"""
        companies = []
        
        for result in results.get("results", []):
            # Simple extraction - look for capitalized words
            title = result.get("title", "")
            words = title.split()
            for word in words:
                if word[0].isupper() and len(word) > 2:
                    companies.append(word)
        
        return list(set(companies))
    
    def _extract_topic_keywords(self, topic: str) -> List[str]:
        """Extract key concepts from the topic for better hashtag search"""
        # Remove common words and extract meaningful keywords
        stop_words = {'the', 'in', 'of', 'and', 'for', 'to', 'with', 'on', 'at', 'by', 'from', 'how', 'why', 'what'}
        
        # Split topic into words
        words = topic.lower().split()
        keywords = []
        
        # Extract meaningful keywords
        for word in words:
            if word not in stop_words and len(word) > 2:
                keywords.append(word)
        
        # Also extract potential compound terms
        if 'ai' in topic.lower():
            keywords.append('artificialintelligence')
        if 'machine learning' in topic.lower():
            keywords.append('machinelearning')
            keywords.append('ml')
        if 'data' in topic.lower() and 'science' in topic.lower():
            keywords.append('datascience')
        
        return keywords
    
    def _calculate_hashtag_relevance(self, hashtag: str, topic: str, keywords: List[str]) -> float:
        """Calculate how relevant a hashtag is to the specific topic"""
        hashtag_lower = hashtag.lower().replace('#', '')
        topic_lower = topic.lower()
        score = 0.0
        
        # Direct topic match
        if topic_lower.replace(' ', '') in hashtag_lower:
            score += 1.0
        
        # Keyword matches
        for keyword in keywords:
            if keyword in hashtag_lower:
                score += 0.5
            # Partial match
            elif len(keyword) > 4 and keyword[:4] in hashtag_lower:
                score += 0.2
        
        # Check if hashtag contains topic words
        topic_words = topic_lower.split()
        for word in topic_words:
            if len(word) > 3 and word in hashtag_lower:
                score += 0.3
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _generate_topic_hashtags(self, topic: str, keywords: List[str], industry: str) -> List[str]:
        """Generate hashtags directly from the topic"""
        generated = []
        
        # Create hashtag from full topic
        topic_hashtag = '#' + topic.replace(' ', '').replace('-', '')
        if len(topic_hashtag) <= HASHTAG_LENGTH_LIMIT:
            generated.append(topic_hashtag)
        
        # Create hashtags from keywords
        for keyword in keywords[:5]:
            hashtag = '#' + keyword.capitalize()
            generated.append(hashtag)
        
        # Industry + topic combination
        if len(keywords) > 0:
            industry_topic = f"#{industry.replace(' ', '')}{keywords[0].capitalize()}"
            if len(industry_topic) <= HASHTAG_LENGTH_LIMIT:
                generated.append(industry_topic)
        
        return generated
    
    def _get_topic_specific_fallback(self, topic: str, industry: str) -> List[str]:
        """Get fallback hashtags specific to the topic when search fails"""
        topic_lower = topic.lower()
        fallback = []
        
        # Topic-specific mappings
        topic_hashtags = {
            'ai': ['#ArtificialIntelligence', '#AI', '#MachineLearning', '#DeepLearning', '#AIInnovation'],
            'remote': ['#RemoteWork', '#WorkFromHome', '#DigitalNomad', '#RemoteTeams', '#FutureOfWork'],
            'sustainability': ['#Sustainability', '#ESG', '#ClimateAction', '#GreenTech', '#SustainableBusiness'],
            'leadership': ['#Leadership', '#LeadershipDevelopment', '#ExecutiveLeadership', '#ThoughtLeadership'],
            'startup': ['#Startup', '#Entrepreneurship', '#StartupLife', '#Founders', '#VentureCapital'],
            'cybersecurity': ['#Cybersecurity', '#InfoSec', '#DataSecurity', '#CyberSafety', '#SecurityAwareness'],
            'blockchain': ['#Blockchain', '#Web3', '#Crypto', '#DeFi', '#NFT'],
            'data': ['#DataScience', '#BigData', '#DataAnalytics', '#DataDriven', '#BusinessIntelligence'],
            'cloud': ['#CloudComputing', '#AWS', '#Azure', '#CloudMigration', '#CloudNative'],
            'agile': ['#Agile', '#Scrum', '#ProjectManagement', '#AgileTransformation', '#ProductManagement']
        }
        
        # Find matching topics
        for key, tags in topic_hashtags.items():
            if key in topic_lower:
                fallback.extend(tags[:3])
        
        # Add industry-specific tags
        industry_lower = industry.lower()
        if 'tech' in industry_lower:
            fallback.extend(['#TechIndustry', '#Technology', '#Innovation'])
        elif 'health' in industry_lower:
            fallback.extend(['#Healthcare', '#HealthTech', '#MedTech'])
        elif 'finance' in industry_lower:
            fallback.extend(['#Finance', '#Fintech', '#Banking'])
        
        # Always add the topic as a hashtag
        topic_words = topic.split()
        for word in topic_words:
            if len(word) > 3:
                fallback.append(f'#{word.capitalize()}')
        
        # Remove duplicates and return
        return list(dict.fromkeys(fallback))[:10]


# Singleton instance
web_search_service = WebSearchService()