# Rapport d'intelligence concurrentielle : CROPWAT [https://cropwat.informer.com/8.0/]

**Analyzed by:** DevOps Engineer Zakariae

## 1. Présentation et positionnement

### 1.1 Qu'est-ce que CROPWAT ?

CROPWAT est un logiciel de bureau développé par la Division des terres et des eaux de la FAO. Il calcule :

* l'évapotranspiration de référence (ET₀) par la méthode de Penman-Monteith ;
* les besoins en eau des cultures et les besoins en irrigation ;
* des calendriers d'irrigation selon différentes hypothèses de gestion ;
* des estimations à l'échelle d'un périmètre irrigué, à partir d'un assolement.

Il s'appuie sur la **publication FAO n° 56 (Irrigation and Drainage Paper 56)**, devenue la méthode de calcul de référence mondiale, et sur la base de données climatiques **CLIMWAT** (moyennes climatiques de milliers de stations). Il est utilisé depuis des décennies dans les projets de développement, les universités et les administrations de l'eau. Son statut est celui d'un **outil étalon**, plus que d'un produit commercial.

### 1.2 Modèle et cible

* **Modèle économique :** gratuit, institutionnel, sans objectif commercial.
* **Utilisateurs principaux :** chercheurs, agronomes, ingénieurs hydrauliciens, bureaux d'études, ONG, ministères, bailleurs de fonds.
* **Cas d'usage typiques :** dimensionnement de projets, études de planification, enseignement, évaluation de politiques de l'eau.
* **Utilisateurs peu ciblés :** exploitants agricoles connectés, conseillers de terrain en temps réel, exploitations commerciales en agriculture de précision.

### 1.3 Lecture des lignes du tableau (selon la description)

* **« Calcul culture » : Oui.** C'est la fonction cœur : le calcul des besoins en eau par culture et par stade de développement. Sur ce terrain, CROPWAT est irréprochable et ne peut pas être attaqué frontalement.
* **« Non ».** Cela se rapporte aux fonctionnalités modernes absentes : connectivité IoT, cloud natif, automatisation des données, alertes, application mobile. C'est le principal angle d'attaque. Il faut vérifier à quelle ligne exacte du tableau ce « Non » correspond avant de l'utiliser dans un argumentaire.
* **« FAO-56 ».** Le standard scientifique sous-jacent. C'est à la fois sa force (légitimité) et un terrain commun : notre solution doit être au minimum compatible avec FAO-56 pour être crédible.

---

## 2. Points forts

### 2.1 Crédibilité scientifique et institutionnelle

* La marque FAO confère une autorité quasi incontestable auprès des gouvernements, des bailleurs (Banque mondiale, FIDA, agences de coopération) et du monde académique.
* FAO-56 est la méthode enseignée, citée dans les publications et exigée dans de nombreux cahiers des charges. Un résultat « conforme à CROPWAT » est perçu comme validé.
* Les décideurs publics y voient un choix sans risque : personne n'est blâmé pour avoir utilisé l'outil de la FAO.

### 2.2 Gratuité et accessibilité

* Aucun coût de licence, ce qui le rend très attractif pour les pays à faibles ressources, les universités et les projets financés sur fonds publics.
* Large base d'utilisateurs, de tutoriels, de formations et de documentation, y compris en plusieurs langues.
* Léger et exécutable sur des machines modestes, sans connexion permanente (atout dans les zones à connectivité limitée).

### 2.3 Fiabilité et standardisation

* Méthodologie stable, transparente et auditée, avec des résultats reproductibles.
* Il sert de **référence de validation** : de nombreux logiciels et chercheurs comparent leurs résultats aux siens.
* La transparence des hypothèses (coefficients culturaux Kc, stades, coefficients de réponse) rassure les experts.

---

## 3. Points faibles

### 3.1 Expérience utilisateur obsolète

* Interface de logiciel de bureau ancienne, à forte courbe d'apprentissage, avec une navigation par modules et une saisie fastidieuse.
* Visualisation et rapports limités, peu adaptés à la communication auprès d'un exploitant ou d'un décideur non expert.
* Il faut généralement une formation ou une bonne connaissance de la méthodologie pour obtenir des résultats exploitables.

