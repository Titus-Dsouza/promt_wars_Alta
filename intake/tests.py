import json
import logging
from unittest.mock import MagicMock, patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from intake.gemma_service import (
    get_gemma_model_name,
    validate_gemma_model,
    is_gemma_configured,
    get_gemma_client,
    get_gemma_status,
    process_patient_intake,
    GemmaConfigurationError,
    GemmaAPIError,
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
        self.assertIn("gemma", data)
        self.assertEqual(data["gemma"]["model"], "gemma-4-31b-it")

    def test_status_json_negotiation(self):
        """Confirm that accessing /status/ returns JSON status."""
        response = self.client.get(reverse('status'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["project"], "MediScribe")
        self.assertEqual(data["phase"], 3)
        self.assertEqual(data["status"], "ready")

    def test_gemma_model_default_is_gemma_4(self):
        """Ensure default model is a Gemma 4 model, not Gemini."""
        model = get_gemma_model_name()
        self.assertTrue(validate_gemma_model(model))
        self.assertIn("gemma-4", model.lower())
        self.assertFalse(model.lower().startswith("gemini"))

    def test_model_validation_rejects_gemini(self):
        """Verify that Gemini models are not accepted in place of Gemma."""
        self.assertFalse(validate_gemma_model("gemini-1.5-flash"))
        self.assertFalse(validate_gemma_model("gemini-2.0-flash"))
        self.assertFalse(validate_gemma_model("gemini-2.5-pro"))
        self.assertTrue(validate_gemma_model("gemma-4-31b-it"))
        self.assertTrue(validate_gemma_model("gemma-4-26b-a4b-it"))

    def test_missing_api_key_does_not_crash_startup(self):
        """Starting the application or checking status without GEMINI_API_KEY must not raise an error."""
        with override_settings(GEMINI_API_KEY=''):
            self.assertFalse(is_gemma_configured())
            client = get_gemma_client(raise_on_missing=False)
            self.assertIsNone(client)
            status = get_gemma_status()
            self.assertFalse(status["configured"])
            self.assertIn("Awaiting API key", status["status"])

    def test_missing_api_key_raises_explicit_exception_when_demanded(self):
        """When an actual API call is attempted without a key, a descriptive error is raised."""
        with override_settings(GEMINI_API_KEY=''):
            with self.assertRaises(GemmaConfigurationError) as ctx:
                get_gemma_client(raise_on_missing=True)
            self.assertIn("GEMINI_API_KEY is not set", str(ctx.exception))


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
        self.assertContains(response, "Google Gemma 4")
        self.assertContains(response, "Start Patient Intake")
        self.assertContains(response, "Try Demo")

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


class Phase3GeminiIntegrationTests(TestCase):
    """Gemma 4 AI Integration, Prompting, and Safety tests for Phase 3."""

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

    @patch('google.genai.Client')
    def test_process_intake_success_with_mocked_gemma(self, mock_client_cls):
        """Process validated intake with mocked Gemma 4 response and verify structure."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "chief_complaint": "Persistent cough and low-grade fever for 3 days in an asthmatic patient",
            "structured_symptoms": [
                {
                    "symptom": "Persistent Cough",
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
                "chronic_conditions": ["Asthma / Respiratory"],
                "current_medications": ["Albuterol inhaler"],
                "known_allergies": ["Penicillin"],
                "additional_notes": "Exertional dyspnea on stairs"
            },
            "missing_or_uncertain_information": [
                "Specific peak temperature readings",
                "Frequency of albuterol inhaler usage"
            ],
            "follow_up_questions": [
                "Have you measured your exact body temperature with a thermometer?",
                "How many puffs of your albuterol inhaler are you requiring per day?"
            ],
            "clinical_safety_notice": SAFETY_DISCLAIMER
        })
        mock_instance.models.generate_content.return_value = mock_response

        with override_settings(GEMINI_API_KEY='mock-test-key-phase3'):
            response = self.client.post(
                reverse('process_intake'),
                data=json.dumps(self.sample_payload),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["model"], "gemma-4-31b-it")
            self.assertIn("gemma-4", data["model"])

            # Verify structured extraction
            ai_data = data["data"]
            self.assertIn("Persistent cough", ai_data["chief_complaint"])
            self.assertEqual(len(ai_data["structured_symptoms"]), 2)
            self.assertEqual(len(ai_data["follow_up_questions"]), 2)
            self.assertEqual(ai_data["clinical_safety_notice"], SAFETY_DISCLAIMER)

            # Verify the SDK client was called with the exact Gemma 4 model
            mock_instance.models.generate_content.assert_called_once()
            call_kwargs = mock_instance.models.generate_content.call_args.kwargs
            self.assertEqual(call_kwargs["model"], "gemma-4-31b-it")
            self.assertFalse(call_kwargs["model"].startswith("gemini-"))

    @patch('google.genai.Client')
    def test_gemini_model_substitution_is_blocked(self, mock_client_cls):
        """Silently substituting Gemini models (e.g. gemini-2.0-flash) must be rejected."""
        with override_settings(GEMINI_API_KEY='mock-test-key', GEMMA_MODEL='gemini-2.5-pro'):
            response = self.client.post(
                reverse('process_intake'),
                data=json.dumps(self.sample_payload),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error_type"], "invalid_model")
            self.assertIn("requires a Gemma 4 model, not Gemini", data["error"])
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
            "medical_history": {},
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
            "medical_history": {},
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
        mock_instance.models.generate_content.side_effect = Exception("429 Resource exhausted: quota exceeded")

        with override_settings(GEMINI_API_KEY='mock-key'):
            response = self.client.post(
                reverse('process_intake'),
                data=json.dumps(self.sample_payload),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error_type"], "rate_limit")
            self.assertIn("rate limit reached", data["error"])

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
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error_type"], "malformed_output")

    @patch('google.genai.Client')
    def test_handle_empty_gemma_response(self, mock_client_cls):
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
            self.assertEqual(response.status_code, 500)
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
            "medical_history": {},
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

        with self.assertLogs('intake.gemma_service', level=logging.INFO) as captured_logs:
            with override_settings(GEMINI_API_KEY='mock-private-key-12345'):
                process_patient_intake(payload)

            log_output = " ".join(captured_logs.output)
            self.assertNotIn(secret_symptom_detail, log_output)
            self.assertNotIn("mock-private-key-12345", log_output)
