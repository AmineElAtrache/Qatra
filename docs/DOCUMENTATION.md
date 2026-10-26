# Qatra

Documentation de projet. M352, Advanced AI Engineering. Octobre 2026.

Pilotage de l'irrigation à la parcelle, pour l'agriculteur et pour le conseiller. Cinq sièges, même niveau. Première culture : les agrumes, au Maroc.

Qatra ne remplace pas le tour d'eau d'un ORMVA. Il aide à utiliser l'eau le jour où elle arrive.

## 1. En une page

Qatra estime, chaque jour, le besoin en eau d'une parcelle d'agrumes, décrit le couvert vu par satellite, et dit si une pulvérisation est raisonnable. L'agriculteur lit le résultat sur un site de téléphone et par notification (site ou Telegram). Le conseiller voit les mêmes parcelles sur une carte.

Le chiffre ne vient pas d'un modèle de langage. Il vient d'un bilan hydrique FAO-56. Le modèle de langage (Ollama en local) explique ce chiffre déjà calculé, en darija, en français et en arabe. Si une donnée manque ou si l'image satellite est trop ancienne, la dose précise n'est pas affichée.

Trois sorties par parcelle et par jour :

- **Irrigation.** Besoin restant de la culture, en millimètres, après la pluie utile et l'eau déjà apportée.
- **Couvert.** NDVI et NDWI Sentinel-2, avec la date de l'image. Si les nuages cachent la parcelle, Sentinel-1 sert de repli. Le radar n'est pas transformé en faux NDVI.
- **Fenêtre de traitement.** Alerte de risque selon la météo, volume lié à la surface, et blocage si le vent dépasse 15 km/h.

## 2. Le problème

Au Maroc, l'agriculture concentre l'essentiel de l'eau consommée, et les années sèches se répètent. Les réseaux se modernisent et le goutte-à-goutte se généralise. La décision du jour, sur une parcelle précise, reste souvent une habitude : trop tôt, trop tard, ou la même dose pour un sol, un stade et une pluie différents.

Le bulletin régional donne le même message à toute une plaine. Deux parcelles voisines ne vivent pas la même semaine. Le conseiller de l'ORMVA, de la coopérative ou de l'association d'usagers ne peut pas visiter chaque exploitation. Une erreur à la floraison ou au grossissement se paie sur le rendement, et personne ne peut dire, en fin de saison, quelle eau a vraiment servi à la culture.

### Deux utilisateurs, un seul résultat

**Agriculteur.** Il dessine sa parcelle, indique la culture, le système d'irrigation et la dernière irrigation. Il lit la carte du jour. S'il l'a demandé, il reçoit une notification (site ou Telegram) quand la consigne change.

**Conseiller.** Il suit plusieurs parcelles : une carte du statut, une liste de visites, et le total d'eau de la saison. Il voit les parcelles qui lui sont liées, pas celles des autres.

## 3. Le principe

L'intelligence artificielle est autour du calcul, pas à la place du calcul.

- **Le moteur** est du Python déterministe. Les mêmes entrées donnent toujours le même résultat. La table des coefficients a une version.
- **Le satellite** calcule un indice et un drapeau de qualité. Une baisse de NDVI signale un changement du couvert. Elle ne prouve pas, seule, qu'il faut irriguer.
- **Le validateur** autorise `show_dose` ou renvoie `needs_check`. Le vent au-dessus de 15 km/h bloque le texte de pulvérisation.
- **L'explication** est le seul module autorisé à appeler un modèle de langage. Chaque nombre du texte existe déjà dans le JSON validé.

La consommation de la culture suit FAO-56 :

`ETc = Kc × ET0`

ETc est la consommation estimée, en millimètres par jour. Kc est le coefficient cultural du stade. ET0 est l'évapotranspiration de référence, calculée par Penman-Monteith à partir de la météo.

Jour d'exemple, verrouillé par un test : ET0 = 4,2 mm, Kc = 0,75, donc ETc = 3,15 mm. Ces valeurs sont un exemple de test, pas une mesure live d'une ferme.

Le moteur met ensuite à jour l'eau de la zone racinaire.

- Il ajoute l'irrigation déjà enregistrée.
- Il ajoute seulement la part utile de la pluie prévue. Le sol, l'intensité et le moment décident de cette part. Toute la prévision n'est pas retirée du besoin du jour.
- Il soustrait ETc.
- Il transforme le déficit net en dose brute selon l'efficience du goutte-à-goutte ou de l'irrigation de surface.