### 3.2 Absence de temps réel et d'automatisation

* Pas d'intégration native avec des capteurs d'humidité du sol, des stations météo connectées ou des données satellitaires (NDVI, évapotranspiration estimée par télédétection).
* Il s'appuie sur des données climatiques moyennes ou saisies manuellement : il est plus **planificateur** que **conseiller opérationnel** et ne réagit pas à la météo de la semaine.
* Pas d'alertes, pas de recommandations automatiques « irriguer maintenant / dans 48 h ».

### 3.3 Collaboration et interopérabilité limitées

* Fichiers locaux, sans synchronisation cloud, sans travail collaboratif ni gestion multi-utilisateurs.
* Échange de données difficile avec les outils modernes (API, SIG, ERP agricoles, outils de gestion de parcelles).
* Pas de logique de suivi par exploitation, parcelle ou équipe.

### 3.4 Rigidité

* Peu adapté à la logique de précision à l'échelle de la parcelle ou de la zone de gestion, ni à la gestion de plusieurs cultures et campagnes dans un tableau de bord.
* Ne tient pas compte de dimensions décisionnelles qui préoccupent les exploitants : coût de l'énergie, rentabilité, contraintes de pompage, fertigation, tours d'eau.
* Évolutions lentes, liées au rythme institutionnel de la FAO.

---

## 4. Matrice SWOT (de notre point de vue)

### Forces de CROPWAT (à respecter ou contourner)

* Autorité FAO et standard FAO-56
* Gratuité
* Référence de validation
* Large communauté et documentation
* Fonctionne hors ligne

### Faiblesses de CROPWAT (à attaquer)

* UX/UI vieillissante
* Pas d'IoT, de temps réel ni d'automatisation
* Pas de cloud ni de collaboration
* Faible adaptation à l'agriculture de précision
* Pas de logique décisionnelle économique

### Opportunités pour notre solution

* Digitalisation de l'agriculture et pression sur l'eau (sécheresses, quotas)
* Disponibilité croissante de capteurs et de données satellitaires bon marché
* Exploitations commerciales prêtes à payer pour le gain d'eau, d'énergie et de rendement
* Besoin d'outils mobiles et d'alertes pour le terrain
* Positionnement possible en « couche moderne » complémentaire de FAO-56

### Menaces

* Perception du « gratuit suffit » et inertie des institutions
* Prescription par les bailleurs et les cahiers des charges publics
* Risque que la FAO ou des partenaires modernisent l'offre
* Scepticisme envers les modèles « boîte noire » privés
* Autres acteurs AgTech et outils gratuits concurrents

> **Implication stratégique :** Ne pas se battre sur la science, mais sur l'usage. Nous ne remplaçons pas FAO-56, nous le rendons opérationnel, automatisé et connecté.

---

## 5. Recommandations stratégiques et battlecards

### 5.1 Positionnement

**Message central :** *« La rigueur de FAO-56, sans la complexité. »* Nous transformons un calcul de planification en décision d'irrigation quotidienne, automatique et mesurable.

**À faire :**

* Rendre notre moteur **conforme à FAO-56** et le dire explicitement. Publier des comparaisons de résultats avec CROPWAT pour neutraliser l'objection scientifique.
* Se présenter comme **complémentaire** auprès des institutions (« construit sur le standard FAO »), et comme **successeur opérationnel** auprès des exploitants.
* Éviter de dénigrer CROPWAT, ce qui coûterait en crédibilité. Le critiquer sur l'usage, pas sur la science.

### 5.2 Battlecard synthétique

