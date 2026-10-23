"""Gemini 3.8 Flash integration and source-grounded patient report generation."""

import json
import logging
import re
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

MODEL_ID_PATTERN = re.compile(r"^gemini-[a-z0-9][a-z0-9.-]*$")
UNSAFE_QUESTION_PATTERN = re.compile(
    r"\b(?:should take|start taking|stop taking|take \d|prescrib(?:e|ing)|"
    r"diagnosed with|you may have|you might have|likely have)\b",
    re.IGNORECASE,
)
SAFETY_DISCLAIMER = (
    "MediScribe supports medical documentation, not diagnosis. It does not replace "
    "professional medical advice. A qualified healthcare professional must review "
    "this patient-reported information before clinical use."
)


class ModelConfigurationError(Exception):
    """Raised when Gemini API configuration is missing or invalid."""


class ModelAPIError(Exception):
    """A safe, user-facing model error without raw provider details."""

    def __init__(self, message: str, error_type: str = "api_error"):
        super().__init__(message)
        self.error_type = error_type


def get_model_name() -> str:
    """Return the configurable Gemini model ID."""
    return (getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash") or "gemini-3.8-flash").strip()


def validate_model_name(model_name: str) -> bool:
    """Check that a model ID is a syntactically valid Gemini model ID."""
    return bool(MODEL_ID_PATTERN.fullmatch((model_name or "").strip().lower()))


def is_gemini_configured() -> bool:
    return bool((getattr(settings, "GEMINI_API_KEY", "") or "").strip())


def get_gemini_client(raise_on_missing: bool = False):
    """Create the official Google Gen AI SDK client, with a bounded request timeout."""
    api_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
    if not api_key:
        if raise_on_missing:
            raise ModelConfigurationError("GEMINI_API_KEY is not configured.")
        return None

    try:
        from google import genai
        from google.genai import types

        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=45_000),
        )
    except Exception as exc:
        logger.error("Google Gen AI client initialization failed: %s", type(exc).__name__)
        if raise_on_missing:
            raise ModelConfigurationError("Google Gen AI client initialization failed.") from None
        return None


def get_model_status() -> dict[str, Any]:
    configured = is_gemini_configured()
    model = get_model_name()
    valid = validate_model_name(model)
    if not valid:
        status = "Invalid Gemini model ID"
    elif configured:
        status = "Credentials configured; account access is checked during generation"
    else:
        status = "Awaiting API key (set GEMINI_API_KEY)"
    return {
        "configured": configured,
        "model": model,
        "is_gemini": valid,
        "provider": "Google Gemini API (google-genai SDK)",
        "status": status,
    }


def build_gemini_prompt(intake_data: dict[str, Any]) -> str:
    """Ask Gemini for structure and review prompts, never clinical conclusions."""
    return f"""You are a clinical documentation organizer. Do not diagnose, prescribe, recommend treatment, or create facts.
Return only valid JSON matching the requested fields. Use only the patient data below. Do not resolve contradictions; flag them for clinician review. Every conflicting_information item must include two exact patient excerpts in quotation marks, copied from the input. If a value is absent, say so in missing_or_uncertain_information rather than guessing.

Patient-entered intake JSON:
{json.dumps(intake_data, ensure_ascii=False)}

Required JSON object:
{{
  "chief_complaint": "Brief organization of the patient's own concern, without adding facts",
  "structured_symptoms": [{{"symptom":"", "reported_duration":"", "severity_score":"", "details":""}}],
  "timeline": "Only the patient's stated timing, or an explicit missing marker",
  "medical_history": {{"chronic_conditions":[], "current_medications":[], "known_allergies":[], "additional_notes":""}},
  "conflicting_information": [],
  "missing_or_uncertain_information": [],
  "follow_up_questions": []
}}
Every follow_up_questions entry must be a neutral question ending in a question mark. The application independently grounds all report facts in the submitted intake; your narrative fact fields will not be trusted as patient facts.
"""


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ModelAPIError(f"Gemini returned an invalid {field} field.", "malformed_output")
    return value


