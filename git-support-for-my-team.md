# Workflow Git & Conventions de Commit

>  **Règle d'or :** Ne codez jamais directement sur `main` ou `develop`. Travaillez toujours sur une branche dédiée (`feat/...`, `fix/...`, `test/...`).

---

##  Conventions de Commit

* **`feat`** : Ajout d'une nouvelle fonctionnalité
* **`test`** : Ajout de tests juste après le code ou la correction d'un bug
* **`refactor`** : Nettoyage ou restructuration du code sans modifier son comportement
* **`fix`** : Correction d'un bug trouvé pendant les tests ou la revue

---

## Exemple d'historique de commits (`feat/auth`)

### Chronologie des modifications

1. `feat(auth): add login endpoint with email and password`
2. `test(auth): add unit tests for login endpoint`
3. `refactor(auth): extract password validation to separate service`
4. `fix(auth): correct error message for invalid credentials`
5. `test(auth): add test for invalid credentials case`

### Rendu avec `git log`

```text
9f3a2c1 test(auth): add test for invalid credentials case
7b1e8d4 fix(auth): correct error message for invalid credentials
4c2f9a0 refactor(auth): extract password validation to separate service
2d8e6b3 test(auth): add unit tests for login endpoint
1a5c4e2 feat(auth): add login endpoint with email and password

```

---

##  Guide du Workflow Étape par Étape

### 1. Mettre à jour la branche de base locale

```bash
git checkout develop
git pull origin develop

```

### 2. Créer et basculer sur votre branche

```bash
git checkout -b feat/auth

```

### 3. Coder & tester en local

Travaillez normalement et lancez le projet localement pour tester (ex. : `npm run dev`).

### 4. Indexer et commiter les changements

```bash
git add .
git commit -m "feat(auth): add login endpoint"

```

### 5. Pousser la branche sur le dépôt distant

```bash
git push -u origin feat/auth

```

### 6. Créer une Pull Request (PR)

Rendez-vous sur GitHub, puis créez une Pull Request de `feat/auth` vers `main` (ou `develop`).

### 7. Nettoyer après la fusion (merge)

```bash
git checkout main
git pull origin main
git branch -d feat/auth

```

---

##  Ajout de Tests en cours de route

1. Ajoutez un test dans `tests/test_auth.py`.
2. Commitez vos modifications :
```bash
git commit -m "test(auth): add unit test for login endpoint"

```


3. Poussez les mises à jour sur votre branche :
```bash
git push origin feat/auth

```