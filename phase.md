# MediScribe — Prompt Wars Phase Plan

## 1. Project objective

MediScribe is a patient-intake web app that converts messy real-world medical information into a clear, structured, reviewable summary that a patient can share with a doctor. The product reduces the friction of collecting symptoms, history, and context before a clinical appointment while preserving uncertainty, missing details, and the distinction between patient-reported facts and document-derived facts. It is designed to improve access to care and reduce administrative burden without replacing professional medical judgment.

The societal benefit is straightforward: patients arrive better prepared, doctors receive cleaner summaries, and critical context is less likely to be missed or lost in transcription.

## 2. MVP scope

### Essential features (in scope)
- New intake flow with a concise patient questionnaire covering:
  - basic demographics and visit reason
  - symptoms and duration
  - severity and triggers
  - current conditions, medications, allergies
  - relevant history and recent tests
  - free-text context from the patient
- Secure backend endpoint for Gemini requests
- Server-side prompt that instructs Gemini to:
  - extract structured data from messy input
  - ask relevant follow-up questions when information is missing or ambiguous
  - clearly identify patient-reported facts vs. document-derived facts
  - avoid inventing facts
  - return structured JSON consistent with a known schema
- Structured patient review page:
  - editable summary fields before final report generation
  - ability to correct incorrect or missing information
  - explicit indicators for uncertainty and missing data
- Final report generation with sections for:
  - symptoms summary
  - medical-history timeline (if available)
  - medications and allergies
  - relevant test results
  - missing information or uncertainties
- Print/download function for the final report
- Synthetic demo mode that works without live API access
- Accessibility basics for desktop/mobile and keyboard use
- Automated tests covering the main business logic and workflow

### Explicitly excluded from MVP
- Authentication or user accounts
- Real database persistence
- Multi-user doctor portal or admin dashboard
- Complex analytics or dashboards
- Detailed appointment scheduling
- File ingestion beyond optional simple text/document upload handling if time permits
- AI diagnosis or treatment recommendations
- Real clinical verification or medical decision support
- Long-term storage of sensitive health data
- Vague “chatbot” experience unrelated to structured intake

### Expected final demo
A clinician-facing demonstration where a patient enters rough, messy information such as “I’ve had a cough for 2 weeks, maybe worse at night, I take ibuprofen, and my dad had asthma,” then sees Gemini convert it into a structured summary, ask a few targeted follow-up questions, and present a final reviewable report that can be printed or downloaded. The demo is synthetic and uses non-sensitive fake patient records.

## 3. Architecture

### Recommended stack
This repository currently appears to be empty aside from a README, so the simplest reliable default is:
- Frontend: React + TypeScript + Vite
- Backend: Node.js + Express
- Gemini integration: server-side Google GenAI SDK (verify the currently supported SDK/model in official documentation at setup time)
- Validation: Zod or equivalent schema validation
- Testing: Vitest + React Testing Library + supertest (or equivalent lightweight setup)
- No database required for the MVP

This keeps the architecture small enough to finish inside five hours while preserving a secure server-side API boundary.

### Frontend design
- Single-page app with a clear multi-step flow:
  1. Start intake
  2. Enter symptoms and details
  3. Review AI extraction and answer follow-ups
  4. Review structured summary
  5. Generate final report
- Use semantic HTML, accessible labels, and visible focus states.
- Keep state in a controlled structure such as a single intake session object.
- Show loading, success, and error states clearly without relying on colour alone.
- Provide a simple print-friendly report view.

### Secure backend design
- Keep the Gemini API key in environment variables only.
- Expose a single server endpoint, for example `/api/intake/summary` or `/api/intake/report`.
- Validate all request bodies on the server.
- Reject oversized input, empty payloads, invalid shape, and unsupported file types if uploads are used.
- Strip or avoid returning internal API errors, stack traces, or sensitive data in frontend responses.
- Do not log patient details; log only request IDs and non-sensitive diagnostics.

### Gemini integration design
- Use a server-side prompt with explicit instructions:
  - never diagnose or prescribe
  - never invent facts
  - separate patient-reported information from document-derived information
  - preserve uncertainty and missing facts
  - return valid JSON only when confidence is sufficient
- Prefer a constrained JSON schema or strongly typed schema from the SDK where supported.
- Handle malformed or empty responses by returning a safe fallback error object and asking the user to review or edit the summary.
- If live API access fails, switch to a clearly labelled demo mode that uses synthetic data; explicitly state that the response is demo data, not a real Gemini response.

