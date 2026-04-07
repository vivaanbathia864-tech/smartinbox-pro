from __future__ import annotations

"""FastAPI application entrypoint for SmartInbox-Pro."""

import os
from pathlib import Path

try:
    import gradio as gr
    from openenv.core.env_server import web_interface as openenv_web_interface
    from openenv.core.env_server.http_server import create_app
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "openenv-core is required for the web interface. Install project dependencies first."
    ) from exc

from fastapi.responses import HTMLResponse

try:
    from ..models import SmartInboxProAction, SmartInboxProObservation
    from .smartinbox_pro_environment import SmartInboxProEnvironment
except ImportError:
    from models import SmartInboxProAction, SmartInboxProObservation
    from server.smartinbox_pro_environment import SmartInboxProEnvironment

README_PATH = Path(__file__).resolve().parent.parent / "README.md"
os.environ.setdefault("ENV_README_PATH", str(README_PATH))

CUSTOM_GRADIO_THEME = gr.themes.Soft(
    primary_hue=gr.themes.colors.blue,
    secondary_hue=gr.themes.colors.cyan,
    neutral_hue=gr.themes.colors.slate,
    font=[
        "IBM Plex Sans",
        "Segoe UI",
        "Helvetica",
        "Arial",
        "sans-serif",
    ],
    font_mono=[
        "JetBrains Mono",
        "Cascadia Code",
        "Consolas",
        "monospace",
    ],
).set(
    body_background_fill="#07111f",
    background_fill_primary="#0d182b",
    background_fill_secondary="#13213a",
    block_background_fill="#0f1b30",
    block_border_color="#294363",
    block_label_text_color="#a9bdd7",
    block_title_text_color="#eff6ff",
    border_color_primary="#294363",
    input_background_fill="#081121",
    input_border_color="#315072",
    button_primary_background_fill="#0ea5e9",
    button_primary_background_fill_hover="#0284c7",
    button_primary_text_color="#eff6ff",
    button_secondary_background_fill="#16243c",
    button_secondary_background_fill_hover="#1e3252",
    button_secondary_text_color="#eff6ff",
    button_secondary_border_color="#315072",
)

CUSTOM_GRADIO_CSS = """
body {
    background:
        radial-gradient(circle at top left, rgba(34, 211, 238, 0.16), transparent 24%),
        radial-gradient(circle at bottom right, rgba(59, 130, 246, 0.20), transparent 28%),
        #07111f !important;
}
.gradio-container {
    background: transparent !important;
}
.gradio-container .main,
.gradio-container .contain {
    max-width: 1380px !important;
    margin: 0 auto !important;
}
.col-left,
.col-right {
    padding: 20px !important;
}
.col-left {
    border-right: 1px solid rgba(120, 153, 191, 0.18) !important;
}
.gradio-container .block,
.gradio-container .gr-group,
.gradio-container .gr-accordion,
.gradio-container .gr-box,
.gradio-container .gr-form,
.gradio-container .gr-code,
.gradio-container .gr-markdown,
.gradio-container .gr-chatbot,
.gradio-container .gr-dataframe {
    border-radius: 18px !important;
    border: 1px solid rgba(120, 153, 191, 0.22) !important;
    box-shadow: 0 18px 42px rgba(0, 0, 0, 0.24) !important;
}
.gradio-container .gr-group,
.gradio-container .gr-box,
.gradio-container .gr-form,
.gradio-container .gr-code {
    background: linear-gradient(180deg, rgba(16, 27, 47, 0.98), rgba(10, 19, 35, 0.98)) !important;
}
.gradio-container .gr-button-primary,
.gradio-container .gr-button-secondary {
    border-radius: 14px !important;
    font-weight: 700 !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease !important;
}
.gradio-container .gr-button-primary:hover,
.gradio-container .gr-button-secondary:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 24px rgba(14, 165, 233, 0.18) !important;
}
.gradio-container .gr-button-primary {
    background: linear-gradient(135deg, #2563eb, #06b6d4) !important;
    border: none !important;
}
.gradio-container .gr-button-secondary {
    background: rgba(20, 34, 57, 0.96) !important;
}
.gradio-container textarea,
.gradio-container input,
.gradio-container select {
    border-radius: 14px !important;
}
.gradio-container .prose,
.gradio-container .markdown-text,
.gradio-container .md,
.gradio-container .prose > *,
.gradio-container .markdown-text > * {
    background: transparent !important;
}
.gradio-container h1,
.gradio-container h2,
.gradio-container h3 {
    letter-spacing: -0.03em;
}
.gradio-container .gr-code textarea,
.gradio-container .gr-code pre {
    font-size: 13px !important;
}
footer {
    display: none !important;
}
"""

