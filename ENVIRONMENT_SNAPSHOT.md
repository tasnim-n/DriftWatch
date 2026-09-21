# DriftWatch Environment Snapshot

This file records the working research environment verified on 2026-09-21. It is descriptive and does not change the project's minimum dependency policy.

## Repository

- Branch: `main`
- Commit: `54a4780d58ac12b4c794145b773da5e2c15a6999`
- Verification timestamp: `2026-09-21T20:15:30.0662534+06:00`

## Platform

- Operating system: Windows 11
- Platform string: `Windows-11-10.0.26200-SP0`
- Python: `3.14.0`

## Major Dependencies

| Dependency | Version |
|---|---:|
| FastAPI | 0.141.1 |
| Uvicorn | 0.52.1 |
| Jinja2 | 3.1.6 |
| python-multipart | 0.0.32 |
| Pydantic | 2.13.4 |
| pydantic-settings | 2.14.2 |
| SQLAlchemy | 2.0.51 |
| pytest | 9.1.1 |
| pandas | 3.0.5 |
| NumPy | 2.5.1 |
| scikit-learn | 1.9.0 |
| SciPy | 1.18.0 |
| tldextract | 5.3.1 |
| HTTPX | 0.28.1 |

The full package snapshot is recorded in `requirements-research-lock.txt`.

## Test Verification

Command:

```powershell
python -m pytest -q
```

Result:

```text
157 passed in 32.55s
```

- Failed: 0
- Skipped: 0
- Warnings reported under configured filters: 0

## Scope

This snapshot supports research verification. It does not claim that every listed version is the minimum supported version, that future dependency releases are compatible, or that the raw corpus can be reconstructed from Git alone.