### Data flow
1. Patient enters intake data in frontend.
2. Frontend sends a validated payload to the backend.
3. Backend validates schema and environment variables.
4. Backend calls Gemini with a targeted prompt and a schema.
5. Gemini returns a structured JSON payload.
6. Backend sanitizes and validates the response.
7. Frontend renders the patient-review page and status indicators.
8. User modifies or approves the data.
9. Backend builds the final report from approved fields.
10. Frontend renders the printable final report.

### Report-generation flow
The final report should be produced from a structured object like:
- patientSummary
- symptoms
- timeline
- medications
- allergies
- tests
- missingInformation
- uncertainties
- sources

The final document should not present medical claims as fact if they were not sufficiently supported. It should surface available facts, unknowns, and sources in a readable format suitable for doctor review.

## 4. Implementation phases

### Phase 1 — Foundation and project setup (P0, 30 minutes)
Goal: Establish a working scaffold and constraints.

Tasks:
- Initialize project structure (Vite + React + TypeScript, Node/Express server)
- Add environment variable template (`.env.example`)
- Add basic folder structure: `src/`, `server/`, `tests/`, `docs/`
- Configure linting and test runner
- Document the run and build commands
- Confirm the supported Gemini SDK and model in official documentation before coding the integration

Dependencies:
- Need repo state confirmed as empty and minimal

Definition of done:
- `npm install` and startup commands work
- app boots in local dev mode
- API key placeholder is documented and not committed

### Phase 2 — Intake form and validation (P0, 45 minutes)
Goal: Build the patient intake experience and the data schema.

Tasks:
- Create the intake form with sections for symptoms, onset, severity, history, medications, allergies, and free-text notes
- Add validation rules for required fields and reasonable length limits
- Add accessible labels and error messaging
- Keep all data in a structured session object
- Ensure empty/invalid submissions cannot be sent

Dependencies:
- Phase 1 setup

Definition of done:
- User can complete a mock intake in a single flow without console errors
- Invalid or empty inputs are blocked with clear messages
- Payload matches the backend schema before submission

### Phase 3 — Secure backend and data contract (P0, 45 minutes)
Goal: Build the server-side boundary and ensure security requirements are met.

Tasks:
- Create `/api/intake` or similar endpoint
- Validate request shape and reject empty input
- Enforce payload size and content rules
- Add safe error handling and no-sensitive-data logging
- Implement a typed JSON response contract for Gemini and fallback paths
- Add a demo-mode route or branch for when the API key is unavailable

Dependencies:
- Phase 2 form shape

Definition of done:
- Backend rejects malformed payloads
- No API key is present in frontend or repo
- Server returns sanitized errors only
- Demo mode can be triggered without a valid API key

### Phase 4 — Gemini extraction and follow-up logic (P0, 60 minutes)
Goal: Make the AI useful and safe.

Tasks:
- Write a narrow, structured prompt for symptom/history extraction
- Add schema for extracted fields: symptoms, duration, medications, allergies, conditions, timeline, uncertainties, missing information, evidence source
- Implement server-side call to Gemini
- Parse and validate the model response
- If Gemini output is malformed or empty, return a safe fallback result and trigger review mode instead of fabricated data
- Add a lightweight follow-up question generator that asks only the missing or ambiguous items

Dependencies:
- Phase 3 backend contract

Definition of done:
- Valid responses are structured JSON
- Invalid responses are handled safely
- Missing data is surfaced instead of guessed
- Follow-up prompts are specific and relevant

### Phase 5 — Review and summary UI (P0, 75 minutes)
Goal: Make the result reviewable and useful to the patient.

Tasks:
- Render a patient review screen with editable fields
- Allow edits for symptoms, conditions, meds, allergies, notes, and timeline entries
- Show source labels: patient-reported, document-derived, or unknown
- Show “uncertainty” and “missing information” blocks distinctly
- Provide a clear “Generate final report” action
- Add a “back” flow so users can correct the data before finalisation

Dependencies:
- Phase 4 extracted structure

Definition of done:
- The user can correct extracted data before final report generation
- Uncertain or missing facts remain visible and are not silently removed
- The generated summary includes a patient-review step

### Phase 6 — Final report generation and print/download (P0, 45 minutes)
Goal: Produce a final doctor-shareable document.

Tasks:
- Generate a final report with sections for summary, timeline, medications, allergies, tests, missing info, and uncertainties
- Ensure the content is plain-language and medically careful
- Add a print-friendly layout and download/export action
- Keep the final output free of diagnosis/treatment guidance
- Add a banner clarifying that this is a patient summary and not medical advice

