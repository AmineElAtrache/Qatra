# Seat · Explanation

**Branch:** `seat/explanation/...`

## Owns

- `explain.py` (unified Ask handler, Ollama health check, deterministic offline templates)
- `backend/knowledge/fao/`, `backend/knowledge/inra/`
- Ask Qatra answers
- CI workflow green for explanation path

## Offline Ask pipeline

- App, Telegram, and WhatsApp Ask requests use the same `ask_qatra` service.
- The app supplies its latest saved recommendation; messaging webhooks load
  `backend/app/services/data/last_stored_state.json`. New recommendations
  replace this snapshot for offline channels.
- The response language is selected from the question (English, French, or
  Arabic), and the app Ask API accepts an optional `language` override. Telegram
  uses the sender's language code when available. The previous Darija template
  is retained for compatibility.
- Ollama availability is checked, but model-generated prose is never used for
  irrigation recommendations. Responses are deterministic and metric values
  appear only when present in stored state.
- Static FAO/INRA excerpts provide qualitative context. They are never used to
  invent or estimate irrigation depths.

## Test

Stop Ollama → Ask remains available from the saved JSON state and static
references, without inventing missing irrigation metrics.
