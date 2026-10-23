# MediScribe — Frontend

The `frontend/` directory contains the client-side presentation layer for MediScribe, built with modern semantic HTML5, CSS3, and responsive vanilla JavaScript without heavy frameworks.

## Directory Structure
```text
frontend/
├── index.html       # Primary clinical intake interface & AI summary view
├── css/
│   └── styles.css   # MediScribe design system (One Medical aesthetic & Dribbble palette)
├── js/
│   └── intake.js    # Multi-step intake wizard, keyboard navigation, and API bridge
└── README.md        # Frontend documentation
```

## Design Palette
- **Primary:** `#04021D` — Deep midnight navy
- **Background:** `#F7F8F5` — Soft off-white
- **Secondary:** `#435A58` — Muted deep teal
- **Neutral:** `#9CA7A6` — Sage grey
- **Accent:** `#7D6873` — Muted mauve
- **Cards:** `#FFFFFF` with 14–18px border radius
- **Borders:** `#E5E8E5`

## Key Capabilities
- **Hero & Landing:** Patient intake overview, 3-step guide, and medical safety disclaimers.
- **Progressive Intake Wizard:** 4-step intake process covering symptoms, duration/severity, medical history, medications, allergies, and step-by-step validation.
- **Accessible Controls:** Keyboard card toggling (`Space` / `Enter`), high-contrast focus rings, and screen-reader ARIA landmarks.
- **Dynamic AI Integration:** Communicates with the Django backend (`/api/validate/` and `/api/process/`) to retrieve source-grounded Google Gemini 3.8 Flash summaries.

## How to Run
1. **Integrated with Django Backend (Recommended):**
   When the Django backend is running at `http://127.0.0.1:8000/`, it serves this frontend directly on the root URL.
2. **Standalone Frontend Server (Optional):**
   ```bash
   cd frontend
   python3 -m http.server 3000
   ```
   Open `http://localhost:3000/` in your browser. The client-side script automatically targets the backend at `http://127.0.0.1:8000`.