Une dose précise n'est montrée que si le stade est connu, la méthode d'irrigation est connue, la météo a moins de 48 heures, et l'image satellite, si elle existe, a au plus 10 jours avec au moins 70 % de pixels valides. Sinon le statut est `needs_check`. Les millimètres restent stockés. Ils ne sont pas présentés comme un ordre.

Exemple de carte quand la donnée est faible :

> Besoin à vérifier. La météo du jour est disponible. La dernière image satellite est trop ancienne. La dose précise n'est pas affichée tant que l'humidité du sol n'est pas confirmée.

## 4. Architecture

Un site Next.js sert l'agriculteur et le conseiller. Une API FastAPI porte le pipeline. PostgreSQL avec PostGIS garde les polygones. Redis file le travail du jour. La page et les notifications parlent à l'API. Aucun des deux n'invente une dose.

1. **Entrées.** Carte Leaflet + OpenStreetMap, formulaire, notification site ou Telegram.
2. **Orchestrateur.** Charge la parcelle et appelle les agents dans l'ordre.
3. **Calcul.** Météo, satellite, bilan, risque, validateur.
4. **Sortie.** Texte en trois langues, carte agriculteur, liste de visites.

### Les agents

| Agent | Rôle | Siège |
| --- | --- | --- |
| Orchestrateur | Charge le profil, enchaîne les appels, enregistre ce qui manque. | Backend |
| Météo | Température, humidité, vent, pluie et rayonnement Open-Meteo, avec l'heure de la requête. | Agronomie |
| Satellite | Sentinel-2, masque nuageux, NDVI, NDWI, date, part de pixels valides, image de vigueur. Sentinel-1 si l'optique est trop nuageuse. | Satellite |
| Agronome | ET0 Penman-Monteith, ETc, bilan racinaire, risque fongique, volume de bouillie, blocage vent. | Agronomie |
| Validateur | Unités, fraîcheur, stade, méthode. Il peut empêcher l'affichage d'une dose précise. | Backend |
| Explication | Darija, français, arabe, à partir du JSON et de pages FAO et INRA, via Ollama en local. Ask Qatra sur le site et depuis Telegram. | Explication |
| Interface | Carte Leaflet, écrans, notifications site ou Telegram, note vocale (Piper / Web Speech). Le texte part toujours avec l'audio. | Interface |

Si le modèle de langage est indisponible, un modèle de phrase écrit en code remplit les trois langues à partir des champs du JSON. La démonstration doit tenir avec le réseau du modèle coupé.

Le score de stress de la première version est calculé à partir du changement de NDVI, du déficit et du stade. Ces facteurs sont listés dans `reasons`. Ce n'est pas un modèle entraîné. Un modèle de stress appris viendrait plus tard, seulement avec des observations de terrain étiquetées.

Le risque de maladie de la première version s'appelle `fungal_risk`. Mildiou et oïdium sont des maladies de la vigne et des légumes. Ils ne sont pas les étiquettes des agrumes tant qu'un agronome n'a pas nommé la maladie de la culture.

## 5. La journée d'une parcelle

1. Le travailleur charge chaque parcelle active. Un appel `POST /plots/{id}/recommendation` lance le même chemin pour une seule parcelle, sans attendre minuit.
2. La météo et le satellite écrivent leurs observations. Chaque valeur garde sa source, son heure, ses unités et sa qualité. Une image absente reste nulle.
3. L'agronomie calcule ET0, ETc, le déficit, la dose brute, l'alerte et la décision de pulvérisation.
4. Le validateur pose `show_dose` ou `needs_check`, et autorise ou bloque la pulvérisation.
5. L'explication écrit les trois textes. L'interface ajoute la note vocale.
6. La ligne est stockée. La carte du site se met à jour. Une notification part seulement si la consigne a changé et si l'agriculteur a accepté les messages.

### Tests qui doivent passer

- ET0 = 4,2 mm et Kc = 0,75 donnent ETc = 3,15 mm.
- Les mêmes entrées rejouent la même sortie.
- Un NDVI manquant force `needs_check`.
- Une scène de plus de 10 jours force `needs_check`.
- Un vent de 16 km/h met `spray_blocked` à vrai.
- Les hauteurs d'eau restent en millimètres. Le vent reste en km/h.

## 6. Données et contrat

Quatre familles. Rien n'est inventé pour combler un trou.

