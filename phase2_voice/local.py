"""Explicit deferred fallback interface. No implicit downloads or paid APIs."""

from typing import Protocol

from .schema import VoiceError


class LocalVoiceEngine(Protocol):
    def render(self, voice_input: dict) -> bytes:
        """Return native PCM WAV using a preinstalled, licensed, reviewed voice."""


class DeferredLocalEngine:
    def render(self, voice_input: dict) -> bytes:
        raise VoiceError("LOCAL_FALLBACK_NOT_CONFIGURED")
