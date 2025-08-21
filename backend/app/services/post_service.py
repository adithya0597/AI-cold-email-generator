"""
LinkedIn post generation and tracking service
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import re
import httpx

from ..models import (
    LinkedInPostRequest, LinkedInPostResponse,
    PostGoal
)
from ..core.llm_clients import LLMClient
from ..core.constants import (
    MAX_POST_LENGTH, MAX_HASHTAGS, MAX_REFERENCE_URLS,
    MAX_URL_CONTENT_LENGTH, DEFAULT_IMAGE_SIZE, IMAGE_PLACEHOLDER_URL,
    DALL_E_MODEL, MIN_HASHTAG_RELEVANCE, HASHTAG_LENGTH_LIMIT
)

logger = logging.getLogger(__name__)


class LinkedInPostService:
    """Service for generating LinkedIn posts and tracking metrics"""
    
    # Pre-defined influencer styles
    INFLUENCER_STYLES = {
        "Gary Vaynerchuk": {
            "description": "Direct, energetic, motivational with strong calls to action",
            "characteristics": ["Short punchy sentences", "Emojis", "Hashtags", "Questions to audience"],
            "tone": "enthusiastic and urgent"
        },
        "Simon Sinek": {
            "description": "Thoughtful, philosophical, focusing on 'why' and purpose",
            "characteristics": ["Storytelling", "Deep insights", "Leadership focus", "Inspirational"],
            "tone": "thoughtful and inspiring"
        },
        "Brené Brown": {
            "description": "Vulnerable, authentic, research-based with personal stories",
            "characteristics": ["Personal anecdotes", "Research citations", "Emotional connection", "Authenticity"],
            "tone": "warm and authentic"
        },
        "Neil Patel": {
            "description": "Data-driven, tactical, actionable marketing insights",
            "characteristics": ["Statistics", "Numbered lists", "Actionable tips", "Case studies"],
            "tone": "informative and practical"
        },
        "Arianna Huffington": {
            "description": "Wellness-focused, balanced perspective on success",
            "characteristics": ["Work-life balance", "Well-being focus", "Personal growth", "Mindfulness"],
            "tone": "calm and reflective"
        },
        "Adam Grant": {
            "description": "Research-backed organizational psychology insights",
            "characteristics": ["Academic research", "Workplace insights", "Counter-intuitive findings", "Questions"],
            "tone": "intellectual and curious"
        }
    }
    
    def __init__(self):
        self.llm_client = LLMClient()
        
        # Import author styles service for custom styles
        from .author_styles_service import AuthorStylesService
        self.author_styles_service = AuthorStylesService()
        
        # Storage (in production, use database)
        self.posts_storage = {}
    
    async def generate_post(self, request: LinkedInPostRequest) -> LinkedInPostResponse:
        """
        Generate a LinkedIn post based on request parameters
        
        Args:
            request: Post generation request
            
        Returns:
            LinkedInPostResponse with generated post
        """
        try:
            # Generate unique post ID
            post_id = str(uuid.uuid4())
            
            # Scrape reference URLs if provided
            reference_content = None
            reference_data = []
            if request.reference_urls:
                from ..core.web_scraper import WebScraper
                web_scraper = WebScraper()
                
                for url in request.reference_urls[:MAX_REFERENCE_URLS]:
                    if url.strip():  # Only process non-empty URLs
                        try:
                            reference_result = await web_scraper.scrape_website(url)
                            if reference_result.success:
                                content_snippet = reference_result.content[:MAX_URL_CONTENT_LENGTH]
                                reference_data.append({
                                    'url': url,
                                    'content': content_snippet,
                                    'title': self._extract_title_from_content(content_snippet)
                                })
                                logger.info(f"Successfully scraped reference URL: {url}")
                            else:
                                logger.warning(f"Failed to scrape reference URL: {url}")
                        except Exception as e:
                            logger.error(f"Error scraping URL {url}: {str(e)}")
                
                # Combine all reference content
                if reference_data:
                    reference_content = self._combine_reference_content(reference_data)
            
            # Determine if using pre-selected or custom style
            if request.custom_author_name:
                # Generate with custom author style
                content = await self._generate_custom_style_post(request, reference_content, reference_data)
                style_analysis = f"Emulating {request.custom_author_name}'s writing style"
            elif request.influencer_style in self.INFLUENCER_STYLES:
                # Use pre-selected influencer style
                content = await self._generate_influencer_style_post(request, reference_content, reference_data)
                style_analysis = self.INFLUENCER_STYLES[request.influencer_style]["description"]
            else:
                # Default professional style
                content = await self._generate_default_post(request, reference_content, reference_data)
                style_analysis = "Professional and engaging LinkedIn style"
            
            # Parse the generated content into components
            hook, body, cta = self._parse_post_components(content)
            
            # Generate trending hashtags (always suggest 7-10 for optimal reach)
            hashtags = await self._generate_hashtags(
                request.topic,
                request.industry,
                MAX_HASHTAGS
            )
            
            # Calculate reading time (average 200 words per minute)
            word_count = len(content.split())
            reading_time = max(10, (word_count * 60) // MAX_POST_LENGTH)
            
            # Format final content with hashtags
            final_content = f"{content}\n\n{' '.join(hashtags)}"
            
            # Generate relevant image for the post only if requested
            image_data = None
            if request.generate_image:
                image_data = await self._generate_post_image(
                    topic=request.topic,
                    content=content,
                    goal=request.post_goal,
                    industry=request.industry
                )
            
            # Store post data (in production, use database)
            post_data = {
                "post_id": post_id,
                "request": request.dict(),
                "generated_at": datetime.utcnow().isoformat(),
                "content": final_content,
                "image_data": image_data
            }
            self.posts_storage[post_id] = post_data
            
            return LinkedInPostResponse(
                post_id=post_id,
                content=final_content,
                hook=hook,
                body=body,
                call_to_action=cta,
                hashtags=hashtags,
                estimated_reading_time=reading_time,
                style_analysis=style_analysis,
                image_url=image_data.get("url") if image_data else None,
                image_type=image_data.get("type") if image_data else None,
                image_prompt=image_data.get("prompt") if image_data else None,
                image_relevance_score=image_data.get("relevance_score") if image_data else None
            )
            
        except Exception as e:
            logger.error(f"Error generating LinkedIn post: {str(e)}")
            raise
    
    def _extract_title_from_content(self, content: str) -> str:
        """Extract a title or main topic from scraped content"""
        lines = content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) > 10 and len(line) < 100:
                return line
        return "Article content"
    
    def _combine_reference_content(self, reference_data: List[Dict]) -> str:
        """Combine multiple reference sources into a single context"""
        combined = "REFERENCE SOURCES:\n\n"
        for i, ref in enumerate(reference_data, 1):
            combined += f"Source {i}: {ref['title']}\n"
            combined += f"URL: {ref['url']}\n"
            combined += f"Content: {ref['content'][:800]}...\n\n"  # Limit per source
        
        return combined
    
    def _format_reference_context(self, reference_content: str, reference_data: Optional[List[Dict]] = None) -> str:
        """Format reference content for use in prompts"""
        if not reference_content:
            return ""
        
        context = "\n\nREFERENCE ARTICLES TO INCORPORATE:\n"
        if reference_data:
            context += f"You have {len(reference_data)} reference sources to draw insights from. "
            context += "Extract key insights, data points, and valuable information from these sources. "
            context += "Ensure the generated post explicitly references or builds upon these articles.\n"
        
        context += reference_content[:1500]  # Limit total context
        context += "\n\nIMPORTANT: The post MUST incorporate insights, data, or concepts from these reference sources. Make it clear that the post is informed by this external content."
        
        return context
    
    async def _generate_custom_style_post(self, request: LinkedInPostRequest, reference_content: Optional[str] = None, reference_data: Optional[List[Dict]] = None) -> str:
        """Generate post emulating a custom author's style"""
        
        # First, check if we have this author in our uploaded database
        author_samples = await self.author_styles_service.get_sample_posts_for_style(
            request.custom_author_name, 
            count=3
        )
        
        if author_samples:
            # Use actual posts from the uploaded database
            examples_text = ""
            for i, sample in enumerate(author_samples, 1):
                # Truncate long samples
                truncated = sample[:500] + "..." if len(sample) > 500 else sample
                examples_text += f"\nExample {i}:\n{truncated}\n"
            
            prompt = f"""
            You are an expert LinkedIn post generator. Create a post emulating the exact writing style of {request.custom_author_name}.
            
            Here are actual examples of {request.custom_author_name}'s posts:
            {examples_text}
            
            Based on these examples, write a NEW post about:
            Topic: {request.topic}
            Industry: {request.industry}
            Target Audience: {request.target_audience}
            Goal: {request.post_goal}
            
            {self._format_reference_context(reference_content, reference_data) if reference_content else ''}
            
            Important:
            - Match the author's tone, vocabulary, and sentence structure
            - Use similar formatting (emojis, line breaks, etc.)
            - Maintain the same level of formality/informality
            - Include similar types of calls to action
            - Keep the same approximate length as the examples
            - If reference articles are provided, explicitly incorporate their insights and data
            - Make clear connections between the referenced content and your post topic
            
            Write the post now:
            """
        else:
            # Fallback to general approach if author not in database
            prompt = f"""
            You are an expert LinkedIn post generator. Create a post emulating the writing style of {request.custom_author_name}.
            
            Topic: {request.topic}
            Industry: {request.industry}
            Target Audience: {request.target_audience}
            Goal: {request.post_goal}
            
            {self._format_reference_context(reference_content, reference_data) if reference_content else ''}
            
            Research suggests {request.custom_author_name} typically writes with certain patterns.
            Apply these general principles for thought leaders:
            - Unique perspective or contrarian view
            - Personal anecdotes or experiences
            - Clear value proposition
            - Engaging opening hook
            - Structured body with clear points
            - Strong call to action aligned with: {request.post_goal}
            - If reference articles are provided, cite insights and build upon them
            - Use data and examples from referenced sources to strengthen your points
            
            Structure the post with:
            1. HOOK: Attention-grabbing opening (1-2 lines)
            2. BODY: Main content with insights (3-4 paragraphs)
            3. CALL TO ACTION: Clear next step for readers
            
            Keep it between 150-200 words for optimal LinkedIn engagement.
            Make it authentic and valuable to the target audience.
            """
        
        content = await self.llm_client.generate(prompt, temperature=0.8)
        return content
    
    async def _generate_influencer_style_post(self, request: LinkedInPostRequest, reference_content: Optional[str] = None, reference_data: Optional[List[Dict]] = None) -> str:
        """Generate post in a pre-selected influencer style with strong goal focus"""
        
        style_info = self.INFLUENCER_STYLES[request.influencer_style]
        
        # Define specific strategies for each goal
        goal_strategies = {
            "Drive Engagement": {
                "hook": "Start with a controversial question or surprising statistic",
                "body": "Include personal story, ask for opinions, create discussion points",
                "cta": "End with 'What's your experience?' or 'Agree or disagree?'",
                "format": "Use polls, questions, and engagement triggers throughout"
            },
            "Generate Leads": {
                "hook": "Lead with a problem your audience faces",
                "body": "Showcase solution/expertise, include case study or results",
                "cta": "Offer free resource, consultation, or invite to DM for more info",
                "format": "Include clear value proposition and credibility markers"
            },
            "Build Thought Leadership": {
                "hook": "Share unique insight or contrarian viewpoint",
                "body": "Provide deep analysis, original framework, or industry prediction",
                "cta": "Invite to follow for more insights or share if valuable",
                "format": "Use data, research, and authoritative tone"
            }
        }
        
        goal_strategy = goal_strategies.get(str(request.post_goal), goal_strategies["Drive Engagement"])
        
        prompt = f"""
        Write a LinkedIn post in the style of {request.influencer_style} that STRONGLY focuses on: {request.post_goal}
        
        Style characteristics:
        - {style_info['description']}
        - Tone: {style_info['tone']}
        - Key elements: {', '.join(style_info['characteristics'])}
        
        Topic: {request.topic}
        Industry: {request.industry}
        Target Audience: {request.target_audience}
        
        {self._format_reference_context(reference_content, reference_data) if reference_content else ''}
        
        CRITICAL GOAL REQUIREMENTS for {request.post_goal}:
        - Hook: {goal_strategy['hook']}
        - Body: {goal_strategy['body']}
        - CTA: {goal_strategy['cta']}
        - Format: {goal_strategy['format']}
        - Reference Integration: If reference articles are provided, weave their insights throughout the post
        - Data Usage: Include specific data points, statistics, or examples from referenced sources
        
        VISUAL FORMATTING REQUIREMENTS:
        - Use line breaks between paragraphs for visual appeal
        - Keep paragraphs SHORT (2-3 lines max)
        - Use strategic emojis (2-3 per post maximum)
        - Include bullet points or numbered lists where appropriate
        - Bold important phrases using **text**
        - Add white space for readability
        
        Structure:
        1. HOOK (attention-grabbing opener with emoji)
        2. BODY (well-formatted with visual breaks)
        3. CALL TO ACTION (clear and separated)
        
        The post MUST be optimized to {request.post_goal} and be visually appealing.
        
        Include elements typical of {request.influencer_style}:
        {chr(10).join('- ' + char for char in style_info['characteristics'])}
        
        Keep it 150-200 words for optimal engagement.
        """
        
        content = await self.llm_client.generate(prompt, temperature=0.7)
        return content
    
    async def _generate_default_post(self, request: LinkedInPostRequest, reference_content: Optional[str] = None, reference_data: Optional[List[Dict]] = None) -> str:
        """Generate post in default professional style with strong goal alignment"""
        
        # Enhanced goal-specific templates
        goal_templates = {
            PostGoal.DRIVE_ENGAGEMENT: f"""
                ENGAGEMENT-OPTIMIZED POST WITH VISUAL FORMATTING:
                
                HOOK (Eye-catching opener with spacing):
                - Start with: "Unpopular opinion:" OR "Can we talk about..." OR "I was wrong about..."
                - Add ONE attention-grabbing emoji at the start (🔥, 💡, 🎯, ⚡, 🚀)
                - Use line break after hook for visual impact
                
                BODY (Visually scannable format):
                - Use SHORT paragraphs (2-3 lines max)
                - Add line breaks between key points
                - Include numbered or bulleted lists with emojis:
                  → Point one (with arrow)
                  → Point two
                  → Point three
                - Strategic emoji placement (1 per paragraph max)
                - Bold key phrases using **text**
                
                CTA (Clear and inviting):
                - Separate with line break
                - "What's your take? 👇"
                - "Agree? Disagree? Let me know in the comments"
                
                VISUAL FORMATTING RULES:
                - Maximum 2-3 emojis per post
                - Use line breaks for visual breathing room
                - Keep lines under 60 characters when possible
                - Use → ▸ • for bullet points
                - Add white space between sections
            """,
            
            PostGoal.GENERATE_LEADS: f"""
                LEAD GENERATION POST WITH PROFESSIONAL FORMATTING:
                
                HOOK (Problem-focused opener):
                - Start with a striking statistic or problem statement
                - "87% of [target audience] struggle with [problem] 📊"
                - Add line break for emphasis
                
                BODY (Value-driven format):
                - Structure as mini case study:
                  
                  The Challenge:
                  → Brief problem description
                  
                  The Solution:
                  ✓ Step 1 achieved X
                  ✓ Step 2 improved Y by 40%
                  ✓ Step 3 saved $Z
                  
                  The Result:
                  📈 Specific measurable outcome
                
                - Use data points and numbers
                - Keep professional but approachable tone
                
                CTA (Clear value exchange):
                - Separate with line break
                - "Want the full framework? Comment 'GUIDE' below 👇"
                - "3 spots left for free strategy call - DM me"
                
                VISUAL FORMATTING:
                - Use ✓ for achievements
                - Include 📊 📈 for data points
                - Maximum 2-3 professional emojis
                - Clear section breaks with white space
            """,
            
            PostGoal.BUILD_THOUGHT_LEADERSHIP: f"""
                THOUGHT LEADERSHIP POST WITH AUTHORITATIVE FORMATTING:
                
                HOOK (Bold insight opener):
                - Start with contrarian or unique perspective
                - "After 10 years in [industry], here's what everyone gets wrong 💭"
                - Use line break for impact
                
                BODY (Structured wisdom format):
                - Present as framework or principle:
                  
                  The Old Way:
                  ❌ Common misconception
                  
                  The New Reality:
                  ✅ Your unique insight
                  
                  Why This Matters:
                  • Impact point 1
                  • Impact point 2
                  • Future implication
                  
                - Include data or research reference
                - Create quotable moment in **bold**
                
                CTA (Authority building):
                - Separate with white space
                - "What's your perspective on this shift?"
                - "Follow for more [industry] insights 🔔"
                
                VISUAL FORMATTING:
                - Use ❌ and ✅ for contrast
                - Include 💭 🔍 🎯 sparingly
                - Bold key insights
                - Create visual hierarchy with spacing
                - Maximum 2-3 thoughtful emojis
            """
        }
        
        template = goal_templates.get(request.post_goal, goal_templates[PostGoal.DRIVE_ENGAGEMENT])
        
        prompt = f"""
        Create a LinkedIn post SPECIFICALLY OPTIMIZED for: {request.post_goal}
        
        Topic: {request.topic}
        Industry: {request.industry}
        Target Audience: {request.target_audience}
        
        {self._format_reference_context(reference_content, reference_data) if reference_content else ''}
        
        {template}
        
        CRITICAL: The post MUST be structured to achieve {request.post_goal}.
        Every line should contribute to this goal.
        
        IF REFERENCE ARTICLES ARE PROVIDED: The post must explicitly reference and build upon the content from these sources. Include specific insights, data points, quotes, or concepts from the referenced articles. Make it clear that the post is informed by and responds to this external content.
        
        Additional guidelines:
        - 150-200 words optimal
        - Use line breaks for readability
        - Professional but conversational
        - Focus on value to reader
        
        Write the post now:
        """
        
        content = await self.llm_client.generate(prompt, temperature=0.7)
        return content
    
    def _parse_post_components(self, content: str) -> tuple[str, str, str]:
        """Parse generated content into hook, body, and CTA"""
        
        lines = content.strip().split('\n')
        
        # Simple heuristic parsing
        # Hook is typically first 1-2 lines
        hook = lines[0] if lines else ""
        if len(lines) > 1 and len(lines[1]) < 100:  # Short second line might be part of hook
            hook = f"{lines[0]}\n{lines[1]}"
            body_start = 2
        else:
            body_start = 1
        
        # CTA is typically last 1-2 lines with questions or action words
        cta_keywords = ['?', 'share', 'comment', 'thoughts', 'connect', 'dm', 'link', 'click', 'join', 'download']
        cta = ""
        body_end = len(lines)
        
        for i in range(len(lines) - 1, max(len(lines) - 3, body_start - 1), -1):
            if any(keyword in lines[i].lower() for keyword in cta_keywords):
                cta = '\n'.join(lines[i:])
                body_end = i
                break
        
        if not cta and len(lines) > body_start:
            # If no clear CTA found, use last line
            cta = lines[-1]
            body_end = len(lines) - 1
        
        # Body is everything in between
        body = '\n'.join(lines[body_start:body_end]) if body_end > body_start else ""
        
        return hook, body, cta
    
    async def _generate_hashtags(self, topic: str, industry: str, count: int) -> List[str]:
        """Generate relevant and trending hashtags for the post"""
        
        # First, get trending hashtags based on topic and industry
        trending_hashtags = await self._get_trending_hashtags(topic, industry)
        
        prompt = f"""
        Generate relevant LinkedIn hashtags for a post about "{topic}" in the {industry} industry.
        
        Current trending hashtags to consider (use if relevant):
        {', '.join(trending_hashtags[:10])}
        
        Requirements:
        - Prioritize trending hashtags that are relevant
        - Mix of broad reach and niche hashtags
        - Include industry-specific tags
        - Popular LinkedIn hashtags for visibility
        - No spaces in hashtags
        - Proper capitalization (e.g., #DigitalMarketing)
        
        Generate 10 hashtags and rank them by relevance and potential reach.
        Return as a JSON object with:
        {{
            "hashtags": [list of hashtags],
            "trending_used": [which trending ones you included]
        }}
        """
        
        result = await self.llm_client.generate_json(prompt, temperature=0.5)
        
        if isinstance(result, dict) and 'hashtags' in result:
            hashtags = result['hashtags']
        elif isinstance(result, list):
            hashtags = result
        else:
            # Fallback to trending + topic hashtags
            hashtags = trending_hashtags[:5] + [
                f"#{topic.replace(' ', '')}",
                f"#{industry.replace(' ', '')}",
                "#LinkedIn",
                "#ProfessionalGrowth",
                "#BusinessInsights"
            ]
        
        # Ensure hashtags are properly formatted and topic-relevant
        formatted_hashtags = []
        topic_keywords = topic.lower().split()
        
        for tag in hashtags[:count]:
            if not tag.startswith('#'):
                tag = f"#{tag}"
            # Remove spaces and special characters
            tag = re.sub(r'[^\w#]', '', tag)
            
            # Verify relevance to topic (final filter)
            tag_lower = tag.lower()
            is_relevant = any(keyword in tag_lower for keyword in topic_keywords if len(keyword) > 3)
            
            # Always include if it's highly relevant, or if we don't have enough yet
            if is_relevant or len(formatted_hashtags) < 5:
                formatted_hashtags.append(tag)
        
        # If we still need more, add topic-based generated ones
        if len(formatted_hashtags) < count:
            # Generate hashtags directly from topic
            topic_hashtag = '#' + topic.replace(' ', '')
            if len(topic_hashtag) <= 30 and topic_hashtag not in formatted_hashtags:
                formatted_hashtags.insert(0, topic_hashtag)  # Put at beginning
            
            # Add topic word combinations
            words = [w.capitalize() for w in topic.split() if len(w) > 3]
            for word in words:
                if len(formatted_hashtags) >= count:
                    break
                word_tag = f'#{word}{industry.replace(" ", "")}'
                if len(word_tag) <= 30 and word_tag not in formatted_hashtags:
                    formatted_hashtags.append(word_tag)
        
        return formatted_hashtags[:count]
    
    async def _get_trending_hashtags(self, topic: str, industry: str) -> List[str]:
        """
        Get trending hashtags for the topic and industry
        Uses web search to find current trending hashtags
        """
        from ..core.web_scraper import WebScraper
        web_scraper = WebScraper()
        
        try:
            # Search for trending LinkedIn hashtags
            search_query = f"trending LinkedIn hashtags {industry} {topic} 2024"
            search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            
            # Get search results
            search_result = await web_scraper.scrape_website(search_url)
            
            if search_result.success:
                # Extract hashtags from search results using AI
                prompt = f"""
                Extract trending LinkedIn hashtags from this search result about {industry} and {topic}.
                
                Content: {search_result.content[:2000]}
                
                Return a JSON array of the most relevant trending hashtags (without # symbol).
                Focus on hashtags that are:
                - Currently trending (2024)
                - Relevant to {industry}
                - Related to {topic}
                - Popular on LinkedIn
                
                Return format: ["hashtag1", "hashtag2", ...]
                """
                
                result = await self.llm_client.generate_json(prompt, temperature=0.3)
                
                if isinstance(result, list):
                    # Add # symbol and return
                    return [f"#{tag}" if not tag.startswith('#') else tag for tag in result[:15]]
            
        except Exception as e:
            logger.warning(f"Could not fetch trending hashtags: {e}")
        
        # Fallback trending hashtags for 2024
        trending_2024 = [
            "#AI", "#ArtificialIntelligence", "#Innovation", "#FutureOfWork",
            "#DigitalTransformation", "#Sustainability", "#RemoteWork",
            "#Leadership", "#TechTrends", "#CareerGrowth", "#Entrepreneurship",
            "#DataScience", "#MachineLearning", "#CloudComputing", "#Cybersecurity"
        ]
        
        # Filter by relevance to industry
        industry_lower = industry.lower()
        relevant_trending = []
        
        if "tech" in industry_lower or "software" in industry_lower:
            relevant_trending = ["#TechTrends", "#CloudComputing", "#AI", "#DigitalTransformation"]
        elif "market" in industry_lower or "sales" in industry_lower:
            relevant_trending = ["#DigitalMarketing", "#GrowthHacking", "#B2B", "#ContentMarketing"]
        elif "finance" in industry_lower:
            relevant_trending = ["#Fintech", "#Blockchain", "#InvestmentStrategies", "#WealthManagement"]
        elif "health" in industry_lower:
            relevant_trending = ["#HealthTech", "#DigitalHealth", "#Wellness", "#HealthcareInnovation"]
        
        # Combine with general trending
        return list(set(relevant_trending + trending_2024[:5]))
    
    async def _generate_post_image(self, topic: str, content: str, goal: str, industry: str) -> Optional[Dict[str, Any]]:
        """
        Generate a relevant image for the LinkedIn post
        
        Args:
            topic: Post topic
            content: Generated post content
            goal: Post goal (engagement, leads, thought leadership)
            industry: Target industry
            
        Returns:
            Dictionary with image URL, type, prompt, and relevance score
        """
        try:
            # First, determine the best image type for this post
            image_type = await self._determine_image_type(content, goal, topic)
            
            # Generate appropriate image prompt based on type
            image_prompt = await self._create_image_prompt(
                image_type=image_type,
                topic=topic,
                content=content,
                industry=industry
            )
            
            # Generate the image using DALL-E
            image_url = await self._generate_dalle_image(image_prompt)
            
            # Validate image relevance
            relevance_score = await self._validate_image_relevance(
                image_prompt=image_prompt,
                post_content=content,
                topic=topic
            )
            
            return {
                "url": image_url,
                "type": image_type,
                "prompt": image_prompt,
                "relevance_score": relevance_score
            }
            
        except Exception as e:
            logger.warning(f"Could not generate image: {e}")
            return None
    
    async def _determine_image_type(self, content: str, goal: str, topic: str) -> str:
        """
        Determine the most appropriate image type for the post
        
        Returns one of: infographic, meme, chart, illustration, flowchart, comparison
        """
        prompt = f"""
        Based on this LinkedIn post, determine the BEST type of visual to accompany it.
        
        Post content: {content[:500]}
        Goal: {goal}
        Topic: {topic}
        
        Choose ONE from these options based on what would be most engaging:
        - "infographic": For data-heavy or educational content
        - "meme": For humorous or relatable content (only if appropriate)
        - "chart": For statistics or trends
        - "illustration": For concepts or storytelling
        - "flowchart": For processes or step-by-step content
        - "comparison": For before/after or old vs new concepts
        
        Consider:
        - Professional context (LinkedIn audience)
        - Goal alignment (what drives {goal}?)
        - Visual impact
        
        Return only the type name, nothing else.
        """
        
        image_type = await self.llm_client.generate(prompt, temperature=0.3, max_tokens=20)
        
        # Validate and default to illustration if unclear
        valid_types = ["infographic", "meme", "chart", "illustration", "flowchart", "comparison"]
        image_type = image_type.strip().lower()
        
        if image_type not in valid_types:
            image_type = "illustration"
            
        return image_type
    
    async def _create_image_prompt(self, image_type: str, topic: str, content: str, industry: str) -> str:
        """
        Create a detailed DALL-E prompt for the specific image type
        """
        # Extract key concepts from the post
        key_concepts_prompt = f"""
        Extract 2-3 key visual concepts from this post that should be in the image:
        {content[:300]}
        
        Return as comma-separated keywords.
        """
        key_concepts = await self.llm_client.generate(key_concepts_prompt, temperature=0.3, max_tokens=30)
        
        # Image type specific prompts
        type_templates = {
            "infographic": f"Modern, clean infographic design showing {key_concepts}, professional LinkedIn style, {industry} theme, minimalist with brand colors blue and white, high contrast, vector style",
            
            "meme": f"Professional business meme about {topic}, subtle humor, corporate-appropriate, featuring {key_concepts}, modern meme format, LinkedIn-friendly",
            
            "chart": f"Clean data visualization chart illustrating {key_concepts}, professional design, {industry} context, modern flat design, clear labels, LinkedIn post visual",
            
            "illustration": f"Professional business illustration depicting {key_concepts}, modern flat design style, {industry} setting, corporate colors, clean and engaging, LinkedIn-appropriate",
            
            "flowchart": f"Clear business flowchart showing {key_concepts}, modern design, professional layout, {industry} process, clean arrows and shapes, LinkedIn post visual",
            
            "comparison": f"Side-by-side comparison visual showing {key_concepts}, before vs after or old vs new, {industry} context, clean modern design, LinkedIn professional style"
        }
        
        base_prompt = type_templates.get(image_type, type_templates["illustration"])
        
        # Add quality modifiers
        final_prompt = f"{base_prompt}, high quality, professional, no text overlays, suitable for LinkedIn post, engaging visual, 16:9 aspect ratio"
        
        return final_prompt
    
    async def _generate_dalle_image(self, prompt: str) -> str:
        """
        Generate image using OpenAI's DALL-E API
        """
        try:
            # Use httpx to call OpenAI API directly
            api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                logger.warning("OpenAI API key not found for image generation")
                return IMAGE_PLACEHOLDER_URL
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": DALL_E_MODEL,
                        "prompt": prompt,
                        "n": 1,
                        "size": DEFAULT_IMAGE_SIZE
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    image_url = data['data'][0]['url']
                    return image_url
                else:
                    logger.error(f"DALL-E API error: {response.status_code} - {response.text}")
                    return IMAGE_PLACEHOLDER_URL
            
        except Exception as e:
            logger.error(f"DALL-E image generation failed: {e}")
            # Return a placeholder or stock image URL
            return IMAGE_PLACEHOLDER_URL
    
    async def _validate_image_relevance(self, image_prompt: str, post_content: str, topic: str) -> float:
        """
        Validate that the generated image is relevant to the post
        Returns a relevance score between 0 and 1
        """
        validation_prompt = f"""
        Rate the relevance of this image to the LinkedIn post (0.0 to 1.0):
        
        Image description: {image_prompt}
        Post topic: {topic}
        Post excerpt: {post_content[:200]}
        
        Consider:
        - Topic alignment
        - Professional appropriateness
        - Visual-content match
        - LinkedIn context
        
        Return only a decimal number between 0.0 and 1.0.
        """
        
        try:
            score_str = await self.llm_client.generate(validation_prompt, temperature=0.1, max_tokens=10)
            relevance_score = float(score_str.strip())
            
            # Ensure score is in valid range
            relevance_score = max(0.0, min(1.0, relevance_score))
            
            return relevance_score
            
        except:
            # Default to moderate relevance if validation fails
            return 0.7
    
    async def search_author_content(self, author_name: str) -> List[str]:
        """
        Search for sample content from a specific author
        In production, this would use a search API or web scraping
        
        Args:
            author_name: Name of the author to search
            
        Returns:
            List of sample content pieces
        """
        # First check our uploaded database
        samples = await self.author_styles_service.get_sample_posts_for_style(author_name, count=3)
        if samples:
            return samples
        
        # In production, implement real-time search
        # For now, return placeholder
        logger.info(f"Searching for content from {author_name}")
        
        # Simulate search results
        return [
            f"Sample post 1 from {author_name}",
            f"Sample post 2 from {author_name}"
        ]
    
    async def get_available_custom_authors(self) -> List[str]:
        """
        Get list of authors available in the uploaded database
        
        Returns:
            List of author names
        """
        authors = await self.author_styles_service.get_all_author_styles()
        return [author["author_name"] for author in authors]