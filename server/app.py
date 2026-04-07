from __future__ import annotations

"""FastAPI application entrypoint for SmartInbox-Pro."""

try:
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


app = create_app(
    SmartInboxProEnvironment,
    SmartInboxProAction,
    SmartInboxProObservation,
    env_name="smartinbox_pro",
    max_concurrent_envs=4,
)


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
