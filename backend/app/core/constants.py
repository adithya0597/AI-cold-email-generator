"""
Constants and configuration values for the AI Content Generation Suite
"""

# API Configuration
DEFAULT_API_TIMEOUT = 30.0
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1.0

# Content Limits
MAX_EMAIL_LENGTH = 100  # words
MAX_POST_LENGTH = 200  # words
MAX_HASHTAGS = 10
MAX_REFERENCE_URLS = 3
MAX_URL_CONTENT_LENGTH = 1500  # characters per URL

# Image Generation
DEFAULT_IMAGE_SIZE = "1024x1024"
IMAGE_PLACEHOLDER_URL = "https://via.placeholder.com/1024x1024.png?text=LinkedIn+Post+Visual"
DALL_E_MODEL = "dall-e-2"

# Tracking Configuration
DEFAULT_TRACKING_BASE_URL = "http://localhost:8000/api/track"

# Monitoring Thresholds
ERROR_RATE_THRESHOLD = 0.1  # 10%
MAX_RESPONSE_TIME = 10.0  # seconds
CONSECUTIVE_FAILURE_LIMIT = 3

# Cache Settings
CACHE_TTL_SECONDS = 900  # 15 minutes

# LinkedIn Hashtag Settings
MIN_HASHTAG_RELEVANCE = 0.3
HASHTAG_LENGTH_LIMIT = 30

# Search Configuration
MAX_SEARCH_RESULTS = 5
SEARCH_TIMEOUT = 30.0

# File Processing
ALLOWED_RESUME_FORMATS = ('.pdf', '.docx', '.doc')
ALLOWED_EXCEL_FORMATS = ('.xlsx', '.xls')