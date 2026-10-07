"""Core scam analysis package for Amanak."""

from .analyzer import analyze
from .models import AnalysisResult

__all__ = ["analyze", "AnalysisResult"]
