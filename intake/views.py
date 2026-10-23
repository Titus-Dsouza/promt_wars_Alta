from django.http import JsonResponse, HttpResponse
from django.conf import settings
from .gemma_service import get_gemma_status


def status_view(request):
    """
    Phase 1 Status and Setup Verification view.
    Confirms application is running and reports configuration status.
    """
    status_data = get_gemma_status()

    # If JSON requested, return clean JSON
    if request.headers.get('Accept') == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse({
            "project": "MediScribe",
            "phase": 1,
            "phase_name": "Setup & Configuration",
            "status": "ready",
            "debug": settings.DEBUG,
            "gemma": status_data,
        })

    # Return a clean, styled status page matching Design.md palette
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MediScribe — Phase 1 Setup</title>
    <style>
        :root {{
            --primary: #04021D;
            --background: #F7F8F5;
            --secondary: #435A58;
            --neutral: #9CA7A6;
            --accent: #7D6873;
            --card-bg: #FFFFFF;
            --border: #E5E8E5;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
            background-color: var(--background);
            color: var(--primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(4, 2, 29, 0.05);
            max-width: 580px;
            width: 100%;
            padding: 36px;
        }}
        .badge {{
            display: inline-block;
            background: #EAF0EE;
            color: var(--secondary);
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 999px;
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        h1 {{
            font-size: 26px;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 8px;
        }}
        p.subtitle {{
            color: var(--secondary);
            font-size: 15px;
            line-height: 1.5;
            margin-bottom: 24px;
        }}
        .status-grid {{
            background: var(--background);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 24px;
        }}
        .row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        .row:last-child {{
            border-bottom: none;
        }}
        .label {{
            font-weight: 600;
            color: var(--primary);
        }}
        .value {{
            color: var(--secondary);
            font-family: monospace;
            font-size: 13px;
        }}
        .active-pill {{
            background: #E7F3ED;
            color: #1F6B43;
            padding: 2px 8px;
            border-radius: 6px;
            font-weight: 600;
        }}
        .footer {{
            font-size: 12px;
            color: var(--neutral);
            text-align: center;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">Phase 1 Complete</span>
        <h1>MediScribe 🩺</h1>
        <p class="subtitle">From patient information to doctor-ready reports.</p>
        
        <div class="status-grid">
            <div class="row">
                <span class="label">Backend Server</span>
                <span class="value active-pill">Django Active</span>
            </div>
            <div class="row">
                <span class="label">Target AI Model</span>
                <span class="value">{status_data['model']}</span>
            </div>
            <div class="row">
                <span class="label">Model Architecture</span>
                <span class="value">Google Gemma 4 (Open Weights)</span>
            </div>
            <div class="row">
                <span class="label">API SDK</span>
                <span class="value">google-genai</span>
            </div>
            <div class="row">
                <span class="label">AI Access Status</span>
                <span class="value">{status_data['status']}</span>
            </div>
        </div>

        <p class="footer">Phase 1 Setup active &amp; ready for Phase 2 UI implementation.</p>
    </div>
</body>
</html>"""
    return HttpResponse(html)


def health_check(request):
    """Simple JSON health check endpoint."""
    return JsonResponse({
        "status": "healthy",
        "phase": 1,
        "gemma": get_gemma_status()
    })
