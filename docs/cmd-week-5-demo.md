# Démo Week 5 — Ask Qatra hors ligne

Guide pas à pas pour lancer la page web, vérifier les services et présenter le
scénario MA-001. Les explications à dire au professeur sont en français.

> Les valeurs MA-001 ci-dessous sont des données de démonstration, pas une
> recommandation agricole réelle : olive, irrigation enregistrée de 4,5 mm sur
> 2 heures, risque fongique moyen, pulvérisation non bloquée, vent enregistré
> à 12 km/h. La température maximale est `28` sans unité fournie par le mock.

## 1. Ouvrir un terminal à la racine du dépôt

```bash
cd /chemin/vers/Qatra
pwd
```

Le résultat de `pwd` doit se terminer par `/Qatra`.

**À dire :** « Je vais présenter Ask Qatra. La page affiche le dernier état
local de démonstration et répond à une question dans la langue demandée. »

## 2. Démarrer PostgreSQL et l’API

Dans le premier terminal :

```bash
docker compose up -d db
docker compose ps db
docker compose build api
docker compose up -d --no-deps api
```

`docker compose ps db` doit indiquer que la base est `healthy`. Vérifier ensuite
l’API :

```bash
curl -fsS http://localhost:8000/api/v1/health
```

Résultat attendu :

```json
{"status":"ok","service":"qatra-api"}
```

**Pourquoi ne pas lancer tout Compose ?** Si Redis est déjà lancé sur la
machine, le service Redis de Compose peut échouer à réserver le port `6379`.
Cette démo n’a pas besoin de Redis : on démarre la base, puis l’API sans
redémarrer ni arrêter le Redis existant.

**À dire :** « L’API lit le snapshot JSON local et les références statiques
FAO/INRA. Ollama n’est pas nécessaire pour produire la réponse. »

## 3. Démarrer la page web

Dans un deuxième terminal :

```bash
cd /chemin/vers/Qatra/web
npm ci
npm run build
npm run start -- --hostname 0.0.0.0 --port 3000
```

`npm ci` est nécessaire seulement à la première installation ou si les
dépendances ne sont pas présentes. Attendre le message de démarrage, puis
ouvrir :

**http://localhost:3000/demo/ask**

Ne pas exécuter `npm run build` pendant que `npm run dev` sert la page : les
deux commandes utilisent le même dossier de build `.next`.

**À dire :** « Voici l’interface de démonstration. Elle présente la question,
la réponse, la disponibilité d’Ollama, l’état MA-001 et les références
disponibles. »

## 4. Vérifier les données du scénario

Dans un troisième terminal, à la racine du dépôt :

```bash
cat backend/app/services/data/last_stored_state.json
```

Le snapshot de démonstration contient notamment `plot_id: MA-001`,
`water_volume_mm: 4.5`, `duration_hours: 2`, `fungal_risk: MEDIUM` et
`spray_blocked: false`.

**À dire :** « Ces valeurs viennent du fichier JSON de démonstration. La page
les marque explicitement comme un exemple, et non comme une mesure du jour. »

## 5. Poser une question en français

Dans la page, saisir :

```text
Faut-il irriguer les oliviers aujourd’hui ?
```

Puis cliquer sur **Demander à Qatra**.

Résultat attendu : une réponse en français qui réutilise la valeur enregistrée
de **4,5 mm**, la durée de **2 heures**, le risque fongique moyen et
l’information que la pulvérisation n’est pas bloquée.

**À dire :** « La réponse est construite à partir de l’état enregistré. Le
moteur n’ajoute pas de mesure d’irrigation qui n’existe pas dans le JSON. »

## 6. Tester la question en arabe

Remplacer la question par :

```text
هل يجب أن أسقي المحصول؟
```

Cliquer sur **Demander à Qatra**. La langue arabe doit être sélectionnée
automatiquement. Résultat attendu : la même recommandation et les mêmes
valeurs que dans la réponse française, mais formulées en arabe, par exemple
**4.5 مم لمدة 2 ساعة**.

**À dire :** « Le changement de langue ne change pas la recommandation : les
trois langues utilisent le même état enregistré. Seule la formulation change. »

## 7. Montrer les langues et les références

Utiliser les boutons **Français**, **English** et **العربية**. La page rappelle
que l’état MA-001 est un exemple et affiche les fichiers de référence FAO/INRA.

**À dire :** « Les citations sont extraites des références statiques. Elles
apportent un contexte qualitatif; elles ne servent pas à calculer ou inventer
des millimètres. »

## 8. Montrer le mode sans Ollama (facultatif)

Vérifier d’abord le statut d’Ollama :

```bash
systemctl is-active ollama
```

Si le service est actif et que vous avez les droits administrateur, l’arrêter
pour ce test :

```bash
sudo systemctl stop ollama
```

Envoyer de nouveau une question sur la page. L’indicateur doit afficher
**Ollama indisponible**; la réponse fondée sur le snapshot et les références
doit toujours apparaître.

Pour rétablir Ollama après la présentation :

```bash
sudo systemctl start ollama
systemctl is-active ollama
```

Si Ollama est déjà arrêté, ne pas lancer la commande `stop`. Si Ollama n’est
pas géré par `systemd`, ignorer cette étape facultative et présenter l’état
actuel indiqué dans la page.

**À dire :** « J’ai vérifié le chemin de fallback : même sans Ollama, Ask
Qatra continue de répondre de façon déterministe avec les données locales. »

## 9. Vérifier directement la réponse de l’API (facultatif)

À la racine du dépôt :

```bash
curl -fsS -X POST http://localhost:8000/api/v1/demo/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"هل يجب أن أسقي المحصول؟","language":"ar"}'
```

La réponse JSON doit contenir `language: "ar"`, `status: "RECOMMENDED"`,
`is_sample: true` et `metrics.water_volume_mm: 4.5`.

**À dire :** « Cette vérification montre que l’interface appelle l’API de
démonstration et que l’API retourne les champs utiles sans exposer l’intégralité
du JSON stocké. »

## 10. Arrêter les services après la démonstration

Arrêter le serveur web avec **Ctrl+C** dans son terminal. Puis, si vous avez
démarré ces conteneurs spécialement pour la démo :

```bash
docker compose stop api db
```

Ne pas exécuter `docker compose down -v` : cette commande supprimerait les
volumes de données de Compose.

## Texte de conclusion (à dire au professeur)

« Pour conclure, Ask Qatra partage le même service de réponse entre l’interface
et les webhooks. En mode hors ligne, il lit le dernier état JSON et les
références FAO/INRA. Les réponses sont disponibles en français, anglais et
arabe. Les mesures d’irrigation ne sont affichées que si elles sont présentes
dans l’état enregistré; le système ne les estime pas. »
