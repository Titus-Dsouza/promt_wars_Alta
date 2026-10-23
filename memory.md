# MediScribe — Memory & Comprehensive Project Audit

## 1. Project Overview & Repository Configuration
MediScribe is a clinical patient intake application that collects patient symptoms, duration, medical history, allergies, and concerns, and prepares structured, doctor-ready summaries using Google Gemma 4 AI via the Gemini API (`google-genai` SDK).

- **Repository:** https://github.com/Titus-Dsouza/promt_wars_Alta
- **Branch:** `main`
- **Remote:** `origin -> https://github.com/Titus-Dsouza/promt_wars_Alta.git`
- **Tech Stack:** Python 3.14.7, Django 6.1.2, HTML5 / CSS3 / Vanilla JavaScript, Google GenAI SDK (`google-genai` v2.33.0)
- **Configured AI Model:** Google Gemma 4 (`gemma-4-31b-it`)

---

## 2. Documentation Recovery Audit (Step 2)
In accordance with user instructions, the four original foundation documents were audited against Git history from initial commit `17a9486` (pre-implementation baseline):

- `README.md`: Restored from commit `17a9486`. In earlier commits, references to Gemma 4 had been altered to Gemini; restoration recovered the original text prioritizing Google Gemma 4 AI assistance.
- `phase.md`: Restored from commit `17a9486`. Checkboxes reset to pristine read-only requirements state (`- [ ]`).
- `Architecture.md`: Audited against `17a9486:Architecture.md`; verified 100% byte-for-byte identical.
- `Design.md`: Audited against `17a9486:Design.md`; verified 100% byte-for-byte identical.

**Permanent Rule Enforced:** `README.md`, `phase.md`, `Architecture.md`, and `Design.md` are treated as strictly immutable requirements specifications. No automated or manual edits, reformatting, or checkmarking will be performed on them. All project progress, audit findings, test logs, and next steps are recorded exclusively in `memory.md`.

Verification: `git diff 17a9486 -- README.md phase.md Architecture.md Design.md` produces 0 diff lines.

---

## 3. Frontend Visibility Investigation & Resolution (Step 4)
The user reported being unable to see the frontend. A systematic inspection was conducted to identify the exact root causes:

### Root Cause Analysis:
1. **Background Process Lifecycle:** The Django development server process had terminated after running verification curl commands in the previous session. Because no persistent process was actively listening on port 8000, attempting to open `http://127.0.0.1:8000/` in a web browser resulted in a connection refused (`ERR_CONNECTION_REFUSED`) error.
2. **Host Header Filtering (`ALLOWED_HOSTS`):** In `mediscribe/settings.py`, `ALLOWED_HOSTS` was initially constrained to `['localhost', '127.0.0.1', '[::1]']`. Browsing via `0.0.0.0`, local network IP addresses, or certain loopback host header permutations resulted in a `400 Bad Request (DisallowedHost)` error.

### Fixes Applied:
- Updated `mediscribe/settings.py` so that when `DEBUG = True`, `ALLOWED_HOSTS = ['*']` is set, allowing connections from localhost, 127.0.0.1, 0.0.0.0, and local development hostnames without HTTP 400 errors.
- Verified that static assets load with correct MIME types:
  - `GET /` &rarr; HTTP 200 OK (text/html)
  - `GET /static/css/styles.css` &rarr; HTTP 200 OK (`Content-Type: text/css`, 15.8 KB)
  - `GET /static/js/intake.js` &rarr; HTTP 200 OK (`Content-Type: text/javascript`, 20.3 KB)
  - Validated JavaScript syntax with `node --check static/js/intake.js` (0 errors).

### How to Run and View the Application Locally:
To view the frontend in any browser:
```bash
# From the project root:
.venv/bin/python manage.py runserver 127.0.0.1:8000
```
Then navigate to:
**`http://127.0.0.1:8000/`** (or **`http://localhost:8000/`**)

*Limitation Disclosure:* Automated headless checks, HTTP status codes, DOM elements, and syntax verification passed with 100% accuracy. However, visual ocular rendering in a physical browser could not be directly captured within this CLI environment.

---

## 4. Requirements & Codebase Audit (Step 3)