Dependencies:
- Phase 5 review step

Definition of done:
- Final report is clearly structured and readable
- Report can be printed or downloaded
- The output excludes any diagnosis or prescription content

### Phase 7 — Testing, accessibility, and demo polish (P0, 45 minutes)
Goal: Make the app credible and testable.

Tasks:
- Write automated tests for:
  - empty submission
  - missing required fields
  - malformed Gemini response
  - API failure fallback
  - patient review workflow
  - final report generation
- Verify focus states and keyboard behavior
- Check contrast and mobile responsiveness
- Add demo data and a synthetic demo mode path
- Prepare the final demo script

Dependencies:
- Earlier phases

Definition of done:
- Test runner executes successfully
- No critical accessibility issues are obvious in the main workflow
- Demo data can be used to run the app without live credentials

### Phase 8 — Contingency buffer and final verification (P1, 30 minutes)
Goal: Protect the demo and keep a realistic buffer.

Tasks:
- Run smoke tests on the full flow
- Verify no secret keys are exposed
- Confirm all core workflow steps work end-to-end
- Remove unused code, debug logs, and placeholder content
- Final presentation rehearsal

Dependencies:
- All prior phases

Definition of done:
- App can be demonstrated reliably in under 10 minutes
- Known risks have been mitigated or intentionally cut

### Time allocation summary
- Total planned build time: ~5 hours 15 minutes including buffer
- P0 work: core app, secure backend, Gemini integration, testing, accessibility, end-to-end flow
- P1 work: final polish and verification only
- P2 work: optional extras such as extra file upload support or richer UI effects are deferred or removed if needed

## 5. Acceptance criteria

### Phase 1 acceptance
- project boots locally
- required tooling is installed
- env variables and instructions are documented

### Phase 2 acceptance
- intake form is usable and validates correctly
- all required fields are captured and structured

### Phase 3 acceptance
- backend endpoint is secure and validated
- no API key leakage and sensible error handling

### Phase 4 acceptance
- Gemini call returns structured data with sources and uncertainty markers
- malformed responses are blocked safely

### Phase 5 acceptance
- patient can review and correct AI-generated summary before finalisation
- patient-reported information and uncertainty remain visible

### Phase 6 acceptance
- readable final report is generated and printable/downloadable
- report excludes diagnosis or treatment recommendations

### Phase 7 acceptance
- tests cover the critical workflow and edge cases
- app works with demo data without live API access

### Phase 8 acceptance
- application is stable enough for demo
- final risk review completed and changes documented

## 6. Evaluation checklist

Use this as the final submission checklist against the seven judging categories.

- [ ] A. Code quality: clear separation of responsibilities, reusable components, and understandable code structure
- [ ] B. Security: no Gemini key in frontend or repo; all calls go through the backend; input validation and safe errors implemented
- [ ] C. Efficiency: minimal redundant API calls; concise prompts; loading indicators; no unnecessary infrastructure
- [ ] D. Testing: important logic and edge cases tested; repeatable test commands documented
- [ ] E. Accessibility: semantic form controls, keyboard support, visible focus states, contrast, mobile responsiveness
- [ ] F. Problem statement alignment: app transforms messy intake into structured summary; retains source and uncertainty; doctor review is central
- [ ] G. Google services usage: real Gemini integration used for a meaningful task; secure credentials; demo fallback clearly labelled

## 7. Testing plan

### Unit tests
- validate intake form schema with required vs optional fields
- reject empty payloads and invalid durations or values
- ensure medication/allergy parsing handles missing or unknown inputs safely
- test fallback logic when Gemini returns malformed JSON
- test final report generation for missing and uncertain data

### Integration tests
- start intake, submit payload, receive structured result from backend
- assert the server returns a sanitised error instead of stack trace on API failure
- assert “demo mode” works when the API key is absent
- verify patient review workflow can accept and modify generated data
- verify final report is produced from approved values only

### Example test scenarios
- valid case: complete intake with symptoms, meds, allergies, and free text
- missing case: symptom duration absent, follow-up question requested
- invalid case: malformed input payload or unsupported content
- malformed model case: Gemini returns invalid JSON or empty fields
- API failure case: network error or 429/500 response
- empty submission case: empty form, no summary

### Test execution instructions
- Use a standard local script such as:
  - `npm install`
  - `npm run test`
  - `npm run build`
