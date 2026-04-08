from __future__ import annotations

"""FastAPI application entrypoint for SmartInbox-Pro."""

import os
from html import escape
from pathlib import Path
from tempfile import gettempdir

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
from smartinbox_env.tasks import TASKS

README_PATH = Path(__file__).resolve().parent.parent / "README.md"
PLAYGROUND_README_PATH = Path(gettempdir()) / "smartinbox_pro_playground_readme.md"


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2].lstrip()


def _prepare_playground_readme() -> None:
    if not README_PATH.exists():
        return
    clean_readme = _strip_frontmatter(README_PATH.read_text(encoding="utf-8"))
    PLAYGROUND_README_PATH.write_text(clean_readme, encoding="utf-8")


_prepare_playground_readme()
os.environ["ENV_README_PATH"] = str(PLAYGROUND_README_PATH)

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

LABEL_STYLES = {
    "spam": "linear-gradient(135deg, rgba(239, 68, 68, 0.22), rgba(220, 38, 38, 0.12))",
    "normal": "linear-gradient(135deg, rgba(56, 189, 248, 0.18), rgba(37, 99, 235, 0.10))",
    "urgent": "linear-gradient(135deg, rgba(245, 158, 11, 0.22), rgba(249, 115, 22, 0.12))",
}


def _email_lookup(task_id: int, email_id: str | None) -> dict | None:
    if not email_id:
        return None
    for email in TASKS.get(task_id, {}).get("emails", []):
        if email["id"] == email_id:
            return email
    return None


def _progress_html(state: dict[str, object]) -> str:
    current_step = int(state.get("current_step", 0))
    total_emails = max(int(state.get("total_emails", 1)), 1)
    progress = min(max(current_step / total_emails, 0), 1)
    percent = round(progress * 100)
    return f"""
    <div style="display:grid; gap:8px;">
      <div style="display:flex; justify-content:space-between; color:#c6d4e7; font-size:13px;">
        <span>Episode progress</span>
        <span>{current_step}/{total_emails}</span>
      </div>
      <div style="height:12px; border-radius:999px; background:rgba(23, 40, 67, 0.96); overflow:hidden; border:1px solid rgba(85, 111, 148, 0.28);">
        <div style="width:{percent}%; height:100%; border-radius:999px; background:linear-gradient(90deg, #2563eb, #22d3ee);"></div>
      </div>
    </div>
    """


def _current_email_html(state: dict[str, object]) -> str:
    task_id = int(state.get("task_id", 1))
    email = _email_lookup(task_id, state.get("current_email_id"))
    if state.get("done"):
        return """
        <div style="padding:20px; border-radius:18px; border:1px solid rgba(94, 126, 168, 0.2); background:rgba(10, 19, 35, 0.94);">
          <div style="font-size:12px; letter-spacing:0.08em; text-transform:uppercase; color:#8fd6ff; font-weight:700; margin-bottom:8px;">Episode complete</div>
          <div style="font-size:24px; font-weight:700; letter-spacing:-0.04em; color:#eff6ff; margin-bottom:8px;">No email remaining</div>
          <div style="color:#b9c8dd;">Reset the environment to start a fresh task run.</div>
        </div>
        """
    if not email:
        return """
        <div style="padding:20px; border-radius:18px; border:1px solid rgba(94, 126, 168, 0.2); background:rgba(10, 19, 35, 0.94); color:#b9c8dd;">
          Reset to load the current email.
        </div>
        """
    difficulty = escape(str(state.get("difficulty", "unknown")).title())
    subject = escape(email.get("subject", "Untitled"))
    sender = escape(email.get("sender", "unknown sender"))
    body = escape(email.get("body", ""))
    style = LABEL_STYLES.get(difficulty.lower(), LABEL_STYLES["normal"])
    return f"""
    <div style="display:grid; gap:14px; padding:22px; border-radius:22px; border:1px solid rgba(94, 126, 168, 0.22); background:linear-gradient(180deg, rgba(11, 20, 37, 0.98), rgba(16, 28, 48, 0.94)); box-shadow:0 18px 36px rgba(0, 0, 0, 0.22);">
      <div style="display:flex; gap:10px; align-items:center; justify-content:space-between; flex-wrap:wrap;">
        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
          <span style="padding:6px 10px; border-radius:999px; font-size:12px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; color:#eff6ff; background:{style}; border:1px solid rgba(255,255,255,0.08);">{difficulty}</span>
          <span style="padding:6px 10px; border-radius:999px; font-size:12px; color:#b9c8dd; background:rgba(20,34,57,0.9); border:1px solid rgba(94, 126, 168, 0.16);">{escape(str(email.get("id", "")))}</span>
        </div>
        <span style="color:#8fd6ff; font-size:13px;">Sender: {sender}</span>
      </div>
      <div>
        <div style="font-size:30px; font-weight:700; line-height:1.04; letter-spacing:-0.05em; color:#eff6ff; margin-bottom:8px;">{subject}</div>
        <div style="color:#b9c8dd; font-size:15px; line-height:1.7;">{body}</div>
      </div>
    </div>
    """