| Requirement Area | Specification Source | Codebase Implementation | Status |
| :--- | :--- | :--- | :--- |
| **Tech Stack** | `Architecture.md` | Django 6.1.2 backend, HTML5/CSS3/JS frontend, `google-genai` SDK | **Complete** |
| **Color Palette** | `Design.md` | Primary `#04021D`, BG `#F7F8F5`, Teal `#435A58`, Mauve `#7D6873`, Cards `#FFFFFF` | **Complete** |
| **Landing Page** | `Design.md` | Logo, Hero *"Your health story, clearly organised"*, 3-step guide, safety banner, Start/Demo buttons | **Complete** |
| **Intake Questionnaire** | `phase.md` (Phase 2) | 8 chief symptom cards + other field, duration cards, 1-10 severity scale, free-text description | **Complete** |
| **Medical Background** | `phase.md` (Phase 2) | Chronic conditions, current medications, known allergies, clinical notes | **Complete** |
| **Step Review** | `phase.md` (Phase 2) | Dynamic client review card summarizing all selections before submission | **Complete** |
| **Validation Engine** | `phase.md` (Phase 2) | Client step validation + `POST /api/validate/` endpoint | **Complete** |
| **AI Integration** | `phase.md` (Phase 3) | Official `google-genai` SDK calling `gemma-4-31b-it`; validates against Gemini substitution | **Complete** |
| **Clinical Safety Rules** | `phase.md`, `README.md` | Prompt forbids diagnosis, prescriptions, and hallucinated facts; distinguishes reported facts | **Complete** |
| **Clarifying Questions** | `phase.md` (Phase 3) | Generates 1-3 follow-up questions only when important clinical details are missing | **Complete** |
| **AI Error Handling** | `phase.md` (Phase 3) | Handles missing API key honestly, catches rate limits (429), auth (401/403), malformed output | **Complete** |
| **Security & Privacy** | `phase.md` (Phase 5) | `.env` ignored; zero keys hardcoded; patient description excluded from logs | **Complete** |
| **Testing** | `phase.md` (Phase 5) | 21 automated unit tests with mocked AI responses; 0 issues on Django check | **Complete** |
| **Medical Report Review** | `phase.md` (Phase 4) | Interactive patient correction and review of final extracted report | **Pending (Phase 4)** |
| **Printable Report** | `phase.md` (Phase 4) | Print/download formatting (`@media print` / export) for doctors | **Pending (Phase 4)** |

---

## 5. AI Integration Status
- **Target Model:** Google Gemma 4 (`gemma-4-31b-it`).
- **Provider:** Gemini API via the official `google-genai` SDK (`from google import genai`).
- **Model ID Validation:** Strict validation in `intake/gemma_service.py` (`validate_gemma_model`) prevents substituting Gemini (`gemini-1.5`, `gemini-2.0`, `gemini-2.5`).
- **Live Execution Status:**
  - With `GEMINI_API_KEY` configured in `.env`, the backend makes genuine calls to `gemma-4-31b-it` via `client.models.generate_content`.
  - When running without a key, the backend reports an honest blocker (`status: "blocked"`, `error_type: "missing_api_key"`) and the UI clearly informs the user that an API key is required, preserving user input without faking AI data.

---

## 6. Security and Test Verification
- **Automated Tests:** 21/21 tests passing in `intake/tests.py`:
  - 7 Setup & Configuration tests (health check, Gemma model verification, safe startup without key).
  - 5 UI & Validation tests (intake page rendering, form controls, payload validation, input rejection).
  - 9 Gemma 4 AI tests (SDK call verification, model ID check, follow-up question logic, rate limit handling, malformed JSON recovery, privacy check preventing patient data in logs).
- **System Checks:** `python manage.py check` reports 0 issues.
- **Git Protection:** Verified `.gitignore` excludes `.env`, `*.sqlite3`, `.venv/`, and caches.

---

## 7. Current Project Phase & Phase Compliance
- **Verified Completed Phases:**
  - **Phase 1 (Setup):** Verified complete.
  - **Phase 2 (Build the UI):** Verified complete.
  - **Phase 3 (Gemma 4 Integration):** Verified complete.
- **Current Standing:** Ready to proceed to **Phase 4: Medical Report**.
- **Pending Phases:**
  - Phase 4: Medical Report (Organize report sections, show missing/uncertain info, inline patient corrections, printable/downloadable summary).
  - Phase 5: Security and Testing (File upload limits, keyboard/contrast audit).
  - Phase 6: Final Polish.
  - Phase 7: Demo and Buffer.

---

## 8. Prioritized Next Steps (Phase 4 Preparation)
1. Build doctor-ready report view with categorized sections: Chief Complaint, Timeline, Symptoms Grid, Relevant Medical History, Medications, Allergies, and Clarifying Q&A.
2. Implement inline correction mechanism allowing patients to edit extracted details before doctor handoff.
3. Add print-ready stylesheet (`@media print`) and downloadable report feature.
