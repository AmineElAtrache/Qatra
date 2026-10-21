Voici votre texte structuré et mis en forme de manière claire et lisible, sous forme de tableau interactif et bien organisé par membre :

---

##  Répartition des Tâches par Membre (Plan sur 6 Semaines)

### 🔹 Membre 1 — Backend & Architecture *(Siège Backend)*

| Semaine | Type / Module | Description de la fonctionnalité |
| --- | --- | --- |
| **Week 1** | `feat(backend)` | Configuration de Docker Compose (PostGIS, Redis), création de la parcelle exemple et publication de `docs/contract.json` |
| **Week 2** | `feat(backend)` | Implémentation de l'authentification JWT (`/auth/register`, `/auth/login`) et création de l'endpoint pour les parcelles (`/plots`) |
| **Week 3** | `feat(backend)` | Développement du service d'orchestration et de validation (`app/services/validator.py`) sur la parcelle MA-001 |
| **Week 4** | `feat(backend)` | Gestion du flux d'exécution pour les requêtes de recommandation agriculteur et persistance des logs d'audit |
| **Week 5** | `feat(backend)` | Mise en place du worker Redis quotidien en arrière-plan pour traiter les mises à jour automatisées des parcelles démo |
| **Week 6** | `feat(auth)` | Application du contrôle d'accès basé sur les rôles (RBAC) pour séparer les permissions Agriculteur et Conseiller sur les routes API |

---

### 🔹 Membre 2 — Imagerie & Données Satellitaires *(Siège Satellite)*

| Semaine | Type / Module | Description de la fonctionnalité |
| --- | --- | --- |
| **Week 1** | `feat(satellite)` | Connexion à l'API Earth Engine pour la récupération de scènes par coordonnées simples ou enregistrement du statut d'accès en attente |
| **Week 2** | `feat(satellite)` | Calcul du NDVI, NDWI, date d'acquisition et proportion de pixels valides pour les polygones cibles |
| **Week 3** | `feat(satellite)` | Rendu et service des cartes PNG de vigueur du couvert végétal pour l'affichage via Mapbox GL |
| **Week 4** | `feat(satellite)` | Intégration d'un gestionnaire d'exceptions tolérant aux pannes autour de l'API Earth Engine pour éviter les crashs en cas de panne |
| **Week 5** | `feat(satellite)` | Pipeline de secours Sentinel-1 SAR (<70% de pixels optiques valides) et système de secours hors-ligne via scènes pré-téléchargées |
| **Week 6** | `feat(satellite)` | Validation de bout en bout du pipeline de données satellites et préparation de la soutenance du module |

---

### 🔹 Membre 3 — Météo & Calculs Agronomiques *(Siège Agronomie)*

| Semaine | Type / Module | Description de la fonctionnalité |
| --- | --- | --- |
| **Week 1** | `feat(agronomy)` | Calcul baseline de l'ET0 à partir d'échantillons météo fixes et envoi d'une constante $ET_c = 3.15\text{ mm}$ |
| **Week 2** | `feat(agronomy)` | Récupération des données Open-Meteo et calcul de l'ET0 (FAO-56 Penman-Monteith) injecté dans le contrat |
| **Week 3** | `feat(agronomy)` | Bilan hydrique de la zone racinaire ($ET_c$, pluie effective, efficacité goutte-à-goutte/surface) et suite de tests unitaires |
| **Week 4** | `feat(agronomy)` | Évaluation du risque fongique (`fungal_risk`), calcul du volume de pulvérisation et règle de blocage en cas de vent > 15 km/h |
| **Week 5** | `feat(agronomy)` | Calcul des cumuls d'eau de la saison et validation de la stabilité des calculs agronomiques sur toutes les parcelles démo |
| **Week 6** | `feat(agronomy)` | Tests de rejouabilité (*replay test*) du moteur et préparation de la soutenance du module |

---

### 🔹 Membre 4 — Application Web & Canal WhatsApp *(Siège Interface)*

| Semaine | Type / Module | Description de la fonctionnalité |
| --- | --- | --- |
| **Week 1** | `feat(interface)` | Rendu de la carte interactive Mapbox GL centrée sur le Maroc |
| **Week 2** | `feat(interface)` | Outil de dessin de polygones sur la carte et liaison du payload POST à l'endpoint `/plots` |
| **Week 3** | `feat(interface)` | Affichage de la carte de résultat parcelle distinguant l'heure de prévision et l'horodatage de l'image |
| **Week 4** | `feat(interface)` | Connexion du flux UI agriculteur de bout en bout (carte vers fiche) et envoi d'un message texte test sur WhatsApp |
| **Week 5** | `feat(interface)` | Tableau de bord conseiller (carte, visites prioritaires, total saison) et notes vocales en Darija via WhatsApp |
| **Week 6** | `feat(interface)` | Polissage UI/UX pour la démo finale (`show_dose`, `needs_check`, traitement bloqué) et préparation de la soutenance du module |

---

### 🔹 Membre 5 — Génération de Texte, QA & Ops *(Siège Explication)*

| Semaine | Type / Module | Description de la fonctionnalité |
| --- | --- | --- |
| **Week 1** | `feat(explanation)` | Génération d'explications textuelles en français et Darija à partir de JSON de test sans chiffres superflus |
| **Week 2** | `feat(explanation)` | Moteur de génération trilingue (FR, AR, Darija) analysant les payloads JSON agronomiques en direct |
| **Week 3** | `feat(explanation)` | Configuration du dossier de référence FAO/INRA et moteur de templates de secours hors-ligne |
| **Week 4** | `feat(explanation)` | Lancement de l'assistant interactif de Q&R *Ask Qatra* pour le web et WhatsApp |
| **Week 5** | `feat(whatsapp)` | Gestion des webhooks WhatsApp entrants et routage direct vers le moteur *Ask Qatra* |
| **Week 6** | `feat(ci)` | Ajout des tests d'intégration quotidiens via GitHub Actions et configuration des tableaux de bord Prometheus/Grafana |