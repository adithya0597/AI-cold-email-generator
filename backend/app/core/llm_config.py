"""
LLM Configuration for optimized performance
"""

import os

# Model selection based on task requirements
class LLMConfig:
    # Fast model for simple tasks (tone analysis, subject generation)
    FAST_MODEL = os.getenv("FAST_MODEL", "gpt-3.5-turbo")
    
    # Quality model for complex tasks (email body, value propositions)
    QUALITY_MODEL = os.getenv("QUALITY_MODEL", "gpt-4-turbo")
    
    # Use fast model for most tasks to reduce latency
    USE_FAST_MODEL_FOR_ANALYSIS = True
    
    # Reduced token limits for faster responses
    MAX_TOKENS_FAST = 300
    MAX_TOKENS_QUALITY = 500
    
    # Optimized temperatures
    TEMPERATURE_ANALYSIS = 0.3  # Lower for consistency
    TEMPERATURE_CREATIVE = 0.7  # Balanced for creativity
    
    # Timeout settings
    API_TIMEOUT = 30  # Reduced from 60
    
    @classmethod
    def get_model_for_task(cls, task_type: str) -> tuple[str, int]:
        """
        Get appropriate model and token limit for specific task
        
        Returns:
            tuple of (model_name, max_tokens)
        """
        fast_tasks = ["tone_analysis", "subject_generation", "hashtag_generation"]
        
        if task_type in fast_tasks:
            return cls.FAST_MODEL, cls.MAX_TOKENS_FAST
        else:
            return cls.QUALITY_MODEL, cls.MAX_TOKENS_QUALITY