* **Objection : « CROPWAT est gratuit et de la FAO. »**
*Réponse :* Notre moteur suit la même méthode FAO-56. Vous gardez la rigueur, et vous ajoutez les données en temps réel, les alertes et le suivi, qui font gagner du temps et de l'eau. Le coût du logiciel est faible face aux économies d'eau, d'énergie et de main-d'œuvre.
* **Objection : « C'est la référence, pas besoin d'autre chose. »**
*Réponse :* C'est la référence pour calculer. Nous sommes la référence pour décider et agir chaque jour sur chaque parcelle.
* **Objection : « Vos calculs sont-ils fiables ? »**
*Réponse :* Présenter la validation croisée avec CROPWAT, la méthodologie documentée et, si possible, des essais de terrain ou une validation académique.
* **Objection : « Mes équipes sont déjà formées à CROPWAT. »**
*Réponse :* Import et export compatibles, prise en main en quelques minutes, onboarding accompagné.

### 5.3 Axes de différenciation clés

1. **Expérience utilisateur :** Interface web et mobile intuitive, sans formation préalable, rapports lisibles par des non-experts.
2. **Automatisation des données :** Météo en temps réel et prévisions, capteurs IoT, satellite ; plus de saisie manuelle.
3. **Aide à la décision en temps réel :** Recommandations « quand et combien irriguer », alertes de stress hydrique, ajustement selon les prévisions.
4. **Collaboration et cloud :** Multi-parcelles, multi-utilisateurs, historiques, partage entre agriculteur, conseiller et gestionnaire.
5. **Interopérabilité :** API, intégration aux SIG, aux équipements d'irrigation et aux outils de gestion d'exploitation.
6. **Valeur économique :** Indicateurs d'eau économisée, d'énergie et de rendement, pour justifier le retour sur investissement.
7. **Support et accompagnement :** Assistance réactive, formation, onboarding, ce qu'un outil institutionnel gratuit ne fournit pas.

### 5.4 Segmentation recommandée

