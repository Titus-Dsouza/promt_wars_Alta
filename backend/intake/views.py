import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from .ai_service import get_model_status, process_patient_intake

logger = logging.getLogger(__name__)

ALLOWED_DURATIONS = {
    'under_24_hours',
    '2-3_days',
    '1-2_weeks',
    'over_a_month',
}


def intake_view(request):
    """
    Renders the primary patient intake interface.
    Supports desktop and mobile responsive layout, multiple-choice questions,
        free-text symptoms, interactive progress states, and Gemini 3.8 Flash processing.
    """
    context = {
        'model_name': getattr(settings, 'GEMINI_MODEL', 'gemini-3.8-flash'),
        'phase': 3,
    }
    return render(request, 'index.html', context)


@ensure_csrf_cookie
def csrf_token_view(request):
    """Issue a CSRF token to the optional localhost frontend dev server."""
    return JsonResponse({'csrfToken': get_token(request)})


def validate_intake_view(request):
    """
    Validates patient intake submission payload without triggering AI processing.
    Confirms form data validity and returns structured intake state.
    """
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'error': 'Only POST method is allowed.',
        }, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({
            'status': 'error',
            'error': 'Invalid JSON request payload.',
        }, status=400)

    if not isinstance(data, dict):
        return JsonResponse({'status': 'error', 'error': 'Request data must be a JSON object.'}, status=400)

    symptoms = data.get('symptoms', [])
    if not isinstance(symptoms, list) or len(symptoms) == 0 or any(not isinstance(item, str) for item in symptoms):
        return JsonResponse({
            'status': 'error',
            'error': 'At least one primary symptom must be selected.',
        }, status=400)

    duration_value = data.get('duration', '')
    if not isinstance(duration_value, str):
        return JsonResponse({'status': 'error', 'error': 'Duration must be text.'}, status=400)
    duration = duration_value.strip()
    if duration not in ALLOWED_DURATIONS:
        return JsonResponse({
            'status': 'error',
            'error': f'Invalid duration value. Allowed: {", ".join(sorted(ALLOWED_DURATIONS))}',
        }, status=400)

    description_value = data.get('description', '')
    if not isinstance(description_value, str) or len(description_value) > 5000:
        return JsonResponse({'status': 'error', 'error': 'Symptom description must be text under 5,000 characters.'}, status=400)
    description = description_value.strip()
    if len(description) < 10:
        return JsonResponse({
            'status': 'error',
            'error': 'Symptom description must contain at least 10 characters.',
        }, status=400)

    try:
        severity = int(data.get('severity', 5))
        severity = max(1, min(10, severity))
    except (TypeError, ValueError):
        severity = 5

    medical_history = data.get('medical_history', [])
    if not isinstance(medical_history, list) or any(not isinstance(item, str) for item in medical_history):
        return JsonResponse({'status': 'error', 'error': 'Medical history must be a list of text values.'}, status=400)

    def safe_text(field, limit=2000):
        value = data.get(field, '')
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError(field)
        return value.strip()

    try:
        medications = safe_text('medications')
        allergies = safe_text('allergies')
        additional_notes = safe_text('additional_notes')
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'error': f'{exc.args[0]} must be text under 2,000 characters.'}, status=400)

    cleaned = {
        'symptoms': [str(s).strip() for s in symptoms if str(s).strip()],
        'duration': duration,
        'severity': severity,
        'description': description,
        'medical_history': [str(m).strip() for m in medical_history if str(m).strip()],
        'medications': medications,
        'allergies': allergies,
        'additional_notes': additional_notes,
    }

    return JsonResponse({
        'status': 'validated',
        'phase': 3,
        'message': 'Intake form validated successfully. Ready for Gemini 3.8 Flash processing.',
        'intake': cleaned,
    })


def process_intake_view(request):
    """
    Processes validated patient intake data using the configured Gemini model.
    Extracts structured clinical documentation and identifies missing information.
    """
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'error': 'Only POST method is allowed.',
        }, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({
            'status': 'error',
            'error': 'Invalid JSON request payload.',
        }, status=400)

    if not isinstance(data, dict):
        return JsonResponse({'status': 'error', 'error': 'Request data must be a JSON object.'}, status=400)

    symptoms = data.get('symptoms', [])
    description = data.get('description', '')
    duration = data.get('duration', '')
    severity = data.get('severity', 5)
    if not isinstance(symptoms, list) or any(not isinstance(item, str) for item in symptoms):
        return JsonResponse({'status': 'error', 'error': 'Symptoms must be a list of text values.'}, status=400)
    if not isinstance(description, str) or len(description) > 5000:
        return JsonResponse({'status': 'error', 'error': 'Symptom description must be text under 5,000 characters.'}, status=400)
    if not isinstance(duration, str) or duration.strip() not in ALLOWED_DURATIONS:
        return JsonResponse({'status': 'error', 'error': 'A valid patient-reported symptom duration is required.'}, status=400)
    if not isinstance(severity, int) or not 1 <= severity <= 10:
        return JsonResponse({'status': 'error', 'error': 'Severity must be an integer from 1 to 10.'}, status=400)
    history = data.get('medical_history', [])
    if not isinstance(history, list) or any(not isinstance(item, str) for item in history):
        return JsonResponse({'status': 'error', 'error': 'Medical history must be a list of text values.'}, status=400)
    for field in ('medications', 'allergies', 'additional_notes'):
        value = data.get(field, '')
        if not isinstance(value, str) or len(value) > 2000:
            return JsonResponse({'status': 'error', 'error': f'{field} must be text under 2,000 characters.'}, status=400)
    if not symptoms and not description:
        return JsonResponse({
            'status': 'error',
            'error': 'Intake data must include symptoms or a description to process.',
        }, status=400)

    data['duration'] = duration.strip()

    result = process_patient_intake(data)
    if result.get('status') in ('success', 'blocked'):
        http_status = 200
    elif result.get('error_type') in ('invalid_model', 'configuration_error'):
        http_status = 500
    else:
        http_status = 502

    return JsonResponse(result, status=http_status)


def status_view(request):
    """
    System status and setup verification view.
    """
    status_data = get_model_status()

    if request.headers.get('Accept') == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse({
            'project': 'MediScribe',
            'phase': 3,
            'phase_name': 'Gemini 3.8 Flash Integration',
            'status': 'ready',
            'debug': settings.DEBUG,
            'gemini': status_data,
        })

    return JsonResponse({
        'status': 'operational',
        'phase': 3,
        'gemini': status_data,
    })


def health_check(request):
    """Simple JSON health check endpoint."""
    return JsonResponse({
        'status': 'healthy',
        'phase': 3,
        'gemini': get_model_status(),
    })