| Famille | Source | Usage |
| --- | --- | --- |
| Météo | Open-Meteo. La Direction de la météorologie nationale si l'accès s'ouvre. | ET0, pluie passée, pluie prévue, vent. |
| Satellite | Sentinel-2 et Sentinel-1, via Copernicus Data Space (Earth Engine si éligible). FAO WaPOR plus tard. | Couvert, date, qualité. WaPOR pour une couche d'évapotranspiration sur le Maroc. |
| Parcelle | Ce que l'agriculteur déclare. | Culture, stade, âge, polygone, système, dernières irrigations, notes de sol. |
| Agronomie | FAO-56, coefficients commentés, INRA ou un agronome pour les valeurs locales. Bulletins publics du ministère pour l'explication. | Le calcul. Les bulletins ne remplacent pas la formule. |

Le fichier `docs/contract.json` est la forme commune. Un nom de champ ne change que si les cinq sont d'accord. Extrait du jour d'exemple, parcelle `MA-001` :

```json
{
  "plot_id": "MA-001",
  "crop": "citrus",
  "stage": "fruit_growth",
  "area_ha": 1.2,
  "irrigation_method": "drip",
  "et0_mm_day": 4.2,
  "et0_source": "penman_monteith",
  "kc": 0.75,
  "etc_mm": 3.15,
  "effective_rain_mm": 1.5,
  "gross_irrigation_mm": 4.7,
  "ndvi": 0.68,
  "ndvi_observed_at": "2026-10-11",
  "valid_pixel_pct": 86,
  "wind_kmh": 9,
  "spray_blocked": false,
  "disease_risk": "low",
  "status": "show_dose",
  "reasons": ["fruit_growth", "rain_reduces_need"],
  "engine_version": "0.1.0"
}
```

`ndvi` est nul s'il n'y a pas de scène optique utilisable. `status` vaut `show_dose` ou `needs_check`.

## 7. Technologies

| Pièce | Choix | Coût / note |
| --- | --- | --- |
| Cartographie | Leaflet + OpenStreetMap | Gratuit. Afficher la carte et dessiner les limites des parcelles. Remplace Mapbox. |
| Images satellitaires | Sentinel-1 / Sentinel-2 via Copernicus Data Space | Gratuit sous conditions. Google Earth Engine possible pour usages éligibles (recherche non commerciale). |
| API conversationnelle | Ollama, modèle open source en local | Sans frais d'API. Dépend des capacités matérielles de la machine. |
| Synthèse vocale | Piper ou Web Speech API | Gratuit en local. Tester la qualité des voix avant de trancher pour la darija. |
| Notifications | Notifications du site, ou Telegram Bot | Alternative gratuite à WhatsApp Cloud API, qui peut entraîner des coûts. |
| Site | Next.js, TypeScript, Leaflet | Un seul site, lisible sur téléphone et sur ordinateur. |
| API | Python, FastAPI | Orchestrateur, moteur, validateur, explication. Routes sous `/api/v1`. |
| Données | PostgreSQL, PostGIS, Redis | Polygones et surface. Redis file le travail quotidien. |
| Comptes | JWT, bcrypt | Agriculteur et conseiller. Les routes publiques d'authentification sont limitées. |
| Météo | Open-Meteo | Prévision de base sans clé. L'ET0 du service est gardé à côté du nôtre, comme contrôle. |
| Exécution | Docker Compose, GitHub Actions | API, PostGIS et Redis. Le test du chemin quotidien vient après. Prometheus et Grafana ensuite. |

### API

| Méthode | Chemin | Rôle |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | Créer un compte, rendre un JWT |
| POST | `/api/v1/auth/login` | Rendre un JWT |
| POST | `/api/v1/plots` | Créer une parcelle depuis un GeoJSON |
| GET | `/api/v1/plots` | Lister les parcelles de l'appelant |
| POST | `/api/v1/plots/{id}/recommendation` | Lancer le pipeline et stocker une ligne |
| GET | `/api/v1/plots/{id}/recommendations` | Historique |
| POST | `/api/v1/plots/{id}/ask` | Répondre depuis la dernière ligne |
| GET | `/api/v1/advisor/plots` | Parcelles liées : statut, stade, déficit, âge satellite, total de saison |
| POST | `/api/v1/telegram/webhook` | Question entrante (Telegram), vers Ask Qatra |

