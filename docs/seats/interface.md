# Seat · Interface

**Branch:** `seat/interface`

## Owns

- Entire `web/` (Next.js + Leaflet + OSM)
- `notification.py`, `api/v1/telegram.py`
- Farmer + advisor screens, Ask Qatra UI
- Speech via Piper or Web Speech

## First MVP tasks

1. [ ] Leaflet map of Morocco + draw polygon
2. [ ] Farmer form (crop, stage, irrigation, last watering)
3. [ ] Result card from contract fields (no invented numbers)
4. [ ] Advisor map colored by status
5. [ ] Telegram bot webhook **or** in-app / web notification
6. [ ] Voice note optional; text always present

## Do not

- Call Mapbox
- Send WhatsApp Cloud API for MVP (cost)
