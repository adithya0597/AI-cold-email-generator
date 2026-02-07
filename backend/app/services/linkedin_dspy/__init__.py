"""
DSPy-based LinkedIn post generation pipeline.

Provides structured, optimized LinkedIn post generation using DSPy modules
with engagement scoring, hook optimization, and influencer style adaptation.
"""

from .service import LinkedInDSPyService
from .modules import LinkedInPostModule

__all__ = ["LinkedInDSPyService", "LinkedInPostModule"]
