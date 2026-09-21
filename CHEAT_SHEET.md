# Cheat Sheet - JS Listener

Guide rapide des options, syntaxes, combinaisons et résultats attendus.

> Utiliser JSL uniquement sur des systèmes et domaines explicitement autorisés. Un fichier `--in-scope` ne remplace pas l'autorisation du propriétaire.

## 1. Commandes disponibles

Après `./setup_env.sh`, les commandes globales utilisent automatiquement `.venv` et peuvent être lancées depuis n'importe quel dossier.

| Commande | Rôle |
|---|---|
| `js-listener` | Lance le listener Playwright. |
| `jslistener-db-reader` | Lit une base SQLite et produit un rapport. |
| `jslistener-secret-scan` | Recherche des secrets et artefacts sensibles. |
| `jslistener-test` | Lance le test d'intégration. |

Aide de chaque commande :

```bash
js-listener --help
jslistener-db-reader --help
jslistener-secret-scan --help
```

## 2. Syntaxe minimale

### Listener

```bash
js-listener --target https://example.com --in-scope ./in-scope.txt
```

Résultat attendu :

- navigateur Chromium visible ;
- mode initial `ctv` ;
- base `/tmp/js_listener.sqlite3` ;
- observation des requêtes autorisées `fetch`/`XHR` ;
- arrêt automatique après 180 secondes d'inactivité.

### Lecteur SQLite

```bash
jslistener-db-reader --db /tmp/js_listener.sqlite3
```

Résultat attendu : rapport texte des sessions, ressources, événements réseau, cookies et domaines.

### Scanner

```bash
jslistener-secret-scan --history
```

Résultat attendu : rapport JSON dans le terminal. Le code de sortie est `0` sans finding critique ou élevé, `1` si un finding critique ou élevé est détecté.

## 3. Modes de collecte

### CTV : trafic observable

```bash
js-listener \
  --target https://example.com \
  --mode ctv \
  --in-scope ./in-scope.txt
```

Collecte principalement les requêtes `fetch` et `XHR` : méthode, URL, statut, MIME, taille, redirection et erreur réseau.

Résultat dans SQLite : table `network_events`.

### CTG : cartographie technique

```bash
js-listener \
  --target https://example.com \
  --mode ctg \
  --in-scope ./in-scope.txt
```

Collecte les ressources JavaScript, MJS et JSON, leur statut, MIME, taille, hash et dépendance avec la page.

Résultat dans SQLite : tables `resources` et `dependencies`, journal optionnel `--js-log`.

### Basculer pendant une session

```bash
kill -USR1 <PID>
```

`ctv` devient `ctg`, puis `ctg` devient `ctv`. Chaque transition est écrite dans `mode_changes` et `events`.

Une nouvelle navigation ou interaction est nécessaire après le changement pour observer les nouvelles données dans le mode actif.

## 4. Options générales

| Option | Syntaxe | Résultat |
|---|---|---|
| Cible | `--target URL` ou `-t URL` | Définit l'URL initiale. Obligatoire. |
| User-Agent | `--user-agent "VALEUR"` ou `-u "VALEUR"` | Utilise le User-Agent choisi. |
| Mode | `--mode ctv` ou `--mode ctg` | Définit le mode initial. Défaut : `ctv`. |
| Périmètre | `--in-scope ./in-scope.txt` | N'enregistre que les URLs correspondant au fichier. |
| Base | `--db /chemin/session.sqlite3` | Change la base SQLite. Les fichiers SQLite sont protégés en `600`. |
| Pause | `--sleep 2` | Vérifie l'état toutes les 2 secondes. |
| Inactivité | `--inactivity 60` | Arrêt après 60 secondes sans activité. |
| Pas d'arrêt automatique | `--inactivity 0` | Désactive l'arrêt pour inactivité. À surveiller manuellement. |
| Navigateur sans interface | `--headless` | Lance Chromium sans fenêtre visible. |
| Effacer les cookies | `--clear-cookies` | Supprime les cookies du contexte avant la navigation. |

Exemple de session contrôlée :

```bash
js-listener \
  -t https://example.com \
  --mode ctv \
  --in-scope ./in-scope.txt \
  --db /tmp/client-session.sqlite3 \
  --sleep 1 \
  --inactivity 120
```

## 5. Cookies : combinaisons

### Aucune capture de cookie, recommandé par défaut

```bash
js-listener -t https://example.com --in-scope ./in-scope.txt
```

Résultat : aucune ligne ajoutée à `cookies`, aucune valeur enregistrée.

### Métadonnées uniquement

```bash
js-listener \
  -t https://example.com \
  --in-scope ./in-scope.txt \
  --capture-cookies \
  --cookie-log /tmp/client-cookie-log.jsonl
```

Résultat : domaines, noms, chemins, expiration et attributs sont enregistrés dans SQLite et JSONL. Les valeurs ne sont pas enregistrées.

### Valeurs de cookies, uniquement en cas de nécessité absolue

```bash
js-listener \
  -t https://example.com \
  --in-scope ./in-scope.txt \
  --capture-cookies \
  --capture-cookie-values \
  --secrets /tmp/client-secrets.json
```

Résultat : les valeurs sont écrites dans le fichier de secrets. Ce fichier peut contenir des tokens de session et doit rester privé, en `600`, puis être supprimé après analyse.

### Combinaison invalide

```bash
js-listener -t https://example.com --capture-cookie-values
```

Résultat attendu : erreur CLI, car `--capture-cookie-values` nécessite `--capture-cookies`.

## 6. Réponses JS/JSON : combinaisons

### Métadonnées seulement, recommandé

```bash
js-listener \
  -t https://example.com \
  --mode ctg \
  --in-scope ./in-scope.txt
```

Résultat : URL, statut, MIME, taille et hash selon les ressources observées ; aucun corps de réponse sauvegardé.

### Sauvegarde limitée des corps

```bash
js-listener \
  -t https://example.com \
  --mode ctg \
  --in-scope ./in-scope.txt \
  --capture-response-bodies \
  --response-dir /tmp/client-responses \
  --max-response-size 1048576
```

Résultat : corps JS/JSON de 1 MiB maximum sauvegardés dans le dossier indiqué, avec nom basé sur SHA-256. Les réponses plus grandes ne sont pas sauvegardées.

`--capture-response-bodies` peut exposer des données personnelles, des tokens et du contenu métier.

Combinaison invalide :

```bash
js-listener -t https://example.com --max-response-size 0
```

Résultat attendu : erreur CLI, car la taille maximale doit être positive.

## 7. TLS et sandbox Chromium

### Configuration sécuritaire par défaut

```bash
js-listener \
  -t https://example.com \
  --in-scope ./in-scope.txt \
  --no-ignore-https-errors
```

Résultat : validation des certificats TLS active. Cette option est implicite par défaut.

### Exception TLS, environnement contrôlé uniquement

```bash
js-listener \
  -t https://site-de-test.local \
  --in-scope ./in-scope.txt \
  --ignore-https-errors
```

Résultat : les erreurs de certificat sont ignorées. Risque d'interception ou de mauvaise configuration TLS non détectée.

### Sandbox actif, recommandé

```bash
js-listener -t https://example.com --in-scope ./in-scope.txt
```

Le sandbox Chromium est actif par défaut.

### Désactiver le sandbox, exception seulement

```bash
js-listener \
  -t https://example.com \
  --in-scope ./in-scope.txt \
  --no-sandbox
```

Résultat : Chromium est lancé sans sandbox. Réserver à une machine ou un conteneur dédié, avec un compte sans privilèges.

Combinaison invalide :

```bash
js-listener -t https://example.com --ignore-https-errors --no-ignore-https-errors
```

Résultat attendu : erreur CLI, car ces options sont mutuellement exclusives.

## 8. JSON et rapports

### Export JSON de la session

```bash
js-listener \
  -t https://example.com \
  --in-scope ./in-scope.txt \
  --output /tmp/session-report.json
```

Résultat : écrit le rapport complet dans le fichier et l'affiche aussi dans le terminal.

### Affichage JSON sans fichier

```bash
js-listener \
  -t https://example.com \
  --in-scope ./in-scope.txt \
  --json
```

Résultat : affiche le rapport complet dans le terminal.

### Lire une base en texte

```bash
jslistener-db-reader --db /tmp/session.sqlite3
```

### Lire une base en JSON

```bash
jslistener-db-reader --db /tmp/session.sqlite3 --json
```

### Lire une base et sauvegarder le rapport

```bash
jslistener-db-reader \
  --db /tmp/session.sqlite3 \
  --output /tmp/session-readable.json
```

Avec `--output`, le lecteur sauvegarde le rapport et l'affiche également en JSON.

## 9. Signaux et arrêt

Trouver le processus :

```bash
pgrep -af '[J]S_listener.py'
```

| Action | Commande | Résultat |
|---|---|---|
| Basculer le mode | `kill -USR1 <PID>` | `ctv <-> ctg`, enregistré dans SQLite. |
| Arrêt propre | `kill -TERM <PID>` | Ferme Chromium et finalise la session avec `status=stopped`. |
| Arrêt d'urgence | `kill -USR2 <PID>` | Arrête avec `status=emergency`; limite les opérations de fin. |
| Arrêt terminal | `Ctrl+C` | Finalise avec `keyboard_interrupt`. |

## 10. Scanner avant publication

### Scanner le dossier courant

```bash
jslistener-secret-scan
```

### Scanner le dépôt et l'historique Git

```bash
jslistener-secret-scan \
  --root /chemin/vers/JSL \
  --history \
  --output /tmp/js_listener-secret-report.json
```

Résultat : rapport JSON contenant les findings, leur sévérité et leur emplacement. Le rapport peut lui-même contenir des chemins sensibles : le conserver hors du dépôt.

Le scanner est heuristique et ne remplace pas une revue manuelle.

## 11. Installation et test

Installation complète :

```bash
cd JSL
./setup_env.sh
```

Test depuis n'importe quel répertoire :

```bash
jslistener-test
```

Résultat attendu : démarrage du navigateur, deux transitions `ctv -> ctg -> ctv`, création SQLite, puis arrêt propre.

## 12. Matrice de choix rapide

| Besoin | Options recommandées | Résultat |
|---|---|---|
| Observation réseau minimale | `--mode ctv` + `--in-scope` | Requêtes `fetch`/`XHR`, sans cookies ni corps. |
| Cartographie JS/JSON | `--mode ctg` + `--in-scope` | Ressources et dépendances, sans corps sauvegardé. |
| Analyse de cookies non secrets | `--capture-cookies` | Métadonnées seulement. |
| Analyse d'un token précis | `--capture-cookies --capture-cookie-values --secrets ...` | Valeurs capturées ; risque élevé, usage temporaire. |
| Analyse de contenu de réponse | `--capture-response-bodies --max-response-size ...` | Corps limités ; risque de données sensibles. |
| Environnement avec certificat de test | `--ignore-https-errors` | TLS permissif ; ne pas utiliser en production. |
| Exécution isolée | `--headless` dans une machine dédiée | Pas de fenêtre ; supervision nécessaire. |

## 13. Fichiers produits

| Fichier ou table | Produit par | Contenu |
|---|---|---|
| `*.sqlite3` | Listener | Sessions, pages, réseau, ressources, cookies et événements. |
| `*.jsonl` | `--cookie-log`, `--js-log` | Journaux de cookies ou de ressources. |
| `secrets.json` | `--capture-cookie-values` | Valeurs de cookies potentiellement réutilisables. |
| `--response-dir` | `--capture-response-bodies` | Corps de réponses JS/JSON. |
| `--output *.json` | `-o`, `--output` | Rapport complet de session. |

Tous ces fichiers doivent rester hors du dépôt public et être supprimés après analyse lorsqu'ils ne sont plus nécessaires.

Voir [SECURITY.md](SECURITY.md) pour la politique complète et les responsabilités de l'utilisateur.
