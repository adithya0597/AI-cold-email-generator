"""
LLM client abstraction for multiple providers
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
import httpx
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"  # For testing


class BaseLLMClient(ABC):
    """Base class for LLM clients"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate JSON response from prompt"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API client"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        
        if not self.api_key:
            logger.warning("OpenAI API key not found")
    
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Generate text using OpenAI API"""
        if not self.api_key:
            return self._fallback_response(prompt)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return self._fallback_response(prompt)
    
    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate JSON response using OpenAI API"""
        # Add JSON mode instruction
        json_prompt = f"{prompt}\n\nRespond with valid JSON only."
        
        response = await self.generate(json_prompt, **kwargs)
        
        try:
            # Try to parse JSON from response
            # Handle case where response might have markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {response}")
            return {}
    
    def _fallback_response(self, prompt: str) -> str:
        """Fallback response when API is unavailable"""
        return "Generated content (API key not configured)"


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = "https://api.anthropic.com/v1"
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        
        if not self.api_key:
            logger.warning("Anthropic API key not found")
    
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Generate text using Anthropic API"""
        if not self.api_key:
            return self._fallback_response(prompt)
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=data,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                return result["content"][0]["text"]
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            return self._fallback_response(prompt)
    
    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate JSON response using Anthropic API"""
        json_prompt = f"{prompt}\n\nRespond with valid JSON only."
        response = await self.generate(json_prompt, **kwargs)
        
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {response}")
            return {}
    
    def _fallback_response(self, prompt: str) -> str:
        """Fallback response when API is unavailable"""
        return "Generated content (API key not configured)"


class LocalLLMClient(BaseLLMClient):
    """Local/Mock LLM client for testing"""
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate mock response for testing"""
        if "cold email" in prompt.lower():
            return self._generate_mock_email()
        elif "linkedin" in prompt.lower():
            return self._generate_mock_post()
        elif "value proposition" in prompt.lower():
            return self._generate_mock_value_props()
        else:
            return "Mock generated content based on prompt"
    
    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate mock JSON response"""
        if "value proposition" in prompt.lower():
            return {
                "propositions": [
                    "Leverage my 5+ years of experience to streamline your development process",
                    "Apply proven methodologies to reduce time-to-market by 30%",
                    "Bridge the gap between technical implementation and business objectives"
                ]
            }
        return {"result": "Mock JSON response"}
    
    def _generate_mock_email(self) -> str:
        """Generate a mock cold email"""
        return """Subject: Enhancing Your Development Process at [Company]

Dear [Recipient],

I noticed your company's impressive growth in the tech sector and your recent expansion into cloud services. 

Having spent 5+ years optimizing development workflows for similar companies, I've consistently helped teams reduce deployment time by 40% while maintaining code quality.

Your recent blog post about scaling challenges resonated with me, particularly the part about maintaining velocity while growing the team. I've successfully addressed similar challenges using a combination of automated testing and progressive deployment strategies.

Would you be open to a brief 15-minute call next week to discuss how these approaches might benefit your team?

Best regards,
[Your Name]"""
    
    def _generate_mock_post(self) -> str:
        """Generate a mock LinkedIn post"""
        return """🚀 The Hidden Cost of Technical Debt Nobody Talks About

After working with 50+ startups, I've noticed a pattern:

Companies that invest 20% of their time in refactoring save 40% in the long run.

Here's what I learned:

→ Small, consistent improvements beat major overhauls
→ Document decisions, not just code
→ Involve the whole team in technical debt discussions

The best time to address technical debt? Before it becomes critical.

What's your approach to managing technical debt?

#TechLeadership #SoftwareEngineering #TechnicalDebt #StartupLessons"""
    
    def _generate_mock_value_props(self) -> str:
        """Generate mock value propositions"""
        return json.dumps([
            "Leverage my expertise to accelerate your development timeline",
            "Apply industry best practices to improve code quality",
            "Reduce operational costs through efficient architecture"
        ])


class LLMClient:
    """Main LLM client that manages multiple providers"""
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        # Determine provider from environment or parameter
        if provider:
            self.provider = provider
        else:
            # Check which API keys are available
            if os.getenv("OPENAI_API_KEY"):
                self.provider = LLMProvider.OPENAI
            elif os.getenv("ANTHROPIC_API_KEY"):
                self.provider = LLMProvider.ANTHROPIC
            else:
                logger.warning("No LLM API keys found, using local mock client")
                self.provider = LLMProvider.LOCAL
        
        # Initialize the appropriate client
        self.client = self._init_client()
    
    def _init_client(self) -> BaseLLMClient:
        """Initialize the appropriate LLM client"""
        if self.provider == LLMProvider.OPENAI:
            return OpenAIClient()
        elif self.provider == LLMProvider.ANTHROPIC:
            return AnthropicClient()
        else:
            return LocalLLMClient()
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        return await self.client.generate(prompt, **kwargs)
    
    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate JSON response from prompt"""
        return await self.client.generate_json(prompt, **kwargs)
    
    async def generate_with_examples(self, prompt: str, examples: List[Dict[str, str]], **kwargs) -> str:
        """Generate text with few-shot examples"""
        # Format examples into prompt
        examples_text = "\n\n".join([
            f"Example {i+1}:\nInput: {ex.get('input', '')}\nOutput: {ex.get('output', '')}"
            for i, ex in enumerate(examples)
        ])
        
        full_prompt = f"{examples_text}\n\nNow, based on these examples:\n{prompt}"
        
        return await self.generate(full_prompt, **kwargs)
    
    async def check_health(self) -> bool:
        """Check if LLM service is healthy"""
        try:
            response = await self.generate("Test prompt", max_tokens=10)
            return len(response) > 0
        except Exception:
            return False
    
    def switch_provider(self, provider: LLMProvider):
        """Switch to a different LLM provider"""
        self.provider = provider
        self.client = self._init_client()
        logger.info(f"Switched to {provider} provider")