# Week 5 Presentation Script — Ask Qatra Offline Pipeline

**Estimated time:** 2–3 minutes  
**Project:** Qatra agricultural advisory platform  
**Seat:** Explanation

## Speaking script

Hello Professor. I worked on the Explanation seat for Qatra, focusing on the
“Ask Qatra” feature. The goal was to let a farmer ask questions about the
latest recommendation, including when our local language model, Ollama, is
unavailable.

The main change is that app requests and messaging requests share the same
Ask service. The app uses its latest saved recommendation. Telegram and
WhatsApp use the locally stored JSON snapshot, which is updated when a new
recommendation is generated. This keeps the fallback available without
depending on Ollama.

The answer is deterministic: the system checks Ollama’s availability, but does
not rely on model-generated text for irrigation advice. It reads metrics only
from the stored recommendation and adds relevant qualitative context from our
static FAO and INRA references. If the state does not contain a numeric
irrigation amount, the answer does not estimate or invent one.

The pipeline supports English, French, and Arabic responses. It can select a
language from the question, accept an explicit language in the app Ask API,
and use the Telegram sender’s language when available. The existing Darija
template is also retained for compatibility.

I added tests for the unified webhook routing, reading and saving the state,
missing irrigation metrics, language selection, and offline behavior. The full
backend test suite passes: **92 passed and 1 skipped**.

This completes the offline Ask Qatra pipeline for my seat. Thank you.

## Live demo outline

Open the browser demo at [`/demo/ask`](http://localhost:3000/demo/ask) after
starting the web app and API. No CLI demo command is needed.

1. Show the recorded recommendation status, irrigation metrics (if present),
   and FAO / INRA references.
2. Stop or disable Ollama, then ask a question in the page. Explain that the
   page calls the same Ask service and reads the locally saved recommendation.
3. Use the language tabs to show the answer in French, English, and Arabic.
4. Show a state with no irrigation depth. Point out that the response asks for
   verification rather than inventing a value in millimetres.
5. If time allows, show a matching qualitative quote from the static
   [`FAO references`](../backend/knowledge/fao/README.md) or
   [`INRA references`](../backend/knowledge/inra/README.md).

## If asked about scope

- Ollama is health-checked, but its generated prose is not used to provide
  recommendations; that prevents it from introducing unsupported irrigation
  numbers.
- Telegram and WhatsApp use the latest locally stored snapshot. It is a shared
  snapshot, not per-chat plot linking.
- The pipeline uses static reference files and local state, so this fallback
  does not require an internet connection to generate its answer.
