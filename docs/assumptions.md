# Assumptions (MVP)

- First crop: citrus in Morocco.
- Dose comes from FAO-56 code, never from the language model.
- Disease label for v1 is `fungal_risk` (not mildiou / oïdium).
- Wind above 15 km/h sets `spray_blocked = true`.
- Optical satellite older than 10 days or under 70 % valid pixels → `needs_check`.
- Missing NDVI stays `null`; radar (Sentinel-1) is a confidence flag, not a fake NDVI.
- Mapping: Leaflet + OpenStreetMap (no Mapbox token).
- Satellite: Copernicus Data Space first; Earth Engine only if eligible.
- LLM: Ollama local; offline sentence templates if the model is down.
- Speech: Piper or Web Speech; always send text with audio.
- Notifications: web push / in-app, or Telegram Bot (not WhatsApp Cloud API for MVP cost).