* **Cibles prioritaires :** exploitations commerciales, coopératives, groupements d'irrigants, conseillers agricoles, domaines à forte valeur (arboriculture, maraîchage, cultures irriguées sous contrainte hydrique).
* **Cible à traiter par partenariat :** institutions et universités. Les approcher en complément de CROPWAT (compatibilité, données ouvertes) plutôt qu'en remplacement.
* **Preuves à produire :** études de cas chiffrées (m³ économisés, gains d'énergie, rendement) et validation comparative avec FAO-56.

---

## 6. Positionnement sur le marché marocain

Un agriculteur simple n'adoptera pas la solution seul et telle quelle : la cible rentable à court terme est l'exploitation moyenne ou grande, et les petits exploitants ne seront atteints qu'à travers un intermédiaire (coopérative, installateur, conseiller, office régional) et une version très simplifiée.

### 6.1 Contexte du marché

* La stratégie [Génération Green 2020-2030](https://fnh.ma/article/actualites-marocaines/e-services-agricoles-le-maroc-veut-connecter-2-millions-d-agriculteurs-et-d-usagers-a-l-horizon-2030) place la digitalisation au cœur de la politique agricole et vise 2 millions d'agriculteurs connectés à des e-services d'ici 2030.
* L'irrigation localisée couvrait [824 000 ha fin 2023](https://www.lavieeco.com/?p=342764), avec un objectif d'un million d'hectares en 2030. Le goutte-à-goutte représente [plus de la moitié de la surface irriguée](https://www.lavieeco.com/affaires/agriculture/irrigation-lapproche-nexus-change-la-donne/?rand=19084). Ces parcelles équipées sont une base naturelle pour une solution de pilotage.
* Le programme national d'économie d'eau en irrigation (PNEEI), [lancé en 2022](https://maroc.ma/index%2Ephp/fr/actualites/region-de-loriental-des-projets-structurants-et-innovants-pour-moderniser-lirrigation-et-atteindre-la), crée un climat favorable aux outils d'efficacité hydrique.
* Selon [Le360](https://fr.le360.ma/economie/agritech-la-necessaire-revolution_7KSIN2HRINFCPLGKV2IODOVCRI/), les grandes exploitations avancent vite en AgriTech, alors que les petits agriculteurs peinent à suivre.
* La presse économique note que l'[adoption des petits agriculteurs est lente](https://maroc-diplomatique.net/lagritech-au-coeur-de-la-revolution-agricole-du-maroc/) et demande un accompagnement de proximité et des modèles économiques adaptés (partage de données, location de services).

### 6.2 Qui utilisera la solution ?

| Segment | Probabilité d'adoption | Raison principale | Voie d'accès |
| --- | --- | --- | --- |
| **Exploitations d'export** (agrumes, maraîchage, petits fruits) | Élevée | Gain d'eau et d'énergie, rentabilité, exigences des acheteurs | Vente directe |
| **Exploitations moyennes irriguées** | Moyenne à élevée | Goutte-à-goutte déjà installé, pression sur l'eau | Vente directe, installateurs |
| **Coopératives et associations d'usagers** | Moyenne | Gestion collective, tours d'eau, appui technique | B2B2C, partenariats |
| **Petit agriculteur individuel** (< 2 ha) | Faible en direct | Budget, usage numérique, langue, connectivité | Via coopérative, conseiller ou programme public |
| **Offices régionaux, bailleurs, universités** | Partenariat | Compatibilité avec FAO-56 et CROPWAT | Partenariat, pilotes |

### 6.3 Pourquoi le petit agriculteur résiste

* **Coût :** Une [étude du CIRAD dans le Gharb](https://revues.cirad.fr/index.php/cahiers-agricultures/article/download/30899/30659/31134) montre que le coût d'installation limite l'accès des petits exploitants à un goutte-à-goutte conforme ; beaucoup recourent à des installations informelles à bas coût. Un outil de pilotage vient après cet investissement.
* **Usage du numérique :** Une application riche en menus et en graphiques n'est pas adaptée à un utilisateur peu à l'aise avec le numérique.
* **Langue :** Un outil en français ou en anglais exclut une partie des utilisateurs ; l'arabe, la darija et l'amazigh sont nécessaires (hypothèse à valider sur le terrain).
* **Connectivité et confiance :** Couverture rurale inégale, méfiance envers les abonnements et envers une recommandation que l'on ne voit pas.

### 6.4 Conditions pour qu'il l'adopte

* **Une recommandation, plutôt qu'un tableau de bord :** Un message court du type *« irriguer demain matin, 40 minutes »*, par WhatsApp, SMS ou notification vocale.
* **Interface en arabe et en darija**, avec icônes et audio.
* **Fonctionnement sans capteurs :** Météo, satellite et méthode FAO-56 suffisent pour démarrer ; les capteurs restent optionnels.
* **Tolérance à la faible connectivité**, avec synchronisation différée.
* **Prix et paiement adaptés :** Abonnement saisonnier ou mensuel faible, paiement mobile, ou financement par un programme public, une coopérative ou un acheteur.
* **Intermédiaires de confiance :** Coopératives, installateurs de goutte-à-goutte, conseillers agricoles, offices régionaux.
* **Preuve visible :** Parcelles de démonstration avec eau économisée chiffrée.

### 6.5 Positionnement recommandé en trois étapes

1. **Étape 1 (Exploitations moyennes et grandes) :** Vente directe, preuves chiffrées (m³, énergie, rendement), validation FAO-56 pour rassurer les ingénieurs.
2. **Étape 2 (Coopératives et associations d'usagers) :** Modèle B2B2C, un compte coopérative qui sert plusieurs adhérents, formation des conseillers.
3. **Étape 3 (Petits agriculteurs) :** Version allégée par WhatsApp ou SMS, distribuée par des intermédiaires et adossée à des programmes publics ou de bailleurs.

*Face à CROPWAT au Maroc, notre rôle est complémentaire : l'outil FAO reste l'étalon pour les études et la planification, nous apportons le conseil quotidien et le suivi à la parcelle.*

### 6.6 Points à valider sur le terrain

* Prix que chaque segment accepte de payer et part des subventions mobilisables.
* Part réelle de smartphones et de WhatsApp chez les clients cibles, par région.
* Acteurs AgriTech locaux déjà actifs (par exemple AgriEdge, cité dans la presse) et leur offre.
* Niveau d'usage actuel de CROPWAT dans les offices régionaux et les universités marocaines.
