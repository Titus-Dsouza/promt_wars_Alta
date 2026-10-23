# MediScribe — Implementation Phases

## Phase 1: Setup (9:30–9:50 AM)
- [ ] Inspect the existing project and files.
- [ ] Set up dependencies and project structure.
- [ ] Configure Gemini API securely using environment variables.

**Done when:** The application runs and the configuration is ready.

## Phase 2: Build the UI (9:50–10:35 AM)
- [ ] Create a clean, modern, responsive interface.
- [ ] Add patient intake forms and multiple-choice symptom questions.
- [ ] Add a free-text field for describing medical concerns.
- [ ] Add loading, error, and success states.

**Done when:** The patient can complete the intake form on desktop and mobile.

## Phase 3: Gemini Integration (10:35–11:25 AM)
- [ ] Connect Gemini through a secure backend.
- [ ] Process patient answers and medical-history text.
- [ ] Generate relevant follow-up questions.
- [ ] Validate Gemini responses and handle API failures.

**Done when:** Gemini converts patient input into structured information.

## Phase 4: Medical Report (11:25 AM–12:10 PM)
- [ ] Organise symptoms, duration, medications, allergies, and medical history.
- [ ] Show missing, conflicting, or uncertain information.
- [ ] Allow patients to review and correct extracted details.
- [ ] Generate a printable or downloadable report.

**Done when:** The patient can review and export a structured report for a doctor.

## Phase 5: Security and Testing (12:10–12:50 PM)
- [ ] Keep API keys out of frontend code and Git.
- [ ] Validate user input and restrict uploaded file types and sizes.
- [ ] Test valid, empty, and invalid submissions.
- [ ] Test Gemini errors and malformed responses.
- [ ] Check keyboard navigation, labels, contrast, and mobile layout.

**Done when:** Core tests pass and unsafe or failed requests are handled properly.

## Phase 6: Final Polish (12:50–1:40 PM)
- [ ] Fix bugs and improve visual consistency.
- [ ] Remove unnecessary code and dependencies.
- [ ] Verify the full workflow from intake to report.
- [ ] Confirm all seven judging criteria are addressed.

**Done when:** The complete application works reliably and is ready to demonstrate.

## Phase 7: Demo and Buffer (1:40–2:30 PM)
- [ ] Test the application from start to finish.
- [ ] Prepare synthetic patient data for the demonstration.
- [ ] Verify the Gemini integration or clearly labelled demo fallback.
- [ ] Prepare a short presentation explaining the societal benefit.
- [ ] Keep time available for last-minute fixes.

**Done when:** The application is demonstrable by 2:30 PM.

## Important Rules
- Never diagnose diseases or prescribe treatment.
- Never invent missing medical information.
- Clearly label uncertainty and distinguish patient-reported facts from extracted information.
- Protect sensitive data and never expose API keys.
- Never claim tests have passed unless they have been run.
- Prioritise a working end-to-end application over optional features.
