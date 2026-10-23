# MediScribe — Architecture

## 1. Overview
MediScribe transforms patient symptoms and medical history into structured reports using **Google Gemma 4 AI**.

## 2. Tech Stack
- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python with Django
- **AI:** Google Gemini Flash via the Gemini API
- **Reports:** Printable and downloadable medical summaries

## 3. Workflow
1. Patient enters symptoms and medical history.
2. Frontend sends information to the Django backend.
3. Backend securely sends the input to Gemma 4.
4. AI organises the information into structured data.
5. Backend validates the response.
6. Patient reviews and downloads the report for their doctor.

## 4. Security
- Store API keys in environment variables.
- Never expose secrets in frontend code.
- Validate inputs and handle API errors.
- Use synthetic patient data for demonstrations.

## 5. Safety
MediScribe organises medical information but does not diagnose diseases or prescribe treatments. Reports must be reviewed by a qualified healthcare professional.

## 6. Google Services
Use Google's Gemini API to access a supported Gemma 4 model. Verify API access and model availability before the demo.
