import os
from django.test import SimpleTestCase
from django.contrib.staticfiles import finders

class StaticAssetsTest(SimpleTestCase):
    def test_css_exists(self):
        """Verify that the main CSS file is findable by Django."""
        path = finders.find('css/styles.css')
        self.assertIsNotNone(path, "Could not find 'css/styles.css' in static files")
        self.assertTrue(os.path.exists(path), f"File at {path} does not exist on disk")

    def test_js_exists(self):
        """Verify that the main JS file is findable by Django."""
        path = finders.find('js/intake.js')
        self.assertIsNotNone(path, "Could not find 'js/intake.js' in static files")
        self.assertTrue(os.path.exists(path), f"File at {path} does not exist on disk")
