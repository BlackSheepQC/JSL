# Manuel utilisateur - JS Listener

## 1. Présentation

`JS_listener.py` ouvre un navigateur Playwright local et observe une navigation manuelle sur une cible autorisée.

L'outil ne lance pas de serveur réseau public. Les informations collectées sont enregistrées localement dans une base SQLite et, selon les options, dans des fichiers JSONL ou JSON.

Utiliser cet outil uniquement sur des domaines explicitement autorisés.

## 2. Prérequis

Le dossier contient un environnement Python virtuel dans `.venv/`.

Depuis le dossier `JSL` :

```bash
source .venv/bin/activate
```

Ou utiliser directement l'interpréteur de l'environnement virtuel :

```bash
.venv/bin/python JS_listener.py --help
```

Playwright et son navigateur Chromium doivent être disponibles dans cet environnement.

## 3. Fichiers principaux

- `JS_listener.py` : programme principal.
- `JSlistenerDB_reader.py` : lecture et synthèse d'une base SQLite.
- `test_js_listener.sh` : test d'intégration local.
- `.venv/` : environnement Python utilisé pour exécuter Playwright.

## 4. Modes de fonctionnement

### CTV - Capture de trafic observable

Le mode `ctv` observe les requêtes `fetch` et `XHR` dans le périmètre autorisé :

- méthode HTTP ;
- URL et domaine ;
- type de ressource ;
- statut HTTP ;
- type MIME ;
- taille de réponse ;
- redirections ;
- erreurs réseau.

### CTG - Cartographie technique

Le mode `ctg` cartographie les ressources JavaScript, MJS et JSON :

- URL de la ressource ;
- page et frame d'origine ;
- statut HTTP ;
- type MIME ;
- taille ;
- empreinte SHA-256 ;
- dépendance entre la page et la ressource.

Les corps des réponses ne sont sauvegardés que si `--capture-response-bodies` est utilisé.

## 5. Définir le périmètre

Le fichier passé à `--in-scope` contient un motif par ligne. Les lignes vides et les commentaires commençant par `#` sont ignorés.

Exemple `in-scope.txt` :

```text
example.com
*.example.com
re:.*\\.example\\.com
```

Le filtrage porte principalement sur le nom d'hôte. Sans fichier de périmètre ou sans motif correspondant, les événements ne sont pas enregistrés.

## 6. Lancer une session

### Mode CTV

```bash
.venv/bin/python JS_listener.py \
  --target https://example.com \
  --mode ctv \
  --in-scope ./in-scope.txt \
  --db /tmp/js_listener.sqlite3
```

### Mode CTG

```bash
.venv/bin/python JS_listener.py \
  --target https://example.com \
  --mode ctg \
  --in-scope ./in-scope.txt \
  --db /tmp/js_listener.sqlite3
```

Le navigateur est visible par défaut afin de permettre une navigation manuelle. Pour lancer Chromium sans interface graphique :

```bash
.venv/bin/python JS_listener.py \
  --target https://example.com \
  --mode ctv \
  --in-scope ./in-scope.txt \
  --headless
```

## 7. Options disponibles

| Option | Description |
|---|---|
| `-t`, `--target` | URL initiale, obligatoire. |
| `-u`, `--user-agent` | User-Agent personnalisé. |
| `--mode ctv\|ctg` | Mode initial, `ctv` par défaut. |
| `--in-scope` | Fichier de périmètre autorisé. |
| `--db` | Chemin de la base SQLite. |
| `--sleep` | Intervalle de surveillance en secondes. |
| `--inactivity` | Arrêt automatique après une période d'inactivité. `0` désactive cette limite. |
| `--headless` | Lance le navigateur sans interface graphique. |
| `--clear-cookies` | Supprime les cookies du contexte avant la navigation. |
| `--capture-cookies` | Enregistre les métadonnées des cookies dans SQLite et JSONL. |
| `--capture-cookie-values` | Enregistre aussi les valeurs dans le fichier de secrets. Nécessite `--capture-cookies`. |
| `--cookie-log` | Chemin du journal JSONL des cookies. |
| `--secrets` | Chemin du fichier contenant les valeurs de cookies. |
| `--capture-response-bodies` | Sauvegarde les corps JS/JSON. |
| `--response-dir` | Dossier de sauvegarde des corps de réponses. |
| `--max-response-size` | Taille maximale d'un corps sauvegardé, en octets. |
| `--js-log` | Journal JSONL des ressources CTG. |
| `-o`, `--output` | Exporte la session complète en JSON à la fin. |
| `-j`, `--json` | Affiche la session complète en JSON à la fin. |

## 8. Basculer de mode pendant la session

