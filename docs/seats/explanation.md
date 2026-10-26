# Seat · Explanation

**Branch:** `seat/explanation`

## Owns

- `explain.py` (Ollama + offline templates)
- `backend/knowledge/fao/`, `backend/knowledge/inra/`
- Ask Qatra answers
- CI workflow green for explanation path

## First MVP tasks

1. [ ] Offline templates: FR / Darija / AR from JSON only
2. [ ] Ollama call when available; fallback if down
3. [ ] Ask Qatra: answer only from last recommendation + knowledge folder
4. [ ] Demo must work with Ollama network/process killed
5. [ ] No number in prose that is absent from the JSON

## Test

Cut Ollama → three languages still returned from templates.