Tables : `farmers`, `plots`, `weather_observations`, `satellite_observations`, `irrigation_events`, `recommendations`, `messages`. Une recommandation garde la version du moteur et l'heure de chaque entrée, pour pouvoir être rejouée.

## 8. Écrans

**Agriculteur.** Carte du Maroc et ses parcelles. Formulaire. Carte de résultat : statut, raisons, ETc, heure de la prévision, date de l'image, décision de pulvérisation, trois langues, image de vigueur. Ask Qatra.

**Conseiller.** Carte colorée par statut. Liste de visites : stade sensible d'abord (floraison, grossissement), puis déficit le plus haut, avec l'âge de l'image. Bilan de saison : pluie, eau conseillée, besoin estimé.

Le site ou Telegram reprend le texte validé quand la consigne change. La note vocale s'ajoute si Piper ou Web Speech renvoie un fichier. Une question reçue sur Telegram suit le même chemin qu'Ask Qatra.

## 9. Cinq sièges, huit semaines

Cinq personnes, cinq sièges, même niveau. Les sièges peuvent bouger la première semaine. Ensuite ils restent fixes. Un dépôt, une branche par personne, une relecture par un coéquipier. Le lundi fixe le but. Le vendredi, chacun montre son travail sur la parcelle `MA-001`.

| Siège | Construit |
| --- | --- |
| Backend | Comptes, PostGIS, API, orchestrateur, validateur, Docker Compose. |
| Satellite | Copernicus Data Space, NDVI, NDWI, masque nuageux, repli Sentinel-1, images de vigueur, travail quotidien. |
| Agronomie | Open-Meteo, Penman-Monteith, bilan, règles de risque, volume de bouillie, tests. |
| Interface | Leaflet, tableaux de bord, notifications / Telegram, voix darija (Piper / Web Speech). |
| Explication | Textes, Ask Qatra, Ollama en local, test du chemin quotidien, puis GitHub Actions. |

| Semaine | Preuve |
| --- | --- |
| 1 · Contrat | Compose, parcelle exemple, une scène ou un blocage écrit, test 3,15 mm, carte Leaflet, darija et français. |
| 2 · Comptes | Inscription, polygone réel, météo live, NDVI et NDWI stockés, trois langues. |
| 3 · Bilan | Orchestrateur, masque nuageux, zone racinaire, formulaire aligné sur le contrat. |
| 4 · Une parcelle | Validateur sur MA-001, image de vigueur, heure de prévision et date d'image séparées. |
| 5 · Carte agriculteur | Historique, appel satellite en échec sans chute de l'API, volume de bouillie, Ask Qatra. |
| 6 · Conseiller | Liste conseiller, travail satellite quotidien, floraison et grossissement, notification ou Telegram. |
| 7 · Messages | Parcelles privées, drapeaux de qualité, blocage vent, note vocale, question qui reste sur la dose stockée. |
| 8 · Soutenance | README qui lance la pile, tests verts, démo téléphone et conseiller, trois langues même si le modèle est coupé. |

