Membre 1 — Backend & Architecture (Siège Backend)
·	Week 1 — feat(backend): spin up Docker Compose with PostGIS, Redis, sample plot, and publish docs/contract.json
·	Week 2 — feat(backend): add JWT authentication (/auth/register, /auth/login) and polygon plot creation endpoint (/plots)
·	Week 3 — feat(backend): build orchestrator and validator service (app/services/validator.py) on plot MA-001
·	Week 4 — feat(backend): manage execution flow for farmer recommendation requests and persist recommendation audit logs
·	Week 5 — feat(backend): implement Redis daily background worker to process automated updates across demo plots
·	Week 6 — feat(auth): enforce role-based access control (RBAC) separating Farmer and Advisor permissions across API routes
Membre 2 — Imagerie & Données Satellitaires (Siège Satellite)
·	Week 1 — feat(satellite): connect Earth Engine API for single coordinate scene fetch or record pending access status
·	Week 2 — feat(satellite): calculate NDVI, NDWI, acquisition date, and valid-pixel share for target polygons
·	Week 3 — feat(satellite): render and serve PNG canopy vigor map overlays for Mapbox GL mapping
·	Week 4 — feat(satellite): wrap Earth Engine API in fault-tolerant exception handler to prevent API crashes on downstream outages
·	Week 5 — feat(satellite): build Sentinel-1 SAR fallback pipeline (<70% valid optical pixels) and offline pre-downloaded scene fallback
·	Week 6 — feat(satellite): validate satellite data pipeline end-to-end and prepare module defense presentation
Membre 3 — Météo & Calculs Agronomiques (Siège Agronomie)
·	Week 1 — feat(agronomy): implement baseline ET0 calculation from fixed weather sample and pass constant ETc = 3.15 mm
·	Week 2 — feat(agronomy): fetch Open-Meteo weather inputs and compute FAO-56 Penman-Monteith ET0 into contract fields
·	Week 3 — feat(agronomy): build root-zone water balance ($ET_c$, effective rain, drip/surface efficiency) and unit test suite
·	Week 4 — feat(agronomy): implement fungal_risk assessment, plot surface spray volume calculation, and 15 km/h wind block rule
·	Week 5 — feat(agronomy): compute season water totals and validate agronomic calculation stability across all demo plots
·	Week 6 — feat(agronomy): conduct engine replay test validation and prepare module defense presentation
Membre 4 — Application Web & Canal WhatsApp (Siège Interface)
·	Week 1 — feat(interface): render interactive Mapbox GL map centered on Morocco
·	Week 2 — feat(interface): implement polygon drawing tool on map and wire POST payload to /plots API endpoint
·	Week 3 — feat(interface): render plot result card displaying forecast time and imagery timestamp as separate facts
·	Week 4 — feat(interface): connect end-to-end farmer UI flow (map to card) and dispatch test WhatsApp text message
·	Week 5 — feat(interface): build advisor dashboard (map, priority visit list, season total) and attach Darija TTS voice notes to WhatsApp messages
·	Week 6 — feat(interface): polish UI/UX for full presentation demo (show_dose, needs_check, blocked spray) and prepare module defense presentation
Membre 5 — Génération de Texte, QA & Ops (Siège Explication)
·	Week 1 — feat(explanation): generate French and Darija text explanations from mock JSON without extra numbers
·	Week 2 — feat(explanation): build 3-language generator (FR, AR, Darija) parsing live agronomy JSON payloads
·	Week 3 — feat(explanation): setup FAO/INRA reference document folder and offline fallback template engine
·	Week 4 — feat(explanation): launch Ask Qatra interactive Q&A assistant for web and WhatsApp queries
·	Week 5 — feat(whatsapp): handle inbound WhatsApp webhook messages and route directly to Ask Qatra engine
·	Week 6 — feat(ci): add daily workflow integration test in GitHub Actions and configure Prometheus/Grafana monitoring dashboards