def parse_and_validate_gemini_response(raw_text: str) -> dict[str, Any]:
    """Require a complete schema; never fill missing report fields with invented defaults."""
    cleaned = (raw_text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE).strip()
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        raise ModelAPIError("Gemini returned an unreadable response. Please retry.", "malformed_output") from None

    required = {
        "chief_complaint", "structured_symptoms", "timeline", "medical_history",
        "conflicting_information", "missing_or_uncertain_information", "follow_up_questions",
    }
    if not isinstance(data, dict) or not required.issubset(data):
        raise ModelAPIError("Gemini returned an incomplete report. Please retry.", "malformed_output")

    _require_text(data["chief_complaint"], "summary")
    _require_text(data["timeline"], "timeline")
    if not isinstance(data["structured_symptoms"], list) or any(not isinstance(item, dict) for item in data["structured_symptoms"]):
        raise ModelAPIError("Gemini returned invalid symptom details. Please retry.", "malformed_output")
    for symptom in data["structured_symptoms"]:
        for key in ("symptom", "reported_duration", "severity_score", "details"):
            if key not in symptom or not isinstance(symptom[key], (str, int, float)):
                raise ModelAPIError("Gemini returned incomplete symptom details. Please retry.", "malformed_output")

    history = data["medical_history"]
    if not isinstance(history, dict):
        raise ModelAPIError("Gemini returned invalid medical history. Please retry.", "malformed_output")
    for key in ("chronic_conditions", "current_medications", "known_allergies"):
        value = history.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ModelAPIError("Gemini returned invalid medical history. Please retry.", "malformed_output")
    _require_text(history.get("additional_notes"), "medical notes")

    for key in ("conflicting_information", "missing_or_uncertain_information", "follow_up_questions"):
        value = data[key]
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ModelAPIError("Gemini returned an invalid review list. Please retry.", "malformed_output")
    if any(not question.rstrip().endswith("?") for question in data["follow_up_questions"]):
        raise ModelAPIError("Gemini returned an invalid follow-up question. Please retry.", "malformed_output")
    if any(UNSAFE_QUESTION_PATTERN.search(question) for question in data["follow_up_questions"]):
        raise ModelAPIError("Gemini returned a potentially unsafe clinical suggestion. Please retry.", "unsafe_output")

    data["clinical_safety_notice"] = SAFETY_DISCLAIMER
    return data


def _source_grounded_report(model_data: dict[str, Any], intake: dict[str, Any]) -> dict[str, Any]:
    """Build every factual report field from submitted values, not model-generated claims."""
    symptoms = [value.strip() for value in intake.get("symptoms", []) if isinstance(value, str) and value.strip()]
    description = intake.get("description", "").strip()
    duration = intake.get("duration", "").strip()
    severity = intake.get("severity", "")
    conditions = [value.strip() for value in intake.get("medical_history", []) if isinstance(value, str) and value.strip()]
    medications = intake.get("medications", "").strip()
    allergies = intake.get("allergies", "").strip()
    notes = intake.get("additional_notes", "").strip()

    structured = [{
        "symptom": symptom,
        "reported_duration": duration or "Not specified by patient",
        "severity_score": str(severity) if severity != "" else "Not rated by patient",
        "details": description,
    } for symptom in symptoms]
    source_text = " ".join([
        *symptoms, duration, str(severity), description, *conditions, medications, allergies, notes,
    ])
    normalized_source = " ".join(source_text.casefold().split())
    grounded_conflicts = []
    for conflict in model_data["conflicting_information"]:
        excerpts = re.findall(r'["“](.+?)["”]', conflict)
        if len(excerpts) >= 2 and all(" ".join(excerpt.casefold().split()) in normalized_source for excerpt in excerpts[:2]):
            grounded_conflicts.append(conflict)

    # Model observations are suggestions, never assertions about patient facts.
    missing = [f"AI-suggested for confirmation: {item}" for item in model_data["missing_or_uncertain_information"]]
    if not duration:
        missing.append("Symptom duration was not provided.")
    if not description:
        missing.append("A symptom description was not provided.")
    if not medications:
        missing.append("Medication information was not provided.")
    if not allergies:
        missing.append("Allergy information was not provided.")

    return {
        "chief_complaint": "; ".join(symptoms) if symptoms else "No symptoms selected",
        "structured_symptoms": structured,
        "timeline": f"Patient-selected duration: {duration or 'Not specified'}. Patient description: {description or 'Not provided.'}",
        "medical_history": {
            "chronic_conditions": conditions,
            "current_medications": [medications] if medications else [],
            "known_allergies": [allergies] if allergies else [],
            "additional_notes": notes,
        },
        # Keep model-flagged potential contradictions explicitly subject to review.
        "conflicting_information": grounded_conflicts,
        "missing_or_uncertain_information": list(dict.fromkeys(missing)),
        "follow_up_questions": model_data["follow_up_questions"],
        "clinical_safety_notice": SAFETY_DISCLAIMER,
    }