openenv_web_interface.OPENENV_GRADIO_THEME = CUSTOM_GRADIO_THEME
openenv_web_interface.OPENENV_GRADIO_CSS = CUSTOM_GRADIO_CSS


app = create_app(
    SmartInboxProEnvironment,
    SmartInboxProAction,
    SmartInboxProObservation,
    env_name="smartinbox_pro",
    max_concurrent_envs=4,
)

app.title = "SmartInbox-Pro API"
app.description = """
# SmartInbox-Pro API

Clean HTTP interface for the SmartInbox-Pro OpenEnv deployment.

## What You Can Do

* Start a fresh episode with `/reset`
* Classify the current email with `/step`
* Inspect live environment memory with `/state`
* Verify the deployment quickly with `/health`

## Labels

* `0` = spam
* `1` = normal
* `2` = urgent

## Notes

The interactive playground is available at `/web`.
"""
app.swagger_ui_parameters = {
    "defaultModelsExpandDepth": -1,
    "displayRequestDuration": True,
    "docExpansion": "none",
    "filter": True,
    "syntaxHighlight.theme": "obsidian",
    "tryItOutEnabled": True,
}


@app.get("/", include_in_schema=False)
def root() -> HTMLResponse:
    """Serve a lightweight landing page that behaves well inside the HF iframe."""
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>SmartInbox-Pro</title>
          <style>
            :root {
              color-scheme: dark;
              --bg: #0b1220;
              --panel: #111827;
              --panel-2: #172033;
              --text: #f3f4f6;
              --muted: #cbd5e1;
              --blue: #60a5fa;
              --green: #34d399;
              --border: rgba(148, 163, 184, 0.25);
            }
            * { box-sizing: border-box; }
            body {
              margin: 0;
              font-family: Arial, Helvetica, sans-serif;
              background:
                radial-gradient(circle at top right, rgba(96, 165, 250, 0.25), transparent 30%),
                radial-gradient(circle at bottom left, rgba(52, 211, 153, 0.18), transparent 28%),
                var(--bg);
              color: var(--text);
              min-height: 100vh;
              display: grid;
              place-items: center;
              padding: 24px;
            }
            .card {
              width: min(760px, 100%);
              background: linear-gradient(180deg, var(--panel-2), var(--panel));
              border: 1px solid var(--border);
              border-radius: 20px;
              padding: 28px;
              box-shadow: 0 30px 60px rgba(0, 0, 0, 0.35);
            }
            h1 {
              margin: 0 0 10px;
              font-size: clamp(28px, 5vw, 42px);
              line-height: 1.05;
            }
            p {
              margin: 0 0 14px;
              color: var(--muted);
              line-height: 1.6;
              font-size: 16px;
            }
            .badge {
              display: inline-block;
              margin-bottom: 14px;
              padding: 6px 10px;
              border-radius: 999px;
              background: rgba(96, 165, 250, 0.16);
              color: var(--blue);
              font-size: 13px;
              font-weight: 700;
              letter-spacing: 0.04em;
              text-transform: uppercase;
            }
            .actions {
              display: flex;
              flex-wrap: wrap;
              gap: 12px;
              margin: 22px 0 18px;
            }
            .btn {
              display: inline-block;
              text-decoration: none;
              padding: 12px 18px;
              border-radius: 12px;
              font-weight: 700;
              border: 1px solid var(--border);
            }
            .btn-primary {
              background: linear-gradient(135deg, #2563eb, #14b8a6);
              color: white;
            }
            .btn-secondary {
              background: rgba(255, 255, 255, 0.04);
              color: var(--text);
            }
            ul {
              margin: 18px 0 0;
              padding-left: 18px;
              color: var(--muted);
              line-height: 1.7;
            }
            code {
              background: rgba(255, 255, 255, 0.06);
              padding: 2px 6px;
              border-radius: 6px;
            }
          </style>
        </head>
        <body>
          <main class="card">
            <div class="badge">OpenEnv Space</div>
            <h1>SmartInbox-Pro</h1>
            <p>
              This Space hosts an email-triage environment for OpenEnv. If the embedded
              playground does not render in the Hugging Face App tab, use the direct
              links below.
            </p>
            <div class="actions">
              <a class="btn btn-primary" href="/web/" target="_self">Open Playground</a>
              <a class="btn btn-secondary" href="/docs" target="_self">Open API Docs</a>
              <a class="btn btn-secondary" href="/health" target="_self">Health Check</a>
            </div>
            <ul>
              <li><code>/web/</code> is the interactive OpenEnv playground.</li>
              <li><code>/docs</code> shows the live FastAPI/OpenAPI documentation.</li>
              <li><code>/health</code> returns a simple deployment health response.</li>
            </ul>
          </main>
        </body>
        </html>
        """
    )


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the SmartInbox-Pro server locally."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
