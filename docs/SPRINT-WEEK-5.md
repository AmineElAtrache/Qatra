# Sprint — Week 5

Live data, advisor, notifications. Branch from `mvp`. One PR per seat. Friday demo on **MA-001**.

Do not start Week 6 (defense polish) until this Friday demo is green.

## Shared Friday proof

On plot `MA-001`:

- A real satellite date **or** an honest missing image (`needs_check` + reason, never a fake NDVI).
- Advisor can see and use that plot.
- One notification leaves the system (Telegram or in-app).

Monday (30 min): each seat picks **one** PR from the table below.

## Per seat

| Seat | Branch | Goal this week | Friday proof |
| --- | --- | --- | --- |
| **Backend** | `seat/backend/...` | Harden the daily path: Alembic on a clean DB, `make worker` without manual seed hacks, plot GeoJSON always passed to satellite, optional PostGIS image documented. Link farmer ↔ advisor plots if the advisor still “sees all”. | `POST /api/v1/jobs/daily` processes MA-001 and stores a new recommendation row. |
| **Satellite** | `seat/satellite/...` | Live Earth Engine with `GEE_PROJECT_ID=qatra-satellite-research` + credentials file. Serve vigor PNG overlay. Keep nulls when GEE fails. Confirm Sentinel-1 fallback when valid pixels &lt; 70 %. | Card shows NDVI / date / quality from a real scene **or** `needs_check` + reason. Never a fake index. |
| **Agronomy** | `seat/agronomy/...` | Season totals (rain, advised water, estimated need) on the recommendation / advisor payload. Replay test: same inputs → same ETc. Tune `fungal_risk` so it is explainable on the card. | Advisor payload has season numbers. ETc = 3.15 test still green. |
| **Interface** | `seat/interface/...` | Advisor map colored by status + visit list. Wire Telegram **or** in-app notification (no WhatsApp Cloud API). Voice: Web Speech or Piper; **text always with audio**. Phone layout on the farmer card. | Draw plot → card. Advisor sees MA-001. One test notify. |
| **Explanation** | `seat/explanation/...` | Ask Qatra on the last stored JSON only + FAO / INRA quotes. Inbound Telegram (or existing webhook) uses the same Ask path. Demo with Ollama **killed**. | Three languages offline. Ask Qatra answers without inventing millimetres. |

## Merge rules (unchanged)

1. Contract first: `docs/contract.json`. Change it only in a PR titled `contract: …`.
2. No invented doses in the UI or in Ollama.
3. Null stays null.
4. Branch from `mvp`: `seat/<seat>/short-topic`.
5. One PR = one seat topic. Another seat reviews.

## How to start

```bash
git checkout mvp
git pull
git checkout -b seat/<your-seat>/week-5-<topic>
```
