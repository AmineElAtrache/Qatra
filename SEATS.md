# Seats — who owns what

Five equal seats. One repo. One branch per person. Merge through pull requests.

| Seat | Branch | Owns (primary) | Touch only with review |
| --- | --- | --- | --- |
| **Backend** | `seat/backend` | `backend/app/core/`, `backend/app/api/`, `backend/app/domain/`, `orchestrator.py`, `validator.py`, `docker-compose.yml`, Alembic | shared contract |
| **Satellite** | `seat/satellite` | `backend/app/services/satellite_service.py`, satellite fixtures | orchestrator call site |
| **Agronomy** | `seat/agronomy` | `weather_service.py`, `agronomy_service.py`, `tests/test_engine.py` | validator rules |
| **Interface** | `seat/interface` | entire `web/`, `notification.py`, `api/v1/telegram.py` | API response shapes |
| **Explanation** | `seat/explanation` | `explain.py`, `backend/knowledge/`, Ask Qatra route, CI workflow | JSON fields used in prose |

## Merge rules

1. **Contract first.** `docs/contract.json` is the shared shape. Change it in a PR titled `contract: …` and get every seat to acknowledge.
2. **Do not invent doses in the UI or in Ollama.** Numbers come from agronomy + validator only.
3. **Null stays null.** Missing satellite or weather stays `null` / `needs_check`. No fake fill.
4. **Branch from `main`.** Name: `seat/<your-seat>/short-topic`.
5. **One PR = one seat topic.** A teammate from another seat reviews.
6. **Demo plot is `MA-001`.** Everyone proves work against that plot.

## Week rhythm

- **Monday (30 min):** set the week goal for each seat.
- **Friday:** each seat shows progress on `MA-001`.
- **Daily:** keep PRs small so merge stays easy.

## First tasks (MVP boot)

See `docs/seats/*.md` for the first checklist of each seat.

Shared day-1 goal: Compose up → sample plot → ETc test 3.15 mm green → Leaflet map of Morocco → French + Darija template text.