- Document the exact command set in the repo README or project setup file
- Ensure tests can be run in CI or locally without real patient data

### Expected outcomes
- All critical validation and workflow tests pass
- Failed Gemini requests do not fabricate medical information
- The app continues in a safe degraded mode instead of crashing

## 8. Security and medical-safety checklist

- [ ] Gemini API key is stored only in server environment variables and not in the source repo
- [ ] Frontend never contains secret keys or server-side configuration
- [ ] All inbound payloads are validated and constrained on the backend
- [ ] Input size and file type limits are enforced if uploads are supported
- [ ] Errors are sanitized and do not expose tokens, stack traces, or health details to the client
- [ ] No patient details are logged to the console or persisted in plain text logging
- [ ] The app does not diagnose, prescribe, or recommend treatment
- [ ] Missing facts remain missing and are labelled as such
- [ ] Uncertainties and conflicting information are preserved in the output rather than flattened
- [ ] The summary clearly distinguishes patient-reported information from document-derived information
- [ ] Synthetic data is used for all demos and screenshots
- [ ] The app states that it is a patient intake support tool and not a substitute for professional care

## 9. Demo plan

Use fully synthetic patient data for the demonstration.

1. Open the app and click “Start new intake”.
2. Enter a messy patient narrative such as:
   - “I’ve had chest tightness for 3 days, not sure if it is stress or my asthma.”
   - “I’m still taking ibuprofen and my mum has high blood pressure.”
3. Submit the intake.
4. Show the AI-generated extraction summary, highlighting structured fields and a follow-up question for missing details such as medication timing or allergies.
5. Review the structured summary and correct an incorrect field.
6. Generate the final report.
7. Show the downloadable/printable report including symptoms, timeline, medications, allergies, missing information, and uncertainty notes.
8. Explain that the report is a clean doctor-facing summary, not a diagnosis or treatment plan.

## 10. Fallback plan

If time is running short, preserve the essential core workflow and security before expanding features.

Cut in this order:
1. Remove nonessential extras such as advanced styling, animations, or optional upload fields
2. Simplify the UI to a single-page workflow without decorative dashboard elements
3. Reduce Gemini prompt complexity while keeping the schema and guardrails intact
4. Drop optional report sections such as broad timeline visuals or richer export options
5. Use demo data mode as the fallback when live API access fails
6. Delay polishing and accessibility refinements only after the main workflow works

Do not cut:
- secure server-side API boundary
- schema validation
- no-diagnosis guardrails
- missing-data handling
- final patient review step
- fallback safety logic

## 11. Definition of done

The project is not done until all of the following are true:

- [ ] The app starts locally with documented setup instructions
- [ ] The patient intake flow works end-to-end
- [ ] A secure backend is used for all Gemini calls
- [ ] Output is structured, reviewable, and editable by the patient
- [ ] Final report can be printed or downloaded
- [ ] Missing, uncertain, or conflicting information is preserved in the output
- [ ] Demo mode works with synthetic data when the API is absent
- [ ] No real patient data or secrets are used in the project
- [ ] Security checks and no-diagnosis boundaries are enforced
- [ ] Tests cover the key risks: empty input, malformed model response, API failure, and review flow
- [ ] Accessibility basics are present on the main flow
- [ ] Final demo is rehearsed and can be explained clearly in a few minutes

## 12. Progress tracking

- [ ] Inspect repository and confirm current tooling baseline
- [ ] Initialize project scaffold and required configuration
- [ ] Build intake form and validation schema
- [ ] Implement secure backend endpoint and error handling
- [ ] Integrate Gemini with structured prompt and output schema
- [ ] Add review/edit workflow and uncertainty handling
- [ ] Implement final report generation and print/export
- [ ] Add automated tests for critical paths
- [ ] Run accessibility and responsiveness checks
- [ ] Prepare demo mode and synthetic example data
- [ ] Run final smoke test and submission review

## Notes for the coding agent

- Keep the implementation small and high-value. The project should feel polished but not over-engineered.
- Do not build a generic chatbot. The product must clearly centre on a structured medical-history intake and doctor-review workflow.
- Keep the system honest: when information is missing, say so. Avoid guessing or pretending the AI has certainty it does not have.
- Default to a minimal MVP architecture unless a clear and time-safe improvement is needed.
- Assume the code must be demonstrable in a hackathon environment with minimal setup and no database dependency.

This plan is designed to fit the nine-thirty-to-two-thirty build window while leaving enough time for final verification and a clear end-to-end demo.