def _state_summary_html(state: dict[str, object], response: dict[str, object] | None = None) -> str:
    done = bool(state.get("done", False))
    total_reward = float(state.get("total_reward_so_far", 0.0))
    overrides = int(state.get("ai_overrides", 0))
    blocks = int(state.get("security_blocks", 0))
    latency = float(state.get("avg_step_latency_ms", 0.0))
    last_reward = None
    if response:
      last_reward = response.get("reward")
    summary = [
        ("Status", "Completed" if done else "Active"),
        ("Reward total", f"{total_reward:.2f}"),
        ("Last reward", "N/A" if last_reward is None else f"{float(last_reward):.2f}"),
        ("AI overrides", str(overrides)),
        ("Security blocks", str(blocks)),
        ("Avg latency", f"{latency:.2f} ms"),
    ]
    cards = "".join(
        f"""
        <div style="padding:14px 16px; border-radius:16px; background:rgba(11, 21, 38, 0.94); border:1px solid rgba(94, 126, 168, 0.18);">
          <div style="font-size:12px; text-transform:uppercase; letter-spacing:0.08em; color:#7fa6d6; margin-bottom:6px;">{escape(label)}</div>
          <div style="font-size:22px; letter-spacing:-0.04em; font-weight:700; color:#eff6ff;">{escape(value)}</div>
        </div>
        """
        for label, value in summary
    )
    return f'<div style="display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px;">{cards}</div>'


def _task_guide_html(state: dict[str, object]) -> str:
    task_id = int(state.get("task_id", 1))
    task = TASKS.get(task_id, TASKS[1])
    ladder = []
    for current_id, current_task in TASKS.items():
        active = current_id == task_id
        border = "rgba(34, 211, 238, 0.42)" if active else "rgba(94, 126, 168, 0.18)"
        background = "rgba(13, 31, 56, 0.98)" if active else "rgba(11, 21, 38, 0.9)"
        ladder.append(
            f"""
            <div style="padding:12px 14px; border-radius:16px; border:1px solid {border}; background:{background};">
              <div style="display:flex; justify-content:space-between; gap:10px; align-items:center;">
                <strong style="color:#eff6ff;">Task {current_id}: {escape(current_task['name'])}</strong>
                <span style="padding:4px 8px; border-radius:999px; font-size:11px; text-transform:uppercase; letter-spacing:0.08em; color:#8fd6ff; background:rgba(37, 99, 235, 0.16);">{escape(current_task['difficulty'])}</span>
              </div>
              <div style="color:#b9c8dd; font-size:14px; margin-top:6px;">{escape(current_task['description'])}</div>
            </div>
            """
        )
    return f"""
    <div style="display:grid; gap:12px;">
      <div style="padding:16px; border-radius:18px; background:rgba(11, 21, 38, 0.94); border:1px solid rgba(94, 126, 168, 0.18);">
        <div style="font-size:12px; text-transform:uppercase; letter-spacing:0.08em; color:#7fa6d6; margin-bottom:8px;">Current task</div>
        <div style="font-size:22px; font-weight:700; color:#eff6ff; letter-spacing:-0.04em;">Task {task_id}: {escape(task['name'])}</div>
        <div style="margin-top:8px; color:#b9c8dd; line-height:1.6;">{escape(task['description'])}</div>
      </div>
      <div style="padding:16px; border-radius:18px; background:rgba(11, 21, 38, 0.94); border:1px solid rgba(94, 126, 168, 0.18);">
        <div style="font-size:12px; text-transform:uppercase; letter-spacing:0.08em; color:#7fa6d6; margin-bottom:10px;">Label guide</div>
        <div style="display:grid; gap:8px;">
          <div style="padding:10px 12px; border-radius:14px; background:{LABEL_STYLES['spam']}; border:1px solid rgba(239, 68, 68, 0.2); color:#eff6ff;"><strong>0 = spam</strong><br><span style="color:#ffd6d6;">Scams, fake promos, suspicious offers, unsafe senders.</span></div>
          <div style="padding:10px 12px; border-radius:14px; background:{LABEL_STYLES['normal']}; border:1px solid rgba(56, 189, 248, 0.18); color:#eff6ff;"><strong>1 = normal</strong><br><span style="color:#dbeafe;">Routine work mail, newsletters, reminders, updates.</span></div>
          <div style="padding:10px 12px; border-radius:14px; background:{LABEL_STYLES['urgent']}; border:1px solid rgba(245, 158, 11, 0.22); color:#eff6ff;"><strong>2 = urgent</strong><br><span style="color:#ffedd5;">Outages, legal/compliance deadlines, billing failures, escalations.</span></div>
        </div>
      </div>
      <div style="display:grid; gap:10px;">{''.join(ladder)}</div>
    </div>
    """


