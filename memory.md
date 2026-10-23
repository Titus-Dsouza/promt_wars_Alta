# MediScribe — Memory & Execution Log

## 1. Project Overview
MediScribe is a clinical patient intake application that collects patient symptoms, duration, medical history, allergies, and concerns, and prepares structured, doctor-ready summaries using Google Gemma 4 AI via the Gemini API (`google-genai` SDK).

- **Repository:** https://github.com/Titus-Dsouza/promt_wars_Alta
- **Branch:** `main`
- **Remote:** `origin -> https://github.com/Titus-Dsouza/promt_wars_Alta.git`
- **Tech Stack:** Python 3.14, Django 6.1, HTML5 / CSS3 / JavaScript, Google GenAI SDK (`google-genai`)
- **Target Model:** Google Gemma 4 (`gemma-4-31b-it`, `gemma-4-26b-a4b-it`)

---

## 2. Phase 1: Setup & Configuration (Completed & Pushed)
- **Commit:** `5e81806`
- Set up Django backend, `.env.example`, `.gitignore` strictly excluding secrets, and minimal dependencies (`django`, `python-dotenv`, `google-genai`).
- Verified Gemma 4 access via Gemini API, preventing Gemini model substitution and key exposure.

---

## 3. Phase 2: Build the UI (Completed & Pushed)
- **Commit:** `a9c39c6`
- Built responsive patient intake wizard adhering to `Design.md` color palette and components.
- Provided multiple-choice symptom cards, duration radios, 1-10 severity scale, free-text description, medications, and allergies.
- Implemented `/api/validate/` endpoint, accessible keyboard navigation, loading state, and step review.

---

## 4. Phase 3: Gemini / Gemma 4 AI Integration (Completed)

### Summary of Completed Work
- **SDK & Model Integration:**
  - Integrated Google's official `google-genai` Python SDK (`from google import genai`).
  - Configured target model `gemma-4-31b-it` (Google Gemma 4 open weights dense model) with fallback to `gemma-4-26b-a4b-it`.
  - Enforced strict model validation (`validate_gemma_model`), which actively rejects mistaken Gemini substitutions (e.g., `gemini-1.5`, `gemini-2.0`, `gemini-2.5`).
- **Clinical Prompt Engineering & Guardrails:**
  - Designed clinical structuring prompt adhering to core safety constraints:
    - Never diagnose diseases, illnesses, or conditions.
    - Never prescribe medications, dosages, or treatments.
    - Never invent or hallucinate missing patient facts.
    - Distinguish between patient-reported facts and extracted structure.
    - Ask relevant follow-up questions **only when important clinical information is missing or ambiguous** (e.g., onset timeline, specific peak temperature, severity progression, missing medication dosages, or unclear drug allergy reactions). If all essential information is present, returns an empty list.
- **Robust Error Handling & Output Validation:**
  - Missing API key: Returns `{ "status": "blocked", "error_type": "missing_api_key", "requires_key": True }` and displays an honest explanation banner in the UI without faking AI data.
  - Rate limiting & quota exhaustion (429): Cleanly caught and reported as `error_type: "rate_limit"`.
  - Authentication errors (401/403): Reported as `error_type: "authentication_error"`.
  - Malformed JSON output: Automatically strips markdown code fences (` ```json `), extracts outermost JSON objects, and validates schema fields.
  - Enforces persistent `clinical_safety_notice` disclaimer on every parsed response.
- **Privacy & Secret Protection:**
  - Avoided logging raw patient descriptions or sensitive medical text.
  - Ensured API keys are never written to disk, logged, or exposed in client responses.
- **Frontend AI Results & Blocker Display:**
  - Connected intake wizard submission to `/api/process/`.
  - Displays structured chief complaint, symptoms list, timeline, and background.
  - Dynamically renders clarifying follow-up questions under *"Recommended Clarifying Questions for Your Consultation"* only when Gemma 4 identifies missing clinical details.
  - Displays an honest blocker card when `GEMINI_API_KEY` is not present in `.env`, displaying the validated intake data without faking output.
- **Checklist Updated:** Marked all Phase 3 tasks complete in `phase.md`.

### Files Changed / Created in Phase 3
- `intake/gemma_service.py`: Added `process_patient_intake()`, `build_gemma_prompt()`, `parse_and_validate_gemma_response()`, and error handling for rate limits, auth errors, and malformed JSON.
- `intake/views.py`: Added `process_intake_view()` mapped to `POST /api/process/` and updated phase status to 3.
- `intake/urls.py`: Added route for `/api/process/`.
- `templates/intake/intake.html`: Added `#ai-results-step` (chief complaint, structured symptoms, timeline, follow-up questions card, safety disclaimer) and `#ai-blocker-step` (honest missing API key notice).
- `static/css/styles.css`: Added styles for AI badges, chief complaint box, structured symptom items, follow-up question list, and blocker notices.
- `static/js/intake.js`: Added Phase 3 submission workflow calling `/api/process/`, rendering structured AI data or blocker cards dynamically.
- `intake/tests.py`: Added comprehensive `Phase3GeminiIntegrationTests` covering mocked Gemma 4 success, follow-up question generation, Gemini model rejection, rate limits, malformed JSON, and log privacy (21/21 tests passing).
- `phase.md`: Marked Phase 3 items complete.
- `memory.md`: Updated execution log.

### Verification & Test Results
- `python manage.py check`: **0 issues identified**.
- `python manage.py test`: **21/21 tests passed in 0.237s**:
  - Phase 1 tests (health check, JSON negotiation, Gemma 4 defaults, Gemini model rejection, startup without key)
  - Phase 2 tests (UI rendering, controls, validation success, input error handling)
  - Phase 3 tests:
    - `test_process_without_api_key_reports_honest_blocker` (Returns clean blocker when key missing)
    - `test_process_intake_success_with_mocked_gemma` (Extracts chief complaint, symptoms, timeline, follow-up questions)
    - `test_gemini_model_substitution_is_blocked` (Rejects `gemini-2.5-pro` substitution)
    - `test_follow_up_questions_generated_when_details_missing` (Parses targeted clarifying questions)
    - `test_empty_follow_up_questions_when_intake_complete` (No follow-up questions when information complete)
    - `test_handle_rate_limit_error` (Gracefully handles 429 quota exhaustion)
    - `test_handle_malformed_json_response` (Handles unparseable model output)
    - `test_handle_empty_gemma_response` (Handles empty response)
    - `test_no_patient_sensitive_data_in_logging` (Verifies logs do not contain patient text or API keys)
- Live dev server verified on `http://127.0.0.1:8000/` via curl:
  - `/health/` returns `{"status": "healthy", "phase": 3, "gemma": {"model": "gemma-4-31b-it", ...}}`
  - `POST /api/process/` without key returns `{"status": "blocked", "error_type": "missing_api_key", "requires_key": true}`.

---

## 5. Phase 4: Medical Report (Next Up)
- **Goal:** Organize structured symptoms, duration, medications, allergies, and medical history into a doctor-ready clinical report.
- **Key Tasks:**
  - Show missing, conflicting, or uncertain information clearly.
  - Allow patients to review and correct extracted details before doctor handoff.
  - Generate a clean, printable and downloadable medical summary.

---

## 6. Remaining Phases
- Phase 4: Medical Report
- Phase 5: Security and Testing
- Phase 6: Final Polish
- Phase 7: Demo and Buffer
