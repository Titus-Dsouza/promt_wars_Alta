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
    """Setup and configuration tests for Phase 1."""

    def setUp(self):
        self.client = Client()

    def test_status_page_renders_successfully(self):
        """Confirm that the application starts and serves the setup status page."""
        response = self.client.get(reverse('status'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MediScribe")
        self.assertContains(response, "Phase 1")
        self.assertContains(response, "gemma-4-31b-it")

    def test_health_check_endpoint(self):
        """Confirm health check returns valid JSON status."""
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["phase"], 1)
        self.assertIn("gemma", data)
        self.assertEqual(data["gemma"]["model"], "gemma-4-31b-it")

    def test_json_status_negotiation(self):
        """Confirm that passing Accept header or format=json returns JSON status."""
        response = self.client.get(reverse('status'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["project"], "MediScribe")
        self.assertEqual(data["phase"], 1)
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
            # Default get_gemma_client must return None rather than crashing
            client = get_gemma_client(raise_on_missing=False)
            self.assertIsNone(client)
            # Status should clearly report awaiting key
            status = get_gemma_status()
            self.assertFalse(status["configured"])
            self.assertIn("Awaiting API key", status["status"])

    def test_missing_api_key_raises_explicit_exception_when_demanded(self):
        """When an actual API call is attempted without a key, a descriptive error is raised."""
        with override_settings(GEMINI_API_KEY=''):
            with self.assertRaises(GemmaConfigurationError) as ctx:
                get_gemma_client(raise_on_missing=True)
            self.assertIn("GEMINI_API_KEY is not set", str(ctx.exception))