def _history_md(state: dict[str, object]) -> str:
    predictions = state.get("predictions_so_far", []) or []
    if not predictions:
        return "No actions yet. Press **Reset** and classify the first email."
    label_names = {0: "spam", 1: "normal", 2: "urgent"}
    chips = []
    for index, label in enumerate(predictions, start=1):
        chips.append(f"`{index}. {label_names.get(int(label), str(label))}`")
    return " ".join(chips)


def create_visualization_tab(
    web_manager,
    action_fields,
    metadata,
    is_chat_env,
    title,
    quick_start_md,
):
    del action_fields, metadata, is_chat_env, title, quick_start_md

    async def reset_dashboard():
        response = await web_manager.reset_environment()
        state = web_manager.get_state()
        return (
            _current_email_html(state),
            _progress_html(state),
            _task_guide_html(state),
            _state_summary_html(state, response),
            _history_md(state),
            "Environment reset. Review the email card and choose a label.",
            json.dumps(response, indent=2),
        )

    async def take_action(label: int):
        response = await web_manager.step_environment({"label": label})
        state = web_manager.get_state()
        label_name = {0: "spam", 1: "normal", 2: "urgent"}[label]
        return (
            _current_email_html(state),
            _progress_html(state),
            _task_guide_html(state),
            _state_summary_html(state, response),
            _history_md(state),
            f"Applied label: {label_name}.",
            json.dumps(response, indent=2),
        )

    async def mark_spam():
        return await take_action(0)

    async def mark_normal():
        return await take_action(1)

    async def mark_urgent():
        return await take_action(2)

    with gr.Blocks() as demo:
        gr.Markdown(
            """
            # Visual Workspace

            A cleaner operator view for exploring the SmartInbox-Pro environment without
            replacing the default OpenEnv playground.
            """
        )
        with gr.Row():
            with gr.Column(scale=5):
                progress = gr.HTML(_progress_html({"current_step": 0, "total_emails": 1}))
                email_card = gr.HTML(_current_email_html({}))
            with gr.Column(scale=3):
                task_guide = gr.HTML(_task_guide_html({}))
                status_cards = gr.HTML(_state_summary_html({}))
                history = gr.Markdown(_history_md({}))
                status = gr.Textbox(
                    value="Reset the environment to load a task.",
                    label="Status",
                    interactive=False,
                )
        with gr.Row():
            reset_btn = gr.Button("Reset Task", variant="secondary")
            spam_btn = gr.Button("Mark Spam", variant="secondary")
            normal_btn = gr.Button("Mark Normal", variant="secondary")
            urgent_btn = gr.Button("Mark Urgent", variant="primary")
        raw_json = gr.Code(
            label="Latest Environment Response",
            language="json",
            interactive=False,
        )

        reset_btn.click(
            fn=reset_dashboard,
            outputs=[email_card, progress, task_guide, status_cards, history, status, raw_json],
        )
        spam_btn.click(
            fn=mark_spam,
            outputs=[email_card, progress, task_guide, status_cards, history, status, raw_json],
        )
        normal_btn.click(
            fn=mark_normal,
            outputs=[email_card, progress, task_guide, status_cards, history, status, raw_json],
        )
        urgent_btn.click(
            fn=mark_urgent,
            outputs=[email_card, progress, task_guide, status_cards, history, status, raw_json],
        )

    return demo


