from __future__ import annotations

import os
from typing import Any


class VoiceTranscriber:
    """Simple interface for voice transcription providers."""

    def __init__(self, provider: str | None = None):
        self.provider = provider or os.getenv("VOICE_PROVIDER", "none")

    def transcribe(self, audio_path: str) -> str:
        if self.provider == "none":
            return ""
        if self.provider == "openai":
            return ""  # Optional provider integration can be added later.
        return ""


def transcribe_audio(audio_path: str, provider: str | None = None) -> str:
    return VoiceTranscriber(provider).transcribe(audio_path)


__all__ = ["VoiceTranscriber", "transcribe_audio"]
