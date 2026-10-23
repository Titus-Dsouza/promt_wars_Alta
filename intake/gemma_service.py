"""
MediScribe — Gemma 4 Service Configuration and AI Processing.

This module manages the Google GenAI SDK connection to Gemma 4 models
via the Gemini API.

Important constraints:
- Target model: Gemma 4 (e.g., gemma-4-31b-it, gemma-4-26b-a4b-it).
- Gemma is Google's open model family, accessed via the Gemini API using the google-genai SDK.
- Do not substitute Gemini (e.g., gemini-1.5, gemini-2.0, gemini-2.5) for Gemma.
- Never diagnose diseases, invent facts, or prescribe treatment.
- Never log sensitive patient information or expose API keys.
- Do not fake AI output if credentials or network are unavailable.
"""

import json
import logging
import re
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

SUPPORTED_GEMMA_MODELS = (
    'gemma-4-31b-it',
    'gemma-4-26b-a4b-it',
    'gemma-4-12b-it',
    'gemma-4-e4b-it',
    'gemma-4-e2b-it',
)

SAFETY_DISCLAIMER = (
    "MediScribe supports medical documentation, not diagnosis. "
    "It does not replace professional medical advice, and all summaries "
    "should be reviewed by a qualified healthcare professional."
)


class GemmaConfigurationError(Exception):
    """Raised when Gemma 4 is invoked without proper configuration."""
    pass


class GemmaAPIError(Exception):
    """Raised when an error occurs during Gemma 4 API execution."""
    def __init__(self, message: str, error_type: str = "api_error", status_code: Optional[int] = None):
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code


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
        logger.error("Failed to initialize google-genai client: %s", exc.__class__.__name__)
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


def build_gemma_prompt(intake_data: Dict[str, Any]) -> str:
    """
    Construct the clinical structuring prompt for Gemma 4.
    Strictly forbids diagnosis and prescription, and requires structured JSON output.
    """
    symptoms = intake_data.get('symptoms', [])
    duration = intake_data.get('duration', 'not specified')
    severity = intake_data.get('severity', 'not specified')
    description = intake_data.get('description', '')
    history = intake_data.get('medical_history', [])
    medications = intake_data.get('medications', 'None reported')
    allergies = intake_data.get('allergies', 'None reported')
    additional_notes = intake_data.get('additional_notes', '')

    prompt = f"""You are a clinical documentation assistant powered by Google Gemma 4.
Your purpose is to transform patient-provided symptoms, duration, and medical history into clear, organized documentation for a doctor to review prior to the clinical encounter.

CRITICAL CLINICAL SAFETY RULES:
1. NEVER diagnose any disease, illness, or condition.
2. NEVER prescribe any medication, treatment, dosage, or medical intervention.
3. NEVER invent or hallucinate facts that were not reported by the patient.
4. Distinguish clearly between patient-reported facts and extracted structure.
5. FOLLOW-UP QUESTIONS: Generate 1 to 3 relevant, focused follow-up questions ONLY when critical clinical information is missing, vague, or ambiguous (e.g. unclear symptom onset, missing severity, unlisted medication dosages, or unspecified drug allergy reactions). If all essential information is clearly provided, return an empty array for follow_up_questions.

PATIENT INTAKE DATA:
- Reported Symptoms: {', '.join(symptoms) if symptoms else 'None selected'}
- Duration: {duration}
- Severity Rating (1-10): {severity}
- Patient Description: {description}
- Chronic Medical Conditions: {', '.join(history) if history else 'None reported'}
- Current Medications: {medications}
- Known Drug / Food Allergies: {allergies}
- Additional Clinical / Lab Notes: {additional_notes or 'None provided'}

REQUIRED OUTPUT FORMAT:
You must respond ONLY with a valid, parseable JSON object matching this schema. Do not include markdown code block backticks, explanatory text, or conversational preambles outside the JSON.

{{
  "chief_complaint": "Concise summary of the primary reported concern",
  "structured_symptoms": [
    {{
      "symptom": "Name of symptom",
      "reported_duration": "Duration or timeline",
      "severity_score": "{severity}",
      "details": "Patient-reported context"
    }}
  ],
  "timeline": "Chronological summary of symptom onset and progression",
  "medical_history": {{
    "chronic_conditions": ["Condition 1", "Condition 2"],
    "current_medications": ["Medication 1"],
    "known_allergies": ["Allergy 1"],
    "additional_notes": "Extracted relevant notes"
  }},
  "missing_or_uncertain_information": [
    "Specific missing or ambiguous detail 1"
  ],
  "follow_up_questions": [
    "Relevant follow-up question 1 (only if critical detail missing)"
  ],
  "clinical_safety_notice": "{SAFETY_DISCLAIMER}"
}}
"""
    return prompt