def process_patient_intake(intake_data: dict[str, Any]) -> dict[str, Any]:
    """Call Gemini; return a report only after strict schema checks and source grounding."""
    model_name = get_model_name()
    if not is_gemini_configured():
        return {
            "status": "blocked", "error_type": "missing_api_key",
            "error": "GEMINI_API_KEY is not configured. No AI report was generated.",
            "requires_key": True, "model": model_name,
        }
    if not validate_model_name(model_name):
        return {
            "status": "error", "error_type": "invalid_model",
            "error": "GEMINI_MODEL must be a valid Gemini model ID.", "model": model_name,
        }

    try:
        client = get_gemini_client(raise_on_missing=True)
    except ModelConfigurationError:
        logger.error("Google Gen AI client configuration failed")
        return {
            "status": "error", "error_type": "configuration_error",
            "error": "Google Gen AI could not be initialized. Check server configuration and try again.",
            "model": model_name,
        }
    logger.info("Dispatching intake to configured Gemini model: %s", model_name)
    try:
        from google.genai import types
        response = client.models.generate_content(
            model=model_name,
            contents=build_gemini_prompt(intake_data),
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        if not response or not getattr(response, "text", None):
            raise ModelAPIError("Gemini returned an empty response. Please retry.", "empty_response")
        model_data = parse_and_validate_gemini_response(response.text)
        return {
            "status": "success", "model": model_name,
            "provider": "Google Gemini 3.8 Flash (Gemini API / google-genai SDK)",
            "data": _source_grounded_report(model_data, intake_data),
        }
    except ModelAPIError as exc:
        logger.warning("Gemini response rejected: %s", exc.error_type)
        return {"status": "error", "error_type": exc.error_type, "error": str(exc), "model": model_name}
    except Exception as exc:
        # Inspect only safe metadata; raw API errors can include request or credential data.
        code = getattr(exc, "code", None)
        name = type(exc).__name__.lower()
        if code == 429:
            error_type, message = "rate_limit", "Gemini is temporarily rate limited. Please wait and try again."
        elif code in (401, 403):
            error_type, message = "authentication_error", "Gemini authentication failed. Check the server API key and account access."
        elif code == 404:
            error_type, message = "model_unavailable", "The configured Gemini model is unavailable to this account. No report was generated."
        elif code == 400:
            error_type, message = "invalid_request", "Gemini rejected the request. Check the API key, model ID, and request configuration. No report was generated."
        elif "timeout" in name:
            error_type, message = "timeout", "Gemini did not respond before the request timed out. Please retry."
        elif isinstance(code, int) and 500 <= code <= 599:
            error_type, message = "provider_unavailable", "Google Gemini is temporarily unavailable. Your answers remain in this browser; please try again later."
        else:
            error_type, message = "network_error", "Gemini could not be reached. Your answers remain in this browser; please try again later."
        logger.error(
            "Gemini generation failed (category=%s, exception=%s, code=%s)",
            error_type,
            type(exc).__name__,
            code if isinstance(code, int) else "unknown",
        )
        return {"status": "error", "error_type": error_type, "error": message, "model": model_name}
