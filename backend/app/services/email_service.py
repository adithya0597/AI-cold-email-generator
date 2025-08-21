"""
Email generation and tracking service
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import PyPDF2
import docx
import io
import re
import os

from ..models import (
    ColdEmailRequest, ColdEmailResponse,
    EmailTrackingEvent, ResumeParsingResult
)
from ..core.llm_clients import LLMClient
from ..core.llm_config import LLMConfig
from ..core.constants import (
    MAX_EMAIL_LENGTH, DEFAULT_TRACKING_BASE_URL
)

logger = logging.getLogger(__name__)


class EmailService:
    """Service for generating and tracking cold emails"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        # Create a fast client for simple tasks
        self.fast_llm_client = LLMClient()
        if hasattr(self.fast_llm_client, 'model'):
            self.fast_llm_client.model = LLMConfig.FAST_MODEL
        self.tracking_base_url = os.getenv("TRACKING_BASE_URL", DEFAULT_TRACKING_BASE_URL)
        self.email_storage = {}  # In production, use a database
        self.tracking_events = []  # In production, use a database
    
    async def generate_cold_email(
        self, 
        request: ColdEmailRequest,
        company_text: str,
        sender_linkedin_text: Optional[str] = None,
        job_posting_content: Optional[str] = None
    ) -> ColdEmailResponse:
        """
        Generate a personalized cold email
        
        Args:
            request: Email generation request
            company_text: Scraped company website text
            sender_linkedin_text: Optional scraped sender's LinkedIn profile text
            job_posting_content: Optional scraped job posting content
            
        Returns:
            ColdEmailResponse with generated email
        """
        try:
            # Generate unique email ID
            email_id = str(uuid.uuid4())
            
            # Run tone analysis and value propositions in parallel for speed
            import asyncio
            tone_task = self._analyze_company_tone(company_text, request.company_tone)
            value_task = self._synthesize_value_propositions(
                request.user_resume_text,
                company_text,
                request.pain_point,
                sender_linkedin_text,
                job_posting_content
            )
            
            # Execute both tasks concurrently
            tone_analysis, value_propositions = await asyncio.gather(tone_task, value_task)
            
            # Generate subject and body in parallel too
            subject_task = self._generate_subject(
                request.recipient_name,
                request.recipient_role,
                value_propositions[0] if value_propositions else "",
                request.email_goal
            )
            
            body_task = self._generate_email_body(
                request,
                company_text,
                tone_analysis,
                value_propositions,
                sender_linkedin_text,
                job_posting_content
            )
            
            # Execute both tasks concurrently
            subject, body = await asyncio.gather(subject_task, body_task)
            
            # Step 5: Add tracking pixel
            tracking_pixel_url = f"{self.tracking_base_url}/email/{email_id}/pixel.gif"
            body_with_tracking = self._add_tracking_pixel(body, tracking_pixel_url)
            
            # Store email data (in production, use database)
            email_data = {
                "email_id": email_id,
                "request": request.dict(),
                "generated_at": datetime.utcnow().isoformat(),
                "subject": subject,
                "body": body_with_tracking
            }
            self.email_storage[email_id] = email_data
            
            return ColdEmailResponse(
                email_id=email_id,
                subject=subject,
                body=body_with_tracking,
                value_propositions=value_propositions,
                tone_analysis=tone_analysis,
                tracking_pixel_url=tracking_pixel_url
            )
            
        except Exception as e:
            logger.error(f"Error generating cold email: {str(e)}")
            raise
    
    async def _analyze_company_tone(self, company_text: str, desired_tone: str) -> str:
        """Analyze and match company communication tone"""
        prompt = f"""
        Analyze the following company website content and provide insights on their communication tone.
        Then explain how to adapt a {desired_tone} tone to match their style.
        
        Company content:
        {company_text[:1000]}
        
        Provide a brief analysis (2-3 sentences) of:
        1. The company's communication style
        2. Key phrases or language patterns they use
        3. How to adapt the {desired_tone} tone to align with their style
        """
        
        # Use fast model for tone analysis
        analysis = await self.fast_llm_client.generate(prompt, temperature=0.3, max_tokens=200)
        return analysis
    
    async def _synthesize_value_propositions(
        self,
        resume_text: str,
        company_text: str,
        pain_point: Optional[str],
        sender_linkedin_text: Optional[str] = None,
        job_posting_content: Optional[str] = None
    ) -> List[str]:
        """Generate value propositions connecting skills to company needs"""
        prompt = f"""
        Act as a TOP TALENT ACQUISITION EXPERT using proven cold email strategies.
        Generate 3 ULTRA-SPECIFIC value propositions that make the candidate STAND OUT.
        
        CRITICAL: These aren't generic benefits. They're SPECIFIC MATCHES between candidate and company.
        
        Each value proposition MUST:
        - Include NUMBERS or SPECIFICS (e.g., "reduced costs by 40%" not "reduced costs")
        - Address a CURRENT pain point the company likely has
        - Show UNIQUE experience that 90% of candidates DON'T have
        - Use the company's own language/terminology (from their website/posting)
        
        {"Pain Point to address: " + pain_point if pain_point else ""}
        
        Resume:
        {resume_text[:1500]}
        
        Company Description:
        {company_text[:1500]}
        
        {f"Sender's LinkedIn Profile:\n{sender_linkedin_text[:500]}\n\nUse this to strengthen the value propositions by highlighting the sender's professional credibility, achievements, and expertise." if sender_linkedin_text else ""}
        
        {f"Job Posting Requirements:\n{job_posting_content[:1000]}\n\nIMPORTANT: Directly address the specific requirements, skills, and qualifications mentioned in this job posting. Match the candidate's experience to each requirement." if job_posting_content else ""}
        
        Return a JSON array of 3 value proposition strings.
        """
        
        result = await self.llm_client.generate_json(prompt, temperature=0.7)
        
        # Extract propositions from response
        if isinstance(result, dict):
            propositions = result.get("propositions", []) or result.get("value_propositions", [])
        elif isinstance(result, list):
            propositions = result
        else:
            propositions = [
                "Bring valuable experience and skills to your team",
                "Help achieve your business objectives more efficiently",
                "Contribute to your company's continued growth and success"
            ]
        
        return propositions[:3]  # Ensure we return exactly 3
    
    async def analyze_job_posting(self, job_posting_text: str) -> Dict[str, Any]:
        """Analyze job posting to extract key requirements and qualifications"""
        prompt = f"""
        Analyze this job posting and extract the following information:
        
        Job Posting:
        {job_posting_text[:2000]}
        
        Extract and return as JSON:
        {{
            "role_title": "exact job title",
            "key_responsibilities": ["list of main responsibilities"],
            "required_skills": ["list of required technical and soft skills"],
            "qualifications": ["list of required qualifications/experience"],
            "nice_to_have": ["list of preferred but not required skills"],
            "company_culture": "brief description of company culture if mentioned",
            "key_technologies": ["specific technologies, tools, or platforms mentioned"],
            "experience_level": "junior/mid/senior/lead",
            "important_keywords": ["important terms to use in application"]
        }}
        """
        
        result = await self.llm_client.generate_json(prompt, temperature=0.3)
        
        # Ensure we have a valid structure
        if not isinstance(result, dict):
            result = {
                "role_title": "Position",
                "key_responsibilities": [],
                "required_skills": [],
                "qualifications": [],
                "nice_to_have": [],
                "company_culture": "",
                "key_technologies": [],
                "experience_level": "mid",
                "important_keywords": []
            }
        
        return result
    
    async def _generate_subject(
        self,
        recipient_name: str,
        recipient_role: str,
        value_prop: str,
        email_goal: str
    ) -> str:
        """Generate compelling email subject line using Josh Braun's strategies"""
        prompt = f"""
        Generate a compelling email subject line using PROVEN cold email strategies from Josh Braun.
        
        Recipient: {recipient_name} ({recipient_role})
        Email Goal: {email_goal}
        Key Value: {value_prop}
        
        PROVEN SUBJECT LINE STRATEGIES (Pick ONE that fits best):
        
        1. **One-word question**: E.g., "Interested?" "Thoughts?" "Priority?"
        2. **Pattern interrupt**: Something unexpected like "Wrong person?" or "Quick question about [specific thing]"
        3. **Specific reference**: "Re: Your [specific project/post/initiative]"
        4. **Mutual connection**: "[Name] suggested I reach out"
        5. **Value tease**: "3 ways to [specific benefit]"
        6. **Problem/solution hint**: "Noticed [specific issue] at [company]"
        7. **Time-sensitive**: "Quick question before [specific date/event]"
        
        RULES:
        - 30-50 characters MAX (shorter is better)
        - NO generic phrases like "Job Opportunity" or "Great Opportunity"
        - Create curiosity without revealing everything
        - Avoid ALL CAPS or excessive punctuation
        - Make it feel like a colleague writing, not a marketer
        
        Return only the subject line, nothing else.
        """
        
        # Use fast model for subject generation
        subject = await self.fast_llm_client.generate(prompt, temperature=0.8, max_tokens=50)
        return subject.strip()
    
    async def _generate_email_body(
        self,
        request: ColdEmailRequest,
        company_text: str,
        tone_analysis: str,
        value_propositions: List[str],
        sender_linkedin_text: Optional[str] = None,
        job_posting_content: Optional[str] = None
    ) -> str:
        """Generate the main email body"""
        linkedin_context = ""
        if sender_linkedin_text:
            linkedin_context = f"""
        
        Sender's LinkedIn Profile (for credibility):
        {sender_linkedin_text[:500]}
        
        Use this information to:
        - Establish sender's credibility and expertise
        - Reference relevant achievements or experience
        - Build trust through professional background
        - Mention mutual connections or shared interests if any
        """
        
        job_posting_context = ""
        if job_posting_content:
            job_posting_context = f"""
        
        Job Posting Details:
        {job_posting_content[:1500]}
        
        CRITICAL: Tailor the email specifically to this job posting by:
        - Directly addressing the key requirements and qualifications
        - Mentioning specific skills or technologies from the posting
        - Showing how your experience matches their exact needs
        - Using similar language and terminology from the posting
        - Demonstrating understanding of the role's responsibilities
        """
        
        prompt = f"""
        Write a HIGH-CONVERTING cold email using the PROVEN 4T Template (Josh Braun methodology) and talent acquisition best practices.
        
        Recipient: {request.recipient_name}, {request.recipient_role}
        Sender: {request.sender_name}
        Email Goal: {request.email_goal}
        Tone: {request.company_tone} (adapted based on: {tone_analysis})
        
        Value Propositions:
        1. {value_propositions[0] if len(value_propositions) > 0 else ""}
        2. {value_propositions[1] if len(value_propositions) > 1 else ""}
        3. {value_propositions[2] if len(value_propositions) > 2 else ""}
        
        Company Context:
        {company_text[:800]}
        {linkedin_context}
        {job_posting_context}
        
        THE 4T STRUCTURE (MUST FOLLOW):
        
        1. **TRIGGER** (1-2 sentences): 
           - Reference a SPECIFIC recent event, achievement, or observation
           - Examples: "Saw your team just raised Series B" or "Noticed you're hiring 10 engineers this quarter"
           - Make it timely and relevant to THEM, not you
           
        2. **TEASE** (1 sentence):
           - Hint at value without giving everything away
           - Create curiosity: "which reminded me of how [similar company] solved [specific problem]"
           - Don't explain HOW yet, just WHAT
           
        3. **TRUST** (1 sentence):
           - Ultra-brief credibility builder
           - Pattern: "I've helped [similar companies] achieve [specific result]"
           - Include numbers if possible
           - {f"MUST reference: {job_posting_content[:200]}" if job_posting_content else ""}
           
        4. **TASK** (1 sentence):
           - ONE clear, low-commitment CTA
           - Use these proven CTAs:
             • "Mind if I send you [specific resource]?"
             • "Worth a 5-minute conversation?"
             • "Interested in seeing how [similar company] did it?"
             • "Open to learning more?"
             • "Would you like me to share [specific thing]?"
        
        CRITICAL RULES:
        - **100 words MAXIMUM** (shorter = better)
        - **3-5 sentences total**
        - Write like you're texting a colleague, not writing a formal letter
        - NO buzzwords, NO fluff, NO "I hope this finds you well"
        - One idea per sentence
        - Mobile-optimized (assume read on phone)
        - Include a P.S. line with additional value or social proof
        
        PSYCHOLOGICAL TRIGGERS TO USE:
        - Pattern interrupt in opening
        - Social proof (mention similar companies)
        - Scarcity (if genuine)
        - Specificity over generality
        
        Remember: You have 3 seconds to grab attention. Make them count.
        """
        
        body = await self.llm_client.generate(prompt, temperature=0.7)
        return body
    
    def _add_tracking_pixel(self, body: str, tracking_url: str) -> str:
        """Add invisible tracking pixel to email body"""
        # For HTML emails
        if "<html>" in body.lower() or "<body>" in body.lower():
            # Add before closing body tag
            tracking_html = f'<img src="{tracking_url}" width="1" height="1" style="display:none;" alt="" />'
            if "</body>" in body.lower():
                body = body.replace("</body>", f"{tracking_html}</body>")
            else:
                body += tracking_html
        else:
            # For plain text, convert to basic HTML and add pixel
            body_html = body.replace("\n", "<br>")
            body = f"""
            <html>
            <body>
            {body_html}
            <img src="{tracking_url}" width="1" height="1" style="display:none;" alt="" />
            </body>
            </html>
            """
        
        return body
    
    async def parse_resume(self, file_content: bytes, filename: str) -> ResumeParsingResult:
        """
        Parse resume from PDF or DOCX file
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            ResumeParsingResult with extracted text
        """
        try:
            text_content = ""
            
            if filename.lower().endswith('.pdf'):
                # Parse PDF
                text_content = self._parse_pdf(file_content)
            elif filename.lower().endswith(('.docx', '.doc')):
                # Parse Word document
                text_content = self._parse_docx(file_content)
            else:
                return ResumeParsingResult(
                    success=False,
                    error_message="Unsupported file format"
                )
            
            # Extract skills and experience
            skills = self._extract_skills(text_content)
            experience_years = self._extract_experience_years(text_content)
            
            return ResumeParsingResult(
                success=True,
                text_content=text_content,
                skills=skills,
                experience_years=experience_years
            )
            
        except Exception as e:
            logger.error(f"Error parsing resume: {str(e)}")
            return ResumeParsingResult(
                success=False,
                error_message=str(e)
            )
    
    def _parse_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            raise
        
        return text
    
    def _parse_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        text = ""
        try:
            doc_file = io.BytesIO(file_content)
            doc = docx.Document(doc_file)
            
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            logger.error(f"Error parsing DOCX: {str(e)}")
            raise
        
        return text
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from resume text"""
        # Common technical skills to look for
        skill_keywords = [
            'python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker',
            'kubernetes', 'git', 'agile', 'scrum', 'machine learning', 'data analysis',
            'project management', 'leadership', 'communication', 'problem solving'
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in skill_keywords:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        # Also look for skills section
        skills_pattern = r'(?:skills|expertise|competencies)[\s:]*([^\n]+(?:\n[^\n]+)*)'
        skills_match = re.search(skills_pattern, text, re.IGNORECASE)
        
        if skills_match:
            skills_text = skills_match.group(1)
            # Split by common delimiters
            additional_skills = re.split(r'[,;|•·]', skills_text)
            for skill in additional_skills:
                skill = skill.strip()
                if skill and len(skill) < 30:  # Reasonable skill length
                    found_skills.append(skill)
        
        # Remove duplicates and return
        return list(set(found_skills))[:10]  # Limit to 10 skills
    
    def _extract_experience_years(self, text: str) -> Optional[int]:
        """Extract years of experience from resume text"""
        # Look for patterns like "X years of experience"
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'experience[:\s]+(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*in\s*'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    years = int(match.group(1))
                    return years
                except:
                    continue
        
        # Try to calculate from work history dates
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, text)
        
        if len(years) >= 2:
            try:
                years_int = [int(f"{y}{rest}") for y, rest in re.findall(r'(19|20)(\d{2})', text)]
                if years_int:
                    experience = max(years_int) - min(years_int)
                    if 0 < experience < 50:  # Reasonable range
                        return experience
            except:
                pass
        
        return None
    
    async def record_email_open(self, email_id: str, timestamp: datetime):
        """Record an email open event"""
        event = EmailTrackingEvent(
            email_id=email_id,
            event_type="open",
            timestamp=timestamp
        )
        
        # In production, store in database
        self.tracking_events.append(event.dict())
        logger.info(f"Recorded email open for {email_id} at {timestamp}")
    
    async def get_email_stats(self, email_id: str) -> Dict[str, Any]:
        """Get tracking statistics for an email"""
        # In production, query from database
        opens = [e for e in self.tracking_events 
                if e.get("email_id") == email_id and e.get("event_type") == "open"]
        
        return {
            "email_id": email_id,
            "total_opens": len(opens),
            "first_open": opens[0]["timestamp"] if opens else None,
            "last_open": opens[-1]["timestamp"] if opens else None,
            "open_times": [e["timestamp"] for e in opens]
        }