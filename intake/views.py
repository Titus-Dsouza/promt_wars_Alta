import json
import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .gemma_service import get_gemma_status

logger = logging.getLogger(__name__)

ALLOWED_DURATIONS = {
    'under_24_hours',
    '2-3_days',
    '1-2_weeks',
    'over_a_month',
}


def intake_view(request):
    """
    Renders the primary patient intake interface (Phase 2 UI).
    Supports desktop and mobile responsive layout, multiple-choice questions,
    free-text symptoms, and interactive progress states.
    """
    context = {
        'model_name': getattr(settings, 'GEMMA_MODEL', 'gemma-4-31b-it'),
        'phase': 2,
    }
    return render(request, 'intake/intake.html', context)


@csrf_exempt
def validate_intake_view(request):
    """
    Validates patient intake submission payload without triggering AI processing.
    Phase 2: Confirms form data validity and returns structured intake state.
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
        'phase': 2,
        'message': 'Intake form validated successfully. Ready for Phase 3 Gemma 4 processing.',
        'intake': cleaned,
    })


def status_view(request):
    """
    System status and setup verification view.
    """
    status_data = get_gemma_status()

    if request.headers.get('Accept') == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse({
            'project': 'MediScribe',
            'phase': 2,
            'phase_name': 'Patient Intake UI',
            'status': 'ready',
            'debug': settings.DEBUG,
            'gemma': status_data,
        })

    return JsonResponse({
        'status': 'operational',
        'phase': 2,
        'gemma': status_data,
    })


def health_check(request):
    """Simple JSON health check endpoint."""
    return JsonResponse({
        'status': 'healthy',
        'phase': 2,
        'gemma': get_gemma_status(),
    })
