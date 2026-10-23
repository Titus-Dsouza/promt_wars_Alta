import json
import logging
from unittest.mock import MagicMock, patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from intake.ai_service import (
    get_model_name,
    validate_model_name,
    is_gemini_configured,
    get_gemini_client,
    get_model_status,
    process_patient_intake,
    parse_and_validate_gemini_response,
    _source_grounded_report,
    ModelConfigurationError,
    ModelAPIError,
    SAFETY_DISCLAIMER,
)


class Phase1SetupTests(TestCase):
    """Setup and configuration tests from Phase 1."""

    def setUp(self):
        self.client = Client()

    def test_health_check_endpoint(self):
        """Confirm health check returns valid JSON status."""
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["phase"], 3)
        self.assertIn("gemini", data)
        self.assertEqual(data["gemini"]["model"], "gemini-3.8-flash")

    def test_status_json_negotiation(self):
        """Confirm that accessing /status/ returns JSON status."""
        response = self.client.get(reverse('status'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["project"], "MediScribe")
        self.assertEqual(data["phase"], 3)
        self.assertEqual(data["status"], "ready")

    def test_configured_model_defaults_to_requested_gemini_flash_id(self):
        with override_settings(GEMINI_MODEL='gemini-3.8-flash'):
            self.assertEqual(get_model_name(), 'gemini-3.8-flash')
            self.assertTrue(validate_model_name(get_model_name()))

    def test_model_name_validation_accepts_gemini_and_rejects_malformed_ids(self):
        self.assertTrue(validate_model_name('gemini-3.8-flash'))
        self.assertTrue(validate_model_name('gemini-3.7-flash'))
        self.assertFalse(validate_model_name('gemma-4-31b-it'))
        self.assertFalse(validate_model_name('https://example.invalid'))
        self.assertFalse(validate_model_name(''))

    def test_missing_api_key_does_not_crash_startup(self):
        """Starting the application or checking status without GEMINI_API_KEY must not raise an error."""
        with override_settings(GEMINI_API_KEY=''):
            self.assertFalse(is_gemini_configured())
            client = get_gemini_client(raise_on_missing=False)
            self.assertIsNone(client)
            status = get_model_status()
            self.assertFalse(status["configured"])
            self.assertIn("Awaiting API key", status["status"])

    def test_missing_api_key_raises_explicit_exception_when_demanded(self):
        """When an actual API call is attempted without a key, a descriptive error is raised."""
        with override_settings(GEMINI_API_KEY=''):
            with self.assertRaises(ModelConfigurationError) as ctx:
                get_gemini_client(raise_on_missing=True)
            self.assertIn("GEMINI_API_KEY is not configured", str(ctx.exception))


class Phase2UITests(TestCase):
    """UI, Form, and Validation tests for Phase 2."""

    def setUp(self):
        self.client = Client()

    def test_intake_page_renders_successfully(self):
        """Confirm that the intake page serves the complete UI."""
        response = self.client.get(reverse('intake'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MediScribe")
        self.assertContains(response, "Your health story, clearly organised.")
        self.assertContains(response, "Google Gemini 3.8 Flash")
        self.assertContains(response, "Start Patient Intake")
        self.assertContains(response, "Try Demo")
        self.assertContains(response, '/static/css/styles.css')
        self.assertContains(response, '/static/js/intake.js')
        self.assertContains(response, 'report-print-btn')
        self.assertContains(response, 'report-download-btn')
        self.assertContains(response, 'ai-uncertainties')
        self.assertContains(response, 'ai-conflicts')
        self.assertContains(response, 'ai-generated-at')
        self.assertContains(response, 'ai-additional-notes')
        self.assertContains(response, 'accept=".txt,text/plain"')
        self.assertContains(response, '16 KB')

    def test_intake_api_requires_csrf_token(self):
        """Same-origin intake endpoints reject cross-site POSTs without CSRF tokens."""
        client = Client(enforce_csrf_checks=True)
        page = client.get(reverse('intake'))
        self.assertEqual(page.status_code, 200)
        self.assertIn('csrftoken', client.cookies)
        response = client.post(
            reverse('validate_intake'),
            data=json.dumps({'symptoms': ['Headache']}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_local_frontend_cors_is_scoped_to_documented_origins(self):
        """The optional local frontend server gets exact-origin CORS, never wildcard CORS."""
        with override_settings(DEBUG=True):
            local = self.client.options(
                reverse('csrf_token'),
                HTTP_ORIGIN='http://localhost:3000',
            )
            self.assertEqual(local.status_code, 204)
            self.assertEqual(local['Access-Control-Allow-Origin'], 'http://localhost:3000')
            self.assertEqual(local['Access-Control-Allow-Credentials'], 'true')

            external = self.client.get(
                reverse('csrf_token'),
                HTTP_ORIGIN='https://untrusted.example',
            )
            self.assertNotIn('Access-Control-Allow-Origin', external)

    def test_documented_local_frontend_can_post_with_issued_csrf_token(self):
        """The local static frontend can obtain a token and submit to the API securely."""
        with override_settings(DEBUG=True):
            client = Client(enforce_csrf_checks=True)
            token_response = client.get(
                reverse('csrf_token'),
                HTTP_ORIGIN='http://localhost:3000',
                HTTP_HOST='127.0.0.1',
            )
            payload = {
                'symptoms': ['Headache'],
                'duration': '2-3_days',
                'description': 'A headache has been present for the last few days.',
            }
            response = client.post(
                reverse('validate_intake'),
                data=json.dumps(payload),
                content_type='application/json',
                HTTP_ORIGIN='http://localhost:3000',
                HTTP_HOST='127.0.0.1',
                HTTP_X_CSRFTOKEN=token_response.json()['csrfToken'],
            )

        self.assertEqual(token_response.status_code, 200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'validated')

    def test_intake_form_contains_required_controls(self):
        """Verify that the template renders all form elements and multiple-choice cards."""
        response = self.client.get(reverse('intake'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Persistent Cough")
        self.assertContains(response, "Fever or Chills")
        self.assertContains(response, "Shortness of Breath")
        self.assertContains(response, "other-symptom")
        self.assertContains(response, "dur-today")
        self.assertContains(response, "dur-days")
        self.assertContains(response, "severity-scale")
        self.assertContains(response, "symptom-description")
        self.assertContains(response, "current-medications")
        self.assertContains(response, "known-allergies")
        self.assertContains(response, "review-symptoms")
        self.assertContains(response, "loading-overlay")

    def test_validate_intake_api_success(self):
        """Confirm valid intake payload is accepted and properly cleaned."""
        payload = {
            "symptoms": ["Persistent Cough", "Fever or Chills"],
            "duration": "2-3_days",
            "severity": 6,
            "description": "Fever spike to 101 F accompanied by productive cough and chest congestion.",
            "medical_history": ["Asthma / Respiratory"],
            "medications": "Albuterol inhaler",
            "allergies": "Penicillin",
            "additional_notes": "No previous hospitalizations.",
        }
        response = self.client.post(
            reverse('validate_intake'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "validated")
        self.assertEqual(len(data["intake"]["symptoms"]), 2)
        self.assertEqual(data["intake"]["severity"], 6)

    def test_validate_intake_missing_symptoms(self):
        """Verify error when no symptoms are provided."""
        payload = {
            "symptoms": [],
            "duration": "2-3_days",
            "description": "Aches and pains throughout the entire body for multiple days.",
        }
        response = self.client.post(
            reverse('validate_intake'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_validate_intake_invalid_duration(self):
        """Verify error when invalid duration is submitted."""
        payload = {
            "symptoms": ["Headache"],
            "duration": "invalid_duration_string",
            "description": "Severe migraine starting early morning.",
        }
        response = self.client.post(
            reverse('validate_intake'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_validate_intake_description_too_short(self):
        """Verify error when description is under 10 characters."""
        payload = {
            "symptoms": ["Persistent Cough"],
            "duration": "under_24_hours",
            "description": "cough",
        }
        response = self.client.post(
            reverse('validate_intake'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_validate_intake_rejects_oversized_patient_notes(self):
        payload = {
            'symptoms': ['Headache'],
            'duration': '2-3_days',
            'description': 'Headache continuing for the past few days.',
            'additional_notes': 'x' * 2001,
        }
        response = self.client.post(
            reverse('validate_intake'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('additional_notes', response.json()['error'])


class Phase3GeminiIntegrationTests(TestCase):
    """Gemini Flash integration, response safety, and error tests."""

    def setUp(self):
        self.client = Client()
        self.sample_payload = {
            "symptoms": ["Persistent Cough", "Fever or Chills"],
            "duration": "2-3_days",
            "severity": 6,
            "description": "Hacking cough with low-grade fever starting 3 days ago. Wheezing at night.",
            "medical_history": ["Asthma / Respiratory"],
            "medications": "Albuterol inhaler",
            "allergies": "Penicillin",
            "additional_notes": "Chest feels tight after walking up stairs.",
        }

    def test_process_without_api_key_reports_honest_blocker(self):
        """When GEMINI_API_KEY is not configured, report the blocker honestly without fake output."""
        with override_settings(GEMINI_API_KEY=''):
            response = self.client.post(
                reverse('process_intake'),
                data=json.dumps(self.sample_payload),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "blocked")
            self.assertEqual(data["error_type"], "missing_api_key")
            self.assertTrue(data["requires_key"])
            self.assertIn("GEMINI_API_KEY is not configured", data["error"])

    def test_structurally_malformed_json_response_is_rejected(self):
        """Valid JSON with invalid clinical field types is rejected as malformed output."""
        raw = json.dumps({
            'chief_complaint': 'Headache',
            'structured_symptoms': [],
            'timeline': 'A few days',
            'medical_history': {
                'chronic_conditions': [], 'current_medications': [],
                'known_allergies': 'not-a-list', 'additional_notes': '',
            },
            'conflicting_information': [],
            'missing_or_uncertain_information': [],
            'follow_up_questions': [],
        })
        with self.assertRaises(ModelAPIError) as context:
            parse_and_validate_gemini_response(raw)
        self.assertEqual(context.exception.error_type, 'malformed_output')

    def test_explicit_conflicts_are_preserved_without_invention(self):
        parsed = parse_and_validate_gemini_response(json.dumps({
            'chief_complaint': 'Patient-reported symptoms',
            'structured_symptoms': [],
            'timeline': 'As reported',
            'medical_history': {
                'chronic_conditions': [], 'current_medications': [],
                'known_allergies': [], 'additional_notes': '',
            },
            'conflicting_information': ['Patient reports symptoms began today and also three days ago.'],
            'missing_or_uncertain_information': [],
            'follow_up_questions': [],
        }))
        self.assertEqual(len(parsed['conflicting_information']), 1)
        self.assertEqual(parsed['clinical_safety_notice'], SAFETY_DISCLAIMER)

    def test_model_suggested_prescription_question_is_rejected(self):
        with self.assertRaises(ModelAPIError) as context:
            parse_and_validate_gemini_response(json.dumps({
                'chief_complaint': 'Reported concern',
                'structured_symptoms': [],
                'timeline': 'Patient selected duration',
                'medical_history': {
                    'chronic_conditions': [], 'current_medications': [],
                    'known_allergies': [], 'additional_notes': '',
                },
                'conflicting_information': [],
                'missing_or_uncertain_information': [],
                'follow_up_questions': ['Should you start taking 20 mg of medicine?'],
            }))
        self.assertEqual(context.exception.error_type, 'unsafe_output')

    def test_model_conflict_flags_need_two_patient_quotes(self):
        model_data = {
            'conflicting_information': [
                'Patient statement conflict: "At 9 I had a cough" and "At 10 I did not have a cough".',
                'Patient statement conflict: "I had a seizure" and "I fainted twice".',
            ],
            'missing_or_uncertain_information': [],
            'follow_up_questions': [],
        }
        intake = {
            'symptoms': ['Cough'], 'duration': 'under_24_hours', 'severity': 3,
            'description': 'At 9 I had a cough. At 10 I did not have a cough.',
            'medical_history': [], 'medications': '', 'allergies': '', 'additional_notes': '',
        }
        grounded = _source_grounded_report(model_data, intake)
        self.assertEqual(len(grounded['conflicting_information']), 1)
        self.assertIn('At 9 I had a cough', grounded['conflicting_information'][0])

    @patch('google.genai.Client')
    def test_process_intake_success_with_mocked_gemini(self, mock_client_cls):
        """Process a mocked Gemini response and return an intake-grounded report."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "chief_complaint": "Persistent cough and low-grade fever for 3 days in an asthmatic patient",
            "structured_symptoms": [
                {
                    "symptom": "Invented symptom",
                    "reported_duration": "2-3 days",
                    "severity_score": "6",
                    "details": "Hacking cough with nocturnal wheezing"
                },
                {
                    "symptom": "Fever or Chills",
                    "reported_duration": "2-3 days",
                    "severity_score": "6",
                    "details": "Low-grade fever"
                }
            ],
            "timeline": "Symptom onset 3 days ago, progressing to nighttime wheezing",
            "medical_history": {
                "chronic_conditions": ["Asthma / Respiratory", "Invented condition"],
                "current_medications": ["Insulin not reported by patient"],
                "known_allergies": ["Latex not reported by patient"],
                "additional_notes": "Invented test result"
            },
            "missing_or_uncertain_information": [
                "Specific peak temperature readings",
                "Frequency of albuterol inhaler usage"
            ],
            "follow_up_questions": [
                "Have you measured your exact body temperature with a thermometer?",
                "How many puffs of your albuterol inhaler are you requiring per day?"
            ],
            "conflicting_information": [],
        })
        mock_instance.models.generate_content.return_value = mock_response

        with override_settings(GEMINI_API_KEY='mock-test-key-phase3', GEMINI_MODEL='gemini-3.8-flash'):
            response = self.client.post(
                reverse('process_intake'),
                data=json.dumps(self.sample_payload),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["model"], "gemini-3.8-flash")

            # Verify structured extraction
            ai_data = data["data"]
            self.assertEqual(ai_data["chief_complaint"], "Persistent Cough; Fever or Chills")
            self.assertEqual(len(ai_data["structured_symptoms"]), 2)
            self.assertEqual(ai_data["timeline"], "Patient-selected duration: 2-3_days. Patient description: Hacking cough with low-grade fever starting 3 days ago. Wheezing at night.")
            self.assertEqual(ai_data["medical_history"]["current_medications"], ["Albuterol inhaler"])
            self.assertEqual(ai_data["medical_history"]["chronic_conditions"], ["Asthma / Respiratory"])
            self.assertEqual(ai_data["medical_history"]["known_allergies"], ["Penicillin"])
            self.assertEqual(ai_data["medical_history"]["additional_notes"], self.sample_payload["additional_notes"])
            self.assertNotIn("Invented symptom", str(ai_data))
            self.assertNotIn("Invented condition", str(ai_data))
            self.assertNotIn("Insulin", str(ai_data))
            self.assertEqual(len(ai_data["follow_up_questions"]), 2)
            self.assertEqual(ai_data["clinical_safety_notice"], SAFETY_DISCLAIMER)

            # Verify the SDK client was called with the requested model ID.
            mock_instance.models.generate_content.assert_called_once()
            call_kwargs = mock_instance.models.generate_content.call_args.kwargs
            self.assertEqual(call_kwargs["model"], "gemini-3.8-flash")

    @patch('google.genai.Client')
    def test_malformed_model_identifier_is_rejected(self, mock_client_cls):
        with override_settings(GEMINI_API_KEY='mock-test-key', GEMINI_MODEL='not-a-model'):
            response = self.client.post(
                reverse('process_intake'),
                data=json.dumps(self.sample_payload),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error_type"], "invalid_model")
            self.assertIn("valid Gemini model ID", data["error"])
            mock_client_cls.assert_not_called()

    @patch('google.genai.Client')
    def test_follow_up_questions_generated_when_details_missing(self, mock_client_cls):
        """Follow-up questions are parsed and returned when critical details are absent."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "chief_complaint": "Severe headache with no duration",
            "structured_symptoms": [],
            "timeline": "Unclear timeline",
            "medical_history": {
                "chronic_conditions": [], "current_medications": [],
                "known_allergies": [], "additional_notes": "",
            },
            "conflicting_information": [],
            "missing_or_uncertain_information": ["Onset suddenness", "Photophobia / visual aura"],
            "follow_up_questions": [
                "Did this headache begin suddenly like a thunderclap or build gradually?",
                "Are you experiencing any visual changes, numbness, or sensitivity to light?"
            ],
            "clinical_safety_notice": SAFETY_DISCLAIMER
        })
        mock_instance.models.generate_content.return_value = mock_response

        with override_settings(GEMINI_API_KEY='mock-key'):
            res = process_patient_intake({"symptoms": ["Headache"], "description": "Bad headache"})
            self.assertEqual(res["status"], "success")
            self.assertEqual(len(res["data"]["follow_up_questions"]), 2)
            self.assertIn("thunderclap", res["data"]["follow_up_questions"][0])

    @patch('google.genai.Client')
    def test_empty_follow_up_questions_when_intake_complete(self, mock_client_cls):
        """When intake information is fully specified, follow_up_questions is an empty list."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "chief_complaint": "Mild ankle strain after twist 2 hours ago",
            "structured_symptoms": [],
            "timeline": "2 hours ago",
            "medical_history": {
                "chronic_conditions": [], "current_medications": [],
                "known_allergies": [], "additional_notes": "",
            },
            "conflicting_information": [],
            "missing_or_uncertain_information": [],
            "follow_up_questions": [],
            "clinical_safety_notice": SAFETY_DISCLAIMER
        })
        mock_instance.models.generate_content.return_value = mock_response

        with override_settings(GEMINI_API_KEY='mock-key'):
            res = process_patient_intake(self.sample_payload)
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["data"]["follow_up_questions"], [])

    @patch('google.genai.Client')
    def test_handle_rate_limit_error(self, mock_client_cls):
        """Handle 429 quota / rate limit errors gracefully without crashing."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        provider_error = Exception("provider details must not be echoed")
        provider_error.code = 429
        mock_instance.models.generate_content.side_effect = provider_error

        with override_settings(GEMINI_API_KEY='mock-key'):
            response = self.client.post(
                reverse('process_intake'),
                data=json.dumps(self.sample_payload),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 502)
            data = response.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error_type"], "rate_limit")
            self.assertIn("rate limited", data["error"])

    @patch('google.genai.Client')
    def test_unavailable_account_model_returns_honest_error(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        provider_error = Exception("private provider details")
        provider_error.code = 404
        mock_instance.models.generate_content.side_effect = provider_error

        with override_settings(GEMINI_API_KEY='mock-key', GEMINI_MODEL='gemini-3.8-flash'):
            result = process_patient_intake(self.sample_payload)

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'model_unavailable')
        self.assertNotIn('private provider details', str(result))
        self.assertNotIn('data', result)

    @patch('google.genai.Client')
    def test_invalid_credentials_return_safe_error(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        provider_error = Exception("secret-bearing provider response")
        provider_error.code = 403
        mock_instance.models.generate_content.side_effect = provider_error

        with override_settings(GEMINI_API_KEY='mock-key'):
            result = process_patient_intake(self.sample_payload)

        self.assertEqual(result['error_type'], 'authentication_error')
        self.assertNotIn('secret-bearing provider response', str(result))

    @patch('google.genai.Client')
    def test_bad_api_key_response_400_is_safe(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        provider_error = Exception("API key details and private payload")
        provider_error.code = 400
        mock_instance.models.generate_content.side_effect = provider_error

        with override_settings(GEMINI_API_KEY='mock-key'):
            result = process_patient_intake(self.sample_payload)

        self.assertEqual(result['error_type'], 'invalid_request')
        self.assertIn('Check the API key', result['error'])
        self.assertNotIn('private payload', str(result))

    @patch('google.genai.Client')
    def test_timeout_returns_safe_error_without_report(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.models.generate_content.side_effect = TimeoutError('private timeout details')

        with override_settings(GEMINI_API_KEY='mock-key'):
            result = process_patient_intake(self.sample_payload)

        self.assertEqual(result['error_type'], 'timeout')
        self.assertNotIn('private timeout details', str(result))
        self.assertNotIn('data', result)

    @patch('google.genai.Client')
    def test_network_error_is_safe_and_does_not_echo_exception_details(self, mock_client_cls):
        """Network failures are reported without echoing request or credential text."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.models.generate_content.side_effect = Exception(
            'connection failed while handling private patient note and mock-secret-key'
        )

        with override_settings(GEMINI_API_KEY='mock-secret-key'):
            response = self.client.post(
                reverse('process_intake'),
                data=json.dumps(self.sample_payload),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()['error_type'], 'network_error')
        self.assertNotContains(response, 'private patient note', status_code=502)
        self.assertNotContains(response, 'mock-secret-key', status_code=502)

    @patch('google.genai.Client')
    def test_handle_malformed_json_response(self, mock_client_cls):
        """Handle non-parseable output from model gracefully."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.text = "I cannot format this as JSON: Here is my narrative thought..."
        mock_instance.models.generate_content.return_value = mock_response

        with override_settings(GEMINI_API_KEY='mock-key'):
            response = self.client.post(
                reverse('process_intake'),
                data=json.dumps(self.sample_payload),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 502)
            data = response.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error_type"], "malformed_output")

    @patch('google.genai.Client')
    def test_incomplete_model_response_does_not_return_fallback_report(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.text = json.dumps({'chief_complaint': 'Invented successful summary'})
        mock_instance.models.generate_content.return_value = mock_response

        with override_settings(GEMINI_API_KEY='mock-key'):
            result = process_patient_intake(self.sample_payload)

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'malformed_output')
        self.assertNotIn('data', result)

    @patch('google.genai.Client')
    def test_handle_empty_gemini_response(self, mock_client_cls):
        """Handle empty or None response from model."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.text = ""
        mock_instance.models.generate_content.return_value = mock_response

        with override_settings(GEMINI_API_KEY='mock-key'):
            response = self.client.post(
                reverse('process_intake'),
                data=json.dumps(self.sample_payload),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 502)
            data = response.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error_type"], "empty_response")

    @patch('google.genai.Client')
    def test_no_patient_sensitive_data_in_logging(self, mock_client_cls):
        """Ensure logging during AI processing does not log raw patient text or API keys."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "chief_complaint": "Extracted summary",
            "structured_symptoms": [],
            "timeline": "Timeline",
            "medical_history": {
                "chronic_conditions": [], "current_medications": [],
                "known_allergies": [], "additional_notes": "",
            },
            "conflicting_information": [],
            "missing_or_uncertain_information": [],
            "follow_up_questions": [],
            "clinical_safety_notice": SAFETY_DISCLAIMER
        })
        mock_instance.models.generate_content.return_value = mock_response

        secret_symptom_detail = "Confidential sensitive patient note XYZ123"
        payload = {
            "symptoms": ["Persistent Cough"],
            "description": secret_symptom_detail,
        }

        with self.assertLogs('intake.ai_service', level=logging.INFO) as captured_logs:
            with override_settings(GEMINI_API_KEY='mock-private-key-12345'):
                process_patient_intake(payload)

            log_output = " ".join(captured_logs.output)
            self.assertNotIn(secret_symptom_detail, log_output)
            self.assertNotIn("mock-private-key-12345", log_output)