Le dépôt public est [github.com/AmineElAtrache/Qatra](https://github.com/AmineElAtrache/Qatra). Les dossiers déjà posés sont `backend/`, `web/` et `docs/`. Les secrets restent dans `.env`, jamais dans git.

## 10. Ce qui existe déjà

Qatra n'est pas la première aide à l'irrigation. La comparaison porte sur le travail réel : à quelle échelle, avec quel capteur, par quelle méthode, et avec quelle preuve de terrain. Les chiffres d'économie d'eau cités plus bas sont ceux publiés par ces produits. Ils ne sont pas des résultats de Qatra.

### Bulletin d'un ORMVA

Le conseil public de la plaine. Il est légitime, et il est le même pour beaucoup de parcelles. Il ne dessine pas un polygone, ne lit pas le stade de cet agrume, et n'explique pas pourquoi deux voisins devraient agir différemment cette semaine.

### FAO CROPWAT

Le logiciel de référence de la FAO pour calculer les besoins en eau selon la méthode FAO-56, à partir du climat, de la culture et du sol. C'est la famille de calcul que Qatra reprend. CROPWAT est un outil de bureau pour un technicien. Ce n'est pas une carte de téléphone, ni un message en darija, ni une liste de visites pour un conseiller.

### SOWIT / SOWATER

Produit marocain déjà en service. SOWATER calcule le besoin en eau de la parcelle à partir de la culture, d'un indice de végétation et de la météo, et donne un conseil du jour ainsi qu'un calendrier sur plusieurs jours. L'application peut aussi s'appuyer sur des capteurs de sol. SOWIT indique qu'une étude indépendante du programme USAID WE4F a mesuré, chez des clients, une économie d'eau d'environ 20 à 25 %. L'entreprise travaille avec de grandes exploitations et propose aussi un accès plus simple pour de plus petits agriculteurs. C'est le produit le plus proche, et il a l'avance du terrain : des fermes, des partenariats, dont l'INRA, et une mesure d'impact. Qatra ne reprend pas ce pourcentage.

### IrriWatch

Service commercial. Chaque matin, un conseil d'irrigation. L'humidité du sol et le stress sont estimés par satellite thermique, à l'échelle d'environ 10 mètres, puis un bilan poursuit les jours sans nouvelle image. Le plan couvre environ une semaine et classe les champs selon l'urgence. IrriWatch est en avance dès que la question est « combien d'eau reste dans le sol », parce que le thermique voit autre chose qu'un NDVI. C'est un abonnement, pas un moteur ouvert que cinq étudiants peuvent relire ligne à ligne.

| | Échelle | Capteur au champ | Méthode | Preuve |
| --- | --- | --- | --- | --- |
| Bulletin ORMVA | Plaine | Non | Conseil régional | Pratique officielle |
| CROPWAT | Calcul culture | Non | FAO-56 | Référence FAO |
| SOWATER | Parcelle | Optionnel | Satellite, météo, culture | Fermes, étude WE4F citée par SOWIT |
| IrriWatch | Pixel d'environ 10 m | Non | Thermique et bilan | Produit commercial quotidien |
| Qatra | Parcelle dessinée | Non pour commencer | FAO-56, NDVI comme signal, validateur | Prototype de cours, pas encore de mesure d'économie |

## 11. Où Qatra est le meilleur choix

Qatra est le meilleur choix pour une question précise : expliquer, en darija, en français et en arabe, le besoin en eau d'une parcelle d'agrumes que l'on vient de dessiner, sans installer de capteur, avec un chiffre que l'on peut rejouer, et avec le même chiffre sur la carte du conseiller.

- **Mieux que le bulletin.** La consigne change avec le stade, la pluie de ce point et la date de l'image. Deux parcelles voisines peuvent recevoir deux statuts.
- **Mieux que CROPWAT seul.** Le calcul FAO-56 arrive sur un téléphone, avec la qualité de la donnée écrite à côté, et avec une liste de visites.
- **Plus lisible qu'un NDVI brut.** L'indice ne conclut pas seul. Le validateur peut cacher la dose. L'explication ne peut pas ajouter un millimètre.
- **Ouvert pour le cours.** Données publiques, moteur en Python, contrat JSON, cinq modules que l'on peut défendre un par un.

Qatra n'est pas en avance sur SOWATER pour l'usage réel, ni sur IrriWatch pour l'humidité du sol vue par thermique. Ces deux services ont des agriculteurs aujourd'hui. Qatra est un prototype. Il devient crédible le jour où un agronome a relu les coefficients, puis le jour où une saison de parcelles permet de comparer la dose conseillée à l'eau réellement apportée.

Le résultat est une aide à la décision. L'agriculteur vérifie encore le sol avant de changer un tour d'eau réel. Aucune économie d'eau et aucun gain de rendement ne sont annoncés tant qu'un pilote ne les a pas mesurés.

## 12. Sources

1. Allen, R. G., Pereira, L. S., Raes, D., Smith, M. *Crop evapotranspiration — Guidelines for computing crop water requirements*. FAO Irrigation and Drainage Paper 56, 1998.
2. FAO. CROPWAT. [fao.org/land-water/databases-and-software/cropwat](https://www.fao.org/land-water/databases-and-software/cropwat/en/).
3. SOWIT. SOWATER, pilotage de l'irrigation. [sowit.fr/pilotage-de-lirrigation](https://sowit.fr/pilotage-de-lirrigation/).
4. FreshPlaza. Entretien avec SOWIT sur l'étude USAID / WE4F et les 20 à 25 % cités par l'entreprise. Article 9517088.
5. IrriWatch. Brochure *The root of effective irrigation*. Conseil quotidien, satellite thermique, plan de plusieurs jours.
6. Open-Meteo, Copernicus Sentinel-2 et Sentinel-1, FAO WaPOR. Données publiques utilisées ou prévues par Qatra.