Le mode peut être changé à chaud avec `SIGUSR1`.

1. Trouver le PID du processus.
2. Envoyer le signal :

```bash
kill -USR1 <PID>
```

Les transitions sont enregistrées dans la table `mode_changes`.

Le changement ne capture pas rétroactivement les ressources déjà chargées. Effectuer une nouvelle navigation ou interaction après le changement de mode.

## 9. Arrêter une session

Arrêt propre :

```bash
kill -TERM <PID>
```

Arrêt d'urgence :

```bash
kill -USR2 <PID>
```

Arrêt manuel depuis le terminal : `Ctrl+C`.

La session est alors marquée comme `stopped` ou `emergency` dans SQLite.

## 10. Données produites

### Base SQLite

La base contient notamment :

- `sessions` : paramètres et état de chaque session ;
- `pages` : pages visitées ;
- `frames` : frames attachées aux pages ;
- `network_events` : événements CTV ;
- `resources` : ressources CTG ;
- `dependencies` : relations page-ressource ;
- `mode_changes` : changements de mode ;
- `cookies` : métadonnées des cookies ;
- `events` : événements internes.

Les fichiers par défaut sont créés dans `/tmp` :

- `/tmp/js_listener.sqlite3` ;
- `/tmp/js_log.jsonl` ;
- `/tmp/cookie_log.jsonl` ;
- `/tmp/secrets.json` ;
- `/tmp/js_listener_responses/`.

Les chemins peuvent être modifiés avec les options correspondantes.

### Rapport JSON

Pour produire un rapport complet :

```bash
.venv/bin/python JS_listener.py \
  --target https://example.com \
  --mode ctg \
  --in-scope ./in-scope.txt \
  --db /tmp/js_listener.sqlite3 \
  --output /tmp/js_listener_report.json
```

Le rapport est construit à partir de SQLite à la fin de la session. Il n'effectue pas de nouvelle requête réseau.

## 11. Lire une base existante

Rapport texte :

```bash
.venv/bin/python JSlistenerDB_reader.py \
  --db /tmp/js_listener.sqlite3
```

Rapport JSON dans le terminal :

```bash
.venv/bin/python JSlistenerDB_reader.py \
  --db /tmp/js_listener.sqlite3 \
  --json
```

Sauvegarder le rapport dans un fichier :

```bash
.venv/bin/python JSlistenerDB_reader.py \
  --db /tmp/js_listener.sqlite3 \
  --output /tmp/rapport.json
```

## 12. Cookies et secrets

Les cookies ne sont pas collectés par défaut.

Pour collecter uniquement leurs métadonnées :

```bash
--capture-cookies
```

Pour collecter aussi leurs valeurs :

```bash
--capture-cookies --capture-cookie-values --secrets /chemin/protege/secrets.json
```

Les valeurs de cookies peuvent donner accès à une session. Protéger le fichier de secrets, ne pas le partager et le supprimer dès qu'il n'est plus nécessaire.

## 13. Sauvegarder les corps JS/JSON

```bash
.venv/bin/python JS_listener.py \
  --target https://example.com \
  --mode ctg \
  --in-scope ./in-scope.txt \
  --capture-response-bodies \
  --response-dir /tmp/js_listener_responses \
  --max-response-size 2097152
```

Les fichiers sont nommés à partir de leur empreinte SHA-256. Les réponses dépassant la taille maximale ne sont pas sauvegardées.

## 14. Test d'intégration

Le test vérifie le démarrage du navigateur, les signaux `SIGUSR1`, la création SQLite et l'arrêt propre :

```bash
PYTHON="$PWD/.venv/bin/python" ./test_js_listener.sh
```

Le test utilise `https://example.com`. Il peut donc produire zéro ressource et zéro événement réseau, ce qui reste valide pour vérifier le cycle de vie et les changements de mode.

## 15. Dépannage

### Le programme s'arrête immédiatement

Consulter le journal :

```bash
cat /tmp/js_listener_test.log
```

Vérifier que Playwright et Chromium sont installés dans `.venv`.

### Aucun événement n'est enregistré

Vérifier :

- que le fichier `--in-scope` existe ;
- que le domaine visité correspond à un motif ;
- que la session utilise le mode approprié ;
- qu'une nouvelle navigation a été effectuée après un changement de mode.

### Le rapport est vide

Vérifier que la base utilisée par `JSlistenerDB_reader.py` correspond à celle fournie par `--db` au listener.

### Le navigateur ne s'arrête pas

Envoyer d'abord un arrêt propre :

```bash
kill -TERM <PID>
```

Utiliser `SIGUSR2` uniquement pour un arrêt d'urgence.
