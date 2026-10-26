# Contributing (team merge)

1. Read [SEATS.md](SEATS.md) — pick your seat and branch name.
2. Never commit `.env`. Copy from `.env.example`.
3. Shared contract: [docs/contract.json](docs/contract.json). Changing it needs a dedicated PR.
4. Keep PRs small and seat-scoped.
5. Tests that must stay green: `backend/tests/test_engine.py` (ETc = 3.15).

## Boot locally

```bash
cp .env.example .env
docker compose up --build
# API http://localhost:8000/docs
# Web http://localhost:3000
```

Backend only (no Docker for unit tests):

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

## Branch example

```bash
git checkout main
git pull
git checkout -b seat/agronomy/etc-root-zone
# … work …
git push -u origin HEAD
# open PR → ask another seat to review
```
