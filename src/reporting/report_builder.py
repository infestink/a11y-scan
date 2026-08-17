from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from src.api.models import ScanResponse, Severity

# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------

def build_json_report(record: ScanResponse, output: Path) -> None:
    output.write_text(record.model_dump_json(indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

_SEVERITY_COLOURS: dict[Severity, str] = {
    Severity.critical: "#d32f2f",
    Severity.serious:  "#f57c00",
    Severity.advisory: "#1976d2",
}


def build_html_report(record: ScanResponse, output: Path) -> None:
    url = str(record.request.url)
    total = sum(len(p.violations) for p in record.pages)
    by_sev = {s: 0 for s in Severity}
    for page in record.pages:
        for v in page.violations:
            by_sev[v.severity] += 1

    badge_html = "".join(
        f'<span class="badge" style="background:{_SEVERITY_COLOURS[s]}">'
        f'{by_sev[s]} {s.value}</span>'
        for s in Severity
    )

    pages_html = "\n".join(_page_section(p_result) for p_result in record.pages)

    html = dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width,initial-scale=1">
          <title>a11y-scan — {url}</title>
          <style>
            body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #212121; }}
            h1 {{ font-size: 1.4rem; }}
            .meta {{ color: #666; font-size: .875rem; margin-bottom: 1.5rem; }}
            .badge {{ display: inline-block; color: #fff; border-radius: 4px;
                      padding: 2px 8px; margin-right: 6px; font-size: .8rem; }}
            details {{ border: 1px solid #e0e0e0; border-radius: 6px;
                       margin-bottom: .75rem; }}
            summary {{ padding: .6rem 1rem; cursor: pointer; font-weight: 600; }}
            .violation {{ padding: .5rem 1rem 1rem; border-top: 1px solid #f0f0f0; }}
            .node {{ background: #f5f5f5; border-radius: 4px; padding: .4rem .6rem;
                     margin-top: .4rem; font-size: .8rem; font-family: monospace;
                     white-space: pre-wrap; word-break: break-all; }}
            a {{ color: #1565c0; }}
            .sev-critical {{ color: {_SEVERITY_COLOURS[Severity.critical]}; }}
            .sev-serious  {{ color: {_SEVERITY_COLOURS[Severity.serious]}; }}
            .sev-advisory {{ color: {_SEVERITY_COLOURS[Severity.advisory]}; }}
          </style>
        </head>
        <body>
          <h1>Accessibility Scan Report</h1>
          <div class="meta">
            <strong>Target:</strong> <a href="{url}">{url}</a><br>
            <strong>Scanned:</strong> {record.created_at.strftime("%Y-%m-%d %H:%M UTC")}<br>
            <strong>Pages:</strong> {len(record.pages)} &nbsp;
            <strong>Total violations:</strong> {total}
          </div>
          <div>{badge_html}</div>
          <hr style="margin: 1.5rem 0">
          {pages_html}
        </body>
        </html>
    """)

    output.write_text(html, encoding="utf-8")


def _page_section(page_result) -> str:  # type: ignore[no-untyped-def]
    if not page_result.violations:
        return f"<h2>{page_result.url}</h2><p>No violations found.</p>"

    violations_html = "\n".join(_violation_block(v) for v in page_result.violations)
    return dedent(f"""\
        <h2>{page_result.url}</h2>
        {violations_html}
    """)


def _violation_block(v) -> str:  # type: ignore[no-untyped-def]
    colour = _SEVERITY_COLOURS.get(v.severity, "#666")
    nodes_html = "\n".join(
        f'<div class="node">{n.html}</div>' for n in v.nodes[:5]
    )
    more = len(v.nodes) - 5
    if more > 0:
        nodes_html += f"<p>… and {more} more nodes</p>"

    return dedent(f"""\
        <details>
          <summary>
            <span style="color:{colour}">[{v.severity.value.upper()}]</span>
            {v.rule_id} — {v.description}
          </summary>
          <div class="violation">
            <a href="{v.help_url}" target="_blank" rel="noopener">More info ↗</a>
            {nodes_html}
          </div>
        </details>
    """)
