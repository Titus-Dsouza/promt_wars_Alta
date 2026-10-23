# MediScribe — Design Guide

## 1. Design Direction
Create a clean, premium healthcare website inspired by One Medical's simplicity and modern Dribbble healthcare dashboards. Keep the interface minimal, calm, professional, and easy to navigate.

## 2. Colour Palette

- **Primary:** `#04021D` — Deep midnight navy
- **Background:** `#F7F8F5` — Soft off-white
- **Secondary:** `#435A58` — Muted deep teal
- **Neutral:** `#9CA7A6` — Sage grey
- **Accent:** `#7D6873` — Muted mauve
- **Cards:** `#FFFFFF`
- **Borders:** `#E5E8E5`
- **Success:** `#435A58`
- **Warning:** `#A66A35`

Use navy for headings and important buttons, off-white for the main background, and mauve sparingly for secondary highlights.

## 3. Typography
Use Inter or a clean system font. Use bold, clear headings, readable body text, and comfortable spacing.

## 4. Landing Page
- Minimal navigation with the MediScribe logo.
- Hero heading: **"Your health story, clearly organised."**
- Short explanation of how MediScribe prepares medical information for doctors.
- Primary button: "Start Patient Intake"
- Secondary button: "Try Demo"
- Three-step section: Share Information → AI Organises It → Review Your Report.
- Small privacy and medical-safety section.

## 5. Patient Intake
- Display one question or a small group of related questions at a time.
- Show a clear progress indicator.
- Use rounded multiple-choice cards.
- Include a text area for describing symptoms.
- Allow medical history entry and document uploads.
- Provide clear Back and Continue buttons.

## 6. AI Processing
- Show a subtle loading animation.
- Display a message explaining that information is being organised.
- Handle API failures with clear error messages.
- Never present mock results as genuine AI output.

## 7. Medical Report
- Show report title and generation date.
- Organise symptoms, medications, allergies, medical history, and available test results into sections.
- Include a timeline when dates are available.
- Clearly mark missing, conflicting, or uncertain information.
- Identify whether information came from patient answers or documents.
- Allow corrections before printing or downloading.

## 8. UI Components
- Rounded cards with 14–18px corner radii.
- Subtle borders and soft shadows.
- Consistent buttons, icons, and spacing.
- Restrained animations and smooth transitions.
- Responsive layouts for desktop and mobile.
- Use navy for primary actions and mauve only for subtle accents.

## 9. Accessibility
- Use semantic HTML and labelled inputs.
- Ensure keyboard navigation and visible focus states.
- Maintain readable contrast and font sizes.
- Provide clear validation, loading, success, and error messages.
- Never rely on colour alone to communicate warnings.

## 10. Final Design Principle
Keep the website as clean as One Medical, with the richer navy and muted colours of a modern Dribbble healthcare dashboard. Prioritise trust, clarity, accessibility, and a smooth journey from patient intake to doctor-ready report.