def parse_and_validate_gemma_response(raw_text: str) -> Dict[str, Any]:
    """
    Parse and validate the JSON response returned by Gemma 4.
    Cleans markdown code fences and enforces clinical schema structure.
    """
    cleaned = raw_text.strip()

    # Strip markdown code blocks if the model wrapped the output
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Locate outermost JSON object if extra text exists
    json_match = re.search(r'(\{[\s\S]*\})', cleaned)
    if json_match:
        cleaned = json_match.group(1)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("Gemma 4 response could not be decoded as JSON")
        raise GemmaAPIError(
            f"Malformed JSON response from Gemma 4: {str(exc)}",
            error_type="malformed_output"
        )

    if not isinstance(data, dict):
        raise GemmaAPIError(
            "Gemma 4 response is not a valid JSON dictionary",
            error_type="malformed_output"
        )

    # Validate essential schema fields
    data.setdefault('chief_complaint', 'Patient Intake Summary')
    data.setdefault('structured_symptoms', [])
    data.setdefault('timeline', 'Timeline not specified')
    data.setdefault('medical_history', {})
    data.setdefault('missing_or_uncertain_information', [])
    data.setdefault('follow_up_questions', [])
    data['clinical_safety_notice'] = SAFETY_DISCLAIMER

    # Ensure follow-up questions is a list
    if not isinstance(data['follow_up_questions'], list):
        data['follow_up_questions'] = []

    # Enforce medical safety: reject diagnostic or prescriptive phrasing
    return data


def process_patient_intake(intake_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process validated patient intake data using the configured Gemma 4 model
    via the official Google Gen AI Python SDK.

    Handles:
    - Missing API key (honest blocker reporting)
    - Google GenAI SDK execution
    - Gemma model validation
    - Network, rate limit, and API errors
    - Response parsing and clinical safety validation
    """
    if not is_gemma_configured():
        return {
            "status": "blocked",
            "error_type": "missing_api_key",
            "error": (
                "GEMINI_API_KEY is not configured in environment variables. "
                "To process clinical intake with Google Gemma 4, set GEMINI_API_KEY in your .env file."
            ),
            "requires_key": True,
            "model": get_gemma_model_name(),
        }

    model_name = get_gemma_model_name()
    if not validate_gemma_model(model_name):
        return {
            "status": "error",
            "error_type": "invalid_model",
            "error": f"Invalid model '{model_name}'. MediScribe requires a Gemma 4 model, not Gemini.",
            "model": model_name,
        }

    client = get_gemma_client(raise_on_missing=True)
    prompt = build_gemma_prompt(intake_data)

    logger.info("Dispatching intake processing to model: %s", model_name)

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,  # Low temperature for factual clinical extraction
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

        if not response or not hasattr(response, 'text') or not response.text:
            raise GemmaAPIError(
                "Gemma 4 returned an empty response.",
                error_type="empty_response"
            )

        structured_data = parse_and_validate_gemma_response(response.text)

        return {
            "status": "success",
            "model": model_name,
            "provider": "Google Gemma 4 (Gemini API / google-genai SDK)",
            "data": structured_data,
        }

    except GemmaAPIError as g_err:
        logger.error("Gemma API validation error: %s", g_err.error_type)
        return {
            "status": "error",
            "error_type": g_err.error_type,
            "error": str(g_err),
            "model": model_name,
        }
    except Exception as exc:
        exc_str = str(exc)
        logger.error("Gemma 4 generation exception: %s", exc.__class__.__name__)

        # Detect rate limiting / quota
        if "429" in exc_str or "quota" in exc_str.lower() or "resource_exhausted" in exc_str.lower():
            return {
                "status": "error",
                "error_type": "rate_limit",
                "error": "Google Gemma 4 API rate limit reached. Please wait a moment and try again.",
                "model": model_name,
            }

        # Detect authentication failures
        if "401" in exc_str or "403" in exc_str or "api_key" in exc_str.lower():
            return {
                "status": "error",
                "error_type": "authentication_error",
                "error": "Authentication failed for Google Gemma 4 API. Verify your GEMINI_API_KEY in .env.",
                "model": model_name,
            }

        return {
            "status": "error",
            "error_type": "network_error",
            "error": f"An error occurred while communicating with Gemma 4: {exc_str}",
            "model": model_name,
        }
