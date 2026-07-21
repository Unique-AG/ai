"""Render the MCP Apps chat panel with test messages into inspectable artifacts.

Generates, for each scenario, a standalone mock-host HTML file (open it in any
browser) and — when Google Chrome is installed — a PNG screenshot. Useful for
comparing the panel's rendering with the Unique chat frontend without going
through Claude.

Usage:
    uv run python preview_panel.py            # writes to ./preview/
    uv run python preview_panel.py --out DIR  # custom output directory
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_space_chat.ui_resource import load_chat_window_html  # noqa: E402

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "chromium",
]

# ── Test scenarios ────────────────────────────────────────────────────────────

_T = "2026-07-21T09:5{}:00Z"


def _user(text: str, minute: int = 0) -> dict:
    return {
        "id": f"u{minute}",
        "role": "USER",
        "text": text,
        "createdAt": _T.format(minute),
        "done": True,
        "references": [],
    }


def _assistant(text: str, minute: int = 1, done: bool = True, references=None) -> dict:
    return {
        "id": f"a{minute}",
        "role": "ASSISTANT",
        "text": text,
        "createdAt": _T.format(minute),
        "done": done,
        "references": references or [],
    }


SCENARIOS: dict[str, list[dict]] = {
    "01_basic_markdown": [
        _user("Show me a markdown feature tour"),
        _assistant(
            "# Heading 1\n"
            "## Heading 2\n"
            "### Heading 3\n\n"
            "Regular paragraph with **bold**, *italic*, `inline code`, and a "
            "[link](https://unique.ai).\n\n"
            "- Bullet one\n"
            "- Bullet two\n"
            "  - Nested bullet\n\n"
            "1. Numbered one\n"
            "2. Numbered two\n\n"
            "> A blockquote with some wisdom.\n\n"
            "---\n\n"
            "| Metric | Q1 | Q2 |\n"
            "|--------|----|----|\n"
            "| Revenue | 1.2M | 1.5M |\n"
            "| Users | 8k | 11k |\n\n"
            "```python\n"
            "def hello(name: str) -> str:\n"
            "    return f\"Hello {name}\"\n"
            "```\n"
        ),
    ],
    "02_citations": [
        _user("What is our travel policy? Cite sources."),
        _assistant(
            "Employees may book **business class** for flights longer than "
            "6 hours.<sup>1</sup> Hotel budgets are capped at CHF 300 per "
            "night in Zurich and CHF 250 elsewhere.<sup>2</sup>\n\n"
            "Approval is required from your line manager for any exception."
            "<sup>1</sup><sup>3</sup>",
            references=[
                {
                    "name": "Travel Policy 2026.pdf",
                    "url": "https://example.com/travel-policy",
                    "sequenceNumber": 1,
                },
                {
                    "name": "Expense Guidelines.docx",
                    "url": "https://example.com/expenses",
                    "sequenceNumber": 2,
                },
                {
                    "name": "Approval Matrix.xlsx",
                    "url": None,
                    "sequenceNumber": 3,
                },
            ],
        ),
    ],
    "03_thinking_and_status": [
        _user("Generate a unique AI sample pptx"),
        _assistant(
            "I'm using the `pptx` skill for the sample deck and first "
            "recovering any prior context.",
            minute=1,
        ),
        _assistant(
            "<details>\n"
            "<summary><b>Thinking steps</b></summary>\n"
            "<i><b>Step 1:</b> Recover prior context from the chat history "
            "and check for existing artifacts.</i>\n\n"
            "<i><b>Step 2:</b> Generate a clean Unique-styled sample deck "
            "with KPI cards and a roadmap.</i>\n"
            "</details>\n\n"
            "---\n\n"
            "Context is recovered; now I'm generating a clean Unique-styled "
            "sample deck.",
            minute=2,
        ),
    ],
    "04_files_and_prompts": [
        _user("Give me the generated files"),
        _assistant(
            "Here is everything the run produced:\n\n"
            "Download: [unique_ai_sample.pptx](unique://content/cont_pptx1)\n\n"
            "Chart preview: ![revenue_chart.png](unique://content/cont_img1)\n\n"
            "````fileWithSource(id='1', contentId='cont_xlsx1', "
            "title=\"kpi_data.xlsx\", type=\"excel\", code=\"df.to_excel(...)\")````\n\n"
            "What next?\n\n"
            "[Make it a dark theme](https://prompt=Make%20the%20deck%20dark)\n"
            "[Add a summary slide](https://prompt=Add%20a%20summary%20slide)\n"
        ),
    ],
    "05_streaming": [
        _user("Write a long analysis"),
        _assistant(
            "## Market analysis\n\nThe Swiss fintech sector grew by",
            done=False,
        ),
    ],
    "07_steps_timeline": [
        _user("Generate a unique AI sample pptx"),
        {
            "id": "a7",
            "role": "ASSISTANT",
            "text": (
                "I'll use the `pptx` skill for this and create a short plan "
                "first so the deck work stays tidy.\n\n"
                "I've got the PPTX workflow; now checking template rules "
                "before building."
            ),
            "createdAt": _T.format(7),
            "done": True,
            "references": [],
            "logs": [
                {
                    "text": "**Loaded Skill**",
                    "status": "COMPLETED",
                    "order": 1,
                    "events": [
                        {"type": "ToolCall", "text": "pptx", "status": None},
                        {"type": "Thinking", "text": "", "status": None},
                        {
                            "type": "Thinking",
                            "text": (
                                "**Considering template-discovery**\n"
                                "I need to continue exploring if "
                                "template-discovery applies here. The user "
                                "provided a generic request without a "
                                "specific template. I think I should check "
                                "the template folder, as the skill indicates "
                                "it should be resolved."
                            ),
                            "status": None,
                        },
                    ],
                },
                {
                    "text": "**Wrote a file**",
                    "status": "RUNNING",
                    "order": 2,
                    "events": [
                        {
                            "type": "Thinking",
                            "text": (
                                "**Status Update**\n"
                                "Still working — this is taking longer than "
                                "usual. Longer tool or subagent calls can "
                                "cause a brief pause."
                            ),
                            "status": None,
                        },
                        {"type": "ToolCall", "text": "Write", "status": None},
                        {"type": "Todo", "text": "Set up deck skeleton", "status": "done"},
                        {"type": "Todo", "text": "Add KPI slides", "status": "todo"},
                    ],
                },
            ],
        },
    ],
    "08_fence_fallback": [
        _user("Show the generated deck"),
        _assistant(
            "I also validated the `.pptx` and exported an internal PDF "
            "preview for QA.\n\n"
            "```\n"
            "id='1', contentId='cont_tn4nari8r67ffse7h65czgv7', "
            "title=\"unique_ai_sample_deck.pptx\", type=\"powerpoint\", "
            "code=\"prs.save('/mnt/data/deck.pptx')\"\n"
            "```\n"
        ),
    ],
    "06_full_conversation": [
        _user("Generate a unique AI sample pptx"),
        _assistant(
            "I'm using the `pptx` skill for the sample deck and first "
            "recovering any prior context.",
            minute=1,
        ),
        _assistant(
            "I created a **7-slide Unique AI sample PowerPoint deck** with a "
            "clean enterprise style, Unique-inspired colors, KPI cards, "
            "architecture visuals, use cases, governance messaging, and a "
            "pilot-to-production roadmap.<sup>1</sup>\n\n"
            "I also validated the deck structure and exported an internal "
            "PDF preview successfully.\n\n"
            "[unique_ai_sample.pptx](unique://content/cont_pptx9)",
            minute=3,
            references=[
                {
                    "name": "Unique brand guide",
                    "url": "https://example.com/brand",
                    "sequenceNumber": 1,
                }
            ],
        ),
    ],
}

# ── Harness template ──────────────────────────────────────────────────────────

_HARNESS_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>panel preview — __NAME__</title></head>
<body style="margin:0;background:#ececec;padding:18px;font-family:sans-serif;">
<div style="margin-bottom:10px;font-size:13px;color:#555;">__NAME__ — mock MCP host rendering the space-chat panel</div>
<iframe id="panel" style="width:780px;height:__HEIGHT__px;border:0;box-shadow:0 2px 12px rgba(0,0,0,0.12);border-radius:12px;" sandbox="allow-scripts"></iframe>
<script>
var MESSAGES = __MSGS__;
var DONE = __DONE__;
var PANEL_HTML = __HTML__;
var frame = document.getElementById('panel');
frame.srcdoc = PANEL_HTML;
window.addEventListener('message', function (ev) {
  var d = ev.data;
  if (!d || d.jsonrpc !== '2.0') return;
  function reply(result) {
    frame.contentWindow.postMessage({jsonrpc:'2.0', id: d.id, result: result}, '*');
  }
  if (d.method === 'ui/initialize') {
    reply({hostContext: {theme: 'light', containerDimensions: {height: __HEIGHT__}}});
    setTimeout(function () {
      frame.contentWindow.postMessage({jsonrpc:'2.0', method:'ui/notifications/tool-result',
        params: {structuredContent: {chatId: 'chat_preview'}}}, '*');
    }, 0);
    return;
  }
  if (d.method === 'tools/call') {
    reply({structuredContent: {chatId: 'chat_preview', messages: MESSAGES, done: DONE}});
    return;
  }
  if (d.id !== undefined) reply({});
});
</script></body></html>"""


def _js(obj) -> str:
    # "</" would terminate the harness <script> tag early.
    return json.dumps(obj).replace("</", "<\\/")


def build_harness(name: str, messages: list[dict], height: int = 900) -> str:
    done = all(m.get("done", True) for m in messages)
    return (
        _HARNESS_TEMPLATE.replace("__NAME__", name)
        .replace("__HEIGHT__", str(height))
        .replace("__MSGS__", _js(messages))
        .replace("__DONE__", "true" if done else "false")
        .replace("__HTML__", _js(load_chat_window_html()))
    )


def find_chrome() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="preview", help="Output directory")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()

    for name, messages in SCENARIOS.items():
        html_path = out / f"{name}.html"
        html_path.write_text(build_harness(name, messages), encoding="utf-8")
        print(f"wrote {html_path}")
        if chrome:
            png_path = out / f"{name}.png"
            subprocess.run(
                [
                    chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--window-size=820,1000",
                    f"--screenshot={png_path}",
                    "--timeout=8000",
                    html_path.resolve().as_uri(),
                ],
                check=True,
                capture_output=True,
            )
            print(f"wrote {png_path}")

    if not chrome:
        print("Chrome not found — HTML files only (open them in a browser).")


if __name__ == "__main__":
    main()