app = create_app(
    SmartInboxProEnvironment,
    SmartInboxProAction,
    SmartInboxProObservation,
    env_name="smartinbox_pro",
    max_concurrent_envs=4,
    gradio_builder=create_visualization_tab,
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
              --bg: #07111f;
              --panel: rgba(13, 24, 43, 0.9);
              --panel-2: rgba(18, 31, 54, 0.96);
              --text: #eff6ff;
              --muted: #b9c8dd;
              --blue: #60a5fa;
              --cyan: #22d3ee;
              --green: #34d399;
              --border: rgba(110, 141, 184, 0.22);
            }
            * { box-sizing: border-box; }
            body {
              margin: 0;
              font-family: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif;
              background:
                radial-gradient(circle at top right, rgba(96, 165, 250, 0.22), transparent 26%),
                radial-gradient(circle at bottom left, rgba(34, 211, 238, 0.14), transparent 30%),
                linear-gradient(180deg, rgba(7, 17, 31, 0.98), rgba(7, 17, 31, 1)),
                var(--bg);
              color: var(--text);
              min-height: 100vh;
              padding: 28px;
            }
            .shell {
              width: min(1100px, 100%);
              margin: 0 auto;
              display: grid;
              gap: 18px;
            }
            .hero {
              background:
                linear-gradient(145deg, rgba(11, 21, 38, 0.96), rgba(19, 33, 58, 0.92)),
                var(--panel);
              border: 1px solid var(--border);
              border-radius: 26px;
              padding: 34px;
              box-shadow: 0 30px 60px rgba(0, 0, 0, 0.28);
              overflow: hidden;
              position: relative;
            }
            .hero::after {
              content: "";
              position: absolute;
              inset: auto -80px -120px auto;
              width: 240px;
              height: 240px;
              background: radial-gradient(circle, rgba(34, 211, 238, 0.22), transparent 70%);
              pointer-events: none;
            }
            h1 {
              margin: 0 0 12px;
              font-size: clamp(34px, 5vw, 58px);
              line-height: 0.98;
              letter-spacing: -0.05em;
            }
            p {
              margin: 0 0 14px;
              color: var(--muted);
              line-height: 1.6;
              font-size: 17px;
            }
            .badge {
              display: inline-block;
              margin-bottom: 18px;
              padding: 7px 12px;
              border-radius: 999px;
              background: rgba(37, 99, 235, 0.18);
              color: #8fc2ff;
              font-size: 12px;
              font-weight: 700;
              letter-spacing: 0.08em;
              text-transform: uppercase;
            }
            .hero-grid {
              display: grid;
              grid-template-columns: 1.3fr 0.9fr;
              gap: 20px;
              align-items: start;
            }
            .eyebrow {
              color: #8fd6ff;
              font-weight: 700;
              letter-spacing: 0.05em;
              text-transform: uppercase;
              font-size: 13px;
              margin-bottom: 12px;
            }
            .stats {
              display: grid;
              grid-template-columns: repeat(3, minmax(0, 1fr));
              gap: 12px;
              margin-top: 22px;
            }
            .stat {
              padding: 16px;
              background: rgba(8, 17, 33, 0.64);
              border: 1px solid rgba(110, 141, 184, 0.18);
              border-radius: 18px;
            }
            .stat strong {
              display: block;
              font-size: 24px;
              margin-bottom: 6px;
              letter-spacing: -0.04em;
            }
            .stat span {
              color: var(--muted);
              font-size: 14px;
            }
            .side-card {
              padding: 18px;
              background: rgba(8, 17, 33, 0.72);
              border: 1px solid rgba(110, 141, 184, 0.18);
              border-radius: 20px;
            }
            .side-card h2 {
              margin: 0 0 12px;
              font-size: 18px;
              letter-spacing: -0.03em;
            }
            .stack {
              display: grid;
              gap: 12px;
            }
            .mini {
              padding: 12px 14px;
              border-radius: 14px;
              background: rgba(15, 28, 47, 0.84);
              border: 1px solid rgba(110, 141, 184, 0.16);
            }
            .mini strong {
              display: block;
              margin-bottom: 5px;
              font-size: 14px;
            }
            .mini span {
              color: var(--muted);
              font-size: 14px;
            }
            .actions {
              display: flex;
              flex-wrap: wrap;
              gap: 12px;
              margin: 24px 0 18px;
            }
            .btn {
              display: inline-block;
              text-decoration: none;
              padding: 13px 18px;
              border-radius: 14px;
              font-weight: 700;
              border: 1px solid var(--border);
              transition: transform 0.18s ease, box-shadow 0.18s ease;
            }
            .btn:hover {
              transform: translateY(-1px);
              box-shadow: 0 12px 28px rgba(34, 211, 238, 0.12);
            }
            .btn-primary {
              background: linear-gradient(135deg, #2563eb, #06b6d4);
              color: white;
              border: none;
            }
            .btn-secondary {
              background: rgba(255, 255, 255, 0.04);
              color: var(--text);
            }
            .grid {
              display: grid;
              grid-template-columns: repeat(3, minmax(0, 1fr));
              gap: 16px;
            }
            .card {
              background: linear-gradient(180deg, rgba(13, 24, 43, 0.92), rgba(10, 19, 35, 0.96));
              border: 1px solid var(--border);
              border-radius: 20px;
              padding: 20px;
            }
            .card h3 {
              margin: 0 0 10px;
              font-size: 18px;
              letter-spacing: -0.03em;
            }
            ul {
              margin: 10px 0 0;
              padding-left: 18px;
              color: var(--muted);
              line-height: 1.7;
            }
            code {
              background: rgba(255, 255, 255, 0.06);
              padding: 2px 6px;
              border-radius: 6px;
            }
            .muted {
              color: var(--muted);
            }
            @media (max-width: 860px) {
              .hero-grid,
              .grid {
                grid-template-columns: 1fr;
              }
              .stats {
                grid-template-columns: 1fr;
              }
              body {
                padding: 18px;
              }
              .hero {
                padding: 24px;
              }
            }
          </style>
        </head>
        <body>
          <main class="shell">
            <section class="hero">
              <div class="badge">OpenEnv Space</div>
              <div class="hero-grid">
                <div>
                  <div class="eyebrow">AI Email Triage Environment</div>
                  <h1>SmartInbox-Pro</h1>
                  <p>
                    A production-style inbox triage environment where an agent must classify each
                    email as <strong>spam</strong>, <strong>normal</strong>, or <strong>urgent</strong>
                    using the standard OpenEnv <code>reset</code>, <code>step</code>, and <code>state</code> flow.
                  </p>
                  <div class="actions">
                    <a class="btn btn-primary" href="/web/" target="_self">Open Playground</a>
                    <a class="btn btn-secondary" href="/docs" target="_self">Open API Docs</a>
                    <a class="btn btn-secondary" href="/health" target="_self">Health Check</a>
                    <a class="btn btn-secondary" href="https://github.com/vivaanbathia864-tech/smartinbox-pro" target="_blank" rel="noreferrer">GitHub Repo</a>
                    <a class="btn btn-secondary" href="https://youtu.be/wlyQTeDSbRY?si=Fm_6MxIwwEVK-TPu" target="_blank" rel="noreferrer">Demo Video</a>
                  </div>
                  <div class="stats">
                    <div class="stat">
                      <strong>3</strong>
                      <span>Progressive tasks</span>
                    </div>
                    <div class="stat">
                      <strong>12D</strong>
                      <span>Observation vector</span>
                    </div>
                    <div class="stat">
                      <strong>0-2</strong>
                      <span>Label space: spam, normal, urgent</span>
                    </div>
                  </div>
                </div>
                <aside class="side-card">
                  <h2>What You Can Explore</h2>
                  <div class="stack">
                    <div class="mini">
                      <strong>Playground</strong>
                      <span>Run episodes manually, classify emails, and inspect JSON responses.</span>
                    </div>
                    <div class="mini">
                      <strong>API Docs</strong>
                      <span>Use FastAPI docs to inspect <code>/reset</code>, <code>/step</code>, and <code>/state</code>.</span>
                    </div>
                    <div class="mini">
                      <strong>Live Health</strong>
                      <span>Confirm the deployment is active and responding before evaluation.</span>
                    </div>
                  </div>
                </aside>
              </div>
            </section>
            <section class="grid">
              <article class="card">
                <h3>Task Design</h3>
                <ul>
                  <li>Easy: basic classification across 5 emails.</li>
                  <li>Medium: prioritization context across 10 emails.</li>
                  <li>Hard: full inbox workflow across 15 emails.</li>
                </ul>
              </article>
              <article class="card">
                <h3>Signals</h3>
                <ul>
                  <li>AI confidence and thread summaries.</li>
                  <li>Security checks like attachment threat scoring.</li>
                  <li>Reward shaping with partial credit.</li>
                </ul>
              </article>
              <article class="card">
                <h3>Routing</h3>
                <ul>
                  <li><code>/web/</code> for the interactive playground.</li>
                  <li><code>/docs</code> for the API surface.</li>
                  <li><code>/health</code> for the deployment heartbeat.</li>
                </ul>
              </article>
              <article class="card">
                <h3>Resources</h3>
                <ul>
                  <li><a href="https://github.com/vivaanbathia864-tech/smartinbox-pro" target="_blank" rel="noreferrer">Source code on GitHub</a></li>
                  <li><a href="https://youtu.be/wlyQTeDSbRY?si=Fm_6MxIwwEVK-TPu" target="_blank" rel="noreferrer">Walkthrough video</a></li>
                  <li><a href="/docs" target="_self">Live OpenAPI reference</a></li>
                </ul>
              </article>
            </section>
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
