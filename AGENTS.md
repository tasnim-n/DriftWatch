# DriftWatch Agent Guidance

## Project Purpose
DriftWatch is a browser-extension behavioural drift cybersecurity research project. It compares extension versions to identify risky changes such as permission creep, host-scope expansion, sensitive API use, network telemetry, and obfuscation.

## Architecture
DriftWatch uses FastAPI as the web application entrypoint (`app.main:app`). The pipeline includes secure archive ingestion, analyzer modules under `analyzers/`, risk scoring under `risk_engine/`, SQLAlchemy models under `app/models/`, schemas under `app/schemas/`, routes under `app/api/`, and Jinja2 templates under `app/templates/`.

## Windows Environment
Work from `E:\DriftWatch` using the project virtual environment.

## Test Command
```powershell
.venv\Scripts\pytest.exe tests\ -v -W default
```

## Run Command
```powershell
.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

## Security Restrictions
- Never execute uploaded extension JavaScript.
- Never bypass or weaken archive extraction protections.
- Never fabricate research results, metrics, scores, or experimental outcomes.
- Treat demo samples as controlled synthetic data only.
- Preserve existing working functionality and avoid unrelated rewrites.
- Run tests after code changes.
- Do not train ML models unless the user explicitly starts that phase.
- Keep DriftBench labels, splits, final risk scores, recommendations, and path-derived class names out of feature columns.
