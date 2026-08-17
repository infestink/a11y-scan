# a11y-scan

Automated web accessibility scanner built on [axe-core](https://github.com/dequelabs/axe-core) and
[Playwright](https://playwright.dev/python/). Exposes a REST API, stores historical scan results for
regression diffing, and generates HTML/JSON reports.

## Quick start

```bash
pip install -e ".[dev]"
playwright install chromium
cp .env.example .env
uvicorn src.api.main:app --reload
```

POST a scan:

```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_pages": 1}'
```

Poll for results:

```bash
curl http://localhost:8000/api/v1/scan/<scan_id>
```

## Project layout

| Path | Purpose |
|------|---------|
| `src/api/` | FastAPI app — routes, models, service layer |
| `src/scanner/` | Playwright crawler + axe-core runner + severity mapping |
| `src/storage/` | SQLite persistence via aiosqlite |
| `src/reporting/` | HTML and JSON report generation |
| `tests/unit/` | Severity mapping, report builder — no network |
| `tests/integration/` | Scanner against local fixture HTML pages |
| `tests/api/` | FastAPI TestClient tests |
| `tests/e2e/` | Playwright driving the live API end-to-end |
| `fixtures/html/` | Local pages with seeded accessibility violations |
| `targets.yaml` | URLs scanned by the nightly workflow |
| `reports/` | Generated output (gitignored; sample committed) |

## Running tests

```bash
# Fast tests only (unit + API)
pytest -m "unit or api"

# Integration (requires: playwright install chromium)
pytest -m integration

# End-to-end (requires running API + network)
pytest -m e2e
```

## Nightly scan

`.github/workflows/nightly-scan.yml` runs at 03:00 UTC, scans every URL in `targets.yaml`,
diffs against the previous SQLite-stored run, and fails if new critical violations exceed
`REGRESSION_THRESHOLD` (default 5). Set `NOTIFY_WEBHOOK_URL` for Slack/Teams alerts.

## Severity levels

| axe impact | a11y-scan severity |
|------------|--------------------|
| critical   | critical |
| serious    | serious  |
| moderate   | advisory |
| minor      | advisory |

Rule-level overrides (e.g. `keyboard` → critical, `color-contrast` → serious, `region` → advisory)
are defined in [src/scanner/severity.py](src/scanner/severity.py).