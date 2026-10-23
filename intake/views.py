import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .gemma_service import get_gemma_status, process_patient_intake

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
    free-text symptoms, interactive progress states, and Gemma 4 AI processing.
    """
    context = {
        'model_name': getattr(settings, 'GEMMA_MODEL', 'gemma-4-31b-it'),
        'phase': 3,
    }
    return render(request, 'intake/intake.html', context)


@csrf_exempt
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

    symptoms = data.get('symptoms', [])
    if not isinstance(symptoms, list) or len(symptoms) == 0:
        return JsonResponse({
            'status': 'error',
            'error': 'At least one primary symptom must be selected.',
        }, status=400)

    duration = data.get('duration', '').strip()
    if duration not in ALLOWED_DURATIONS:
        return JsonResponse({
            'status': 'error',
            'error': f'Invalid duration value. Allowed: {", ".join(sorted(ALLOWED_DURATIONS))}',
        }, status=400)

    description = data.get('description', '').strip()
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
    if not isinstance(medical_history, list):
        medical_history = []

    cleaned = {
        'symptoms': [str(s).strip() for s in symptoms if str(s).strip()],
        'duration': duration,
        'severity': severity,
        'description': description,
        'medical_history': [str(m).strip() for m in medical_history if str(m).strip()],
        'medications': str(data.get('medications', '')).strip(),
        'allergies': str(data.get('allergies', '')).strip(),
        'additional_notes': str(data.get('additional_notes', '')).strip(),
    }

    return JsonResponse({
        'status': 'validated',
        'phase': 3,
        'message': 'Intake form validated successfully. Ready for Gemma 4 AI processing.',
        'intake': cleaned,
    })


@csrf_exempt
def process_intake_view(request):
    """
    Phase 3: Processes validated patient intake data using Google Gemma 4.
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

    symptoms = data.get('symptoms', [])
    description = data.get('description', '')
    if not symptoms and not description:
        return JsonResponse({
            'status': 'error',
            'error': 'Intake data must include symptoms or a description to process.',
        }, status=400)

    result = process_patient_intake(data)
    http_status = 200 if result.get('status') in ('success', 'blocked') else 500

    return JsonResponse(result, status=http_status)


def status_view(request):
    """
    System status and setup verification view.
    """
    status_data = get_gemma_status()

    if request.headers.get('Accept') == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse({
            'project': 'MediScribe',
            'phase': 3,
            'phase_name': 'Gemma 4 AI Integration',
            'status': 'ready',
            'debug': settings.DEBUG,
            'gemma': status_data,
        })

    return JsonResponse({
        'status': 'operational',
        'phase': 3,
        'gemma': status_data,
    })


def health_check(request):
    """Simple JSON health check endpoint."""
    return JsonResponse({
        'status': 'healthy',
        'phase': 3,
        'gemma': get_gemma_status(),
    })
