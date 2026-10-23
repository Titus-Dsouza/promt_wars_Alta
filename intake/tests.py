import json
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from intake.gemma_service import (
    get_gemma_model_name,
    validate_gemma_model,
    is_gemma_configured,
    get_gemma_client,
    get_gemma_status,
    GemmaConfigurationError,
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
        self.assertEqual(data["phase"], 2)
        self.assertIn("gemma", data)
        self.assertEqual(data["gemma"]["model"], "gemma-4-31b-it")

    def test_status_json_negotiation(self):
        """Confirm that accessing /status/ returns JSON status."""
        response = self.client.get(reverse('status'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["project"], "MediScribe")
        self.assertEqual(data["phase"], 2)
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
        """Confirm that the intake page serves the complete Phase 2 UI."""
        response = self.client.get(reverse('intake'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MediScribe")
        self.assertContains(response, "Your health story, clearly organised.")
        self.assertContains(response, "Google Gemma 4")
        self.assertContains(response, "Start Patient Intake")
        self.assertContains(response, "Try Demo")

    def test_intake_form_contains_required_controls(self):
        """Verify that the template renders all Phase 2 form elements and multiple-choice cards."""
        response = self.client.get(reverse('intake'))
        self.assertEqual(response.status_code, 200)
        # Step 1: Symptoms
        self.assertContains(response, "Persistent Cough")
        self.assertContains(response, "Fever or Chills")
        self.assertContains(response, "Shortness of Breath")
        self.assertContains(response, "other-symptom")
        # Step 2: Duration, Severity, Description
        self.assertContains(response, "dur-today")
        self.assertContains(response, "dur-days")
        self.assertContains(response, "severity-scale")
        self.assertContains(response, "symptom-description")
        # Step 3: Medical background
        self.assertContains(response, "current-medications")
        self.assertContains(response, "known-allergies")
        # Step 4 & States
        self.assertContains(response, "review-symptoms")
        self.assertContains(response, "loading-overlay")
        self.assertContains(response, "Organising your health story...")

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
        self.assertEqual(data["phase"], 2)
        self.assertEqual(len(data["intake"]["symptoms"]), 2)
        self.assertEqual(data["intake"]["severity"], 6)
        self.assertEqual(data["intake"]["duration"], "2-3_days")

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
        self.assertIn("symptom", data["error"].lower())

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
        data = response.json()
        self.assertIn("duration", data["error"].lower())

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
        data = response.json()
        self.assertIn("description", data["error"].lower())

    def test_validate_intake_rejects_get(self):
        """Ensure GET request to validate endpoint returns 400 Bad Request."""
        response = self.client.get(reverse('validate_intake'))
        self.assertEqual(response.status_code, 400)
