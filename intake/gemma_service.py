"""
MediScribe — Gemma 4 Service Configuration.

This module manages the Google GenAI SDK connection to Gemma 4 models
via the Gemini API.

Important:
- Target model: Gemma 4 (e.g., gemma-4-31b-it, gemma-4-26b-a4b-it).
- Gemma is Google's open model family, accessed via the Gemini API and the google-genai SDK.
- Do not substitute Gemini (e.g., gemini-1.5, gemini-2.0, gemini-2.5) for Gemma.
- A real API key is NOT required just to start the application.
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)

SUPPORTED_GEMMA_MODELS = (
    'gemma-4-31b-it',
    'gemma-4-26b-a4b-it',
    'gemma-4-12b-it',
    'gemma-4-e4b-it',
    'gemma-4-e2b-it',
)


class GemmaConfigurationError(Exception):
    """Raised when Gemma 4 is invoked without proper configuration."""
    pass


def get_gemma_model_name() -> str:
    """Return the configured Gemma 4 model name."""
    model_name = getattr(settings, 'GEMMA_MODEL', 'gemma-4-31b-it')
    return model_name.strip() if model_name else 'gemma-4-31b-it'


def validate_gemma_model(model_name: str) -> bool:
    """
    Validate that the configured model is a Gemma model and not Gemini.
    Returns True if valid Gemma model name, False if a Gemini model is mistakenly used.
    """
    cleaned = model_name.strip().lower()
    if cleaned.startswith('gemini-'):
        return False
    return 'gemma' in cleaned


def is_gemma_configured() -> bool:
    """Check if the Gemini API key for Gemma 4 access is configured."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    return bool(api_key and api_key.strip())


def get_gemma_client(raise_on_missing: bool = False):
    """
    Return an initialized google.genai.Client instance if configured.
    If not configured:
      - Returns None by default (safe for server startup and checks).
      - Raises GemmaConfigurationError if raise_on_missing is True.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '').strip()
    if not api_key:
        if raise_on_missing:
            raise GemmaConfigurationError(
                "GEMINI_API_KEY is not set. Please configure GEMINI_API_KEY in your .env "
                "or environment variables to enable Gemma 4 processing."
            )
        return None

    model_name = get_gemma_model_name()
    if not validate_gemma_model(model_name):
        raise GemmaConfigurationError(
            f"Invalid model configured: '{model_name}'. MediScribe requires a Gemma 4 model "
            f"(e.g., 'gemma-4-31b-it'). Do not substitute Gemini models."
        )

    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as exc:
        logger.error("Failed to initialize google-genai client: %s", exc)
        if raise_on_missing:
            raise
        return None


def get_gemma_status() -> dict:
    """
    Return a summary of Gemma 4 configuration status.
    Never exposes raw API keys.
    """
    configured = is_gemma_configured()
    model = get_gemma_model_name()
    model_valid = validate_gemma_model(model)

    if not model_valid:
        status = "Invalid model: Gemma model required, Gemini detected"
    elif configured:
        status = "Configured and ready"
    else:
        status = "Awaiting API key (set GEMINI_API_KEY in .env)"

    return {
        "configured": configured,
        "model": model,
        "is_gemma": model_valid,
        "provider": "Google Gemini API (google-genai SDK)",
        "status": status,
    }
