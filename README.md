# Manuel utilisateur - JS Listener

## 1. Présentation

`JS_listener.py` ouvre un navigateur Playwright local et observe une navigation manuelle sur une cible autorisée.

L'outil ne lance pas de serveur réseau public. Les informations collectées sont enregistrées localement dans une base SQLite et, selon les options, dans des fichiers JSONL ou JSON.

Utiliser cet outil uniquement sur des domaines explicitement autorisés.

## 2. Prérequis

Prévoir :

- Python 3.9 ou plus récent ;
- `venv` disponible dans l'installation Python ;
- une connexion Internet pendant l'installation de Playwright et Chromium ;
- un environnement graphique si le navigateur n'est pas lancé avec `--headless`.

Les dépendances Python sont listées dans [requirements.txt](requirements.txt). Le dossier `.venv/` est local et n'est pas versionné.

### Installation automatique

Après avoir cloné le dépôt :

```bash
cd JSL
chmod +x setup_env.sh
./setup_env.sh
```

Le script :

1. crée `.venv/` s'il n'existe pas ;
2. installe les dépendances de `requirements.txt` ;
3. installe le navigateur Chromium utilisé par Playwright ;
4. installe les commandes globales dans `~/.local/bin` ;
5. vérifie que les commandes principales répondent.

Si Python n'est pas nommé `python3`, préciser son chemin :

```bash
PYTHON_BIN=/usr/bin/python3 ./setup_env.sh
```

Si `~/.local/bin` n'est pas dans le `PATH` :

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Installation manuelle

La même installation peut être effectuée ainsi :

Depuis le dossier `JSL` :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
./install_cli.sh
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
- `secret_scan.py` : recherche heuristique de secrets et d'artefacts sensibles.
- `SECURITY.md` : politique de sécurité, risques et protections.
- `CHEAT_SHEET.md` : options, combinaisons et résultats attendus.
- `install_cli.sh` : installe les commandes globales dans `~/.local/bin`.
- `setup_env.sh` : construit l'environnement `.venv` et installe Chromium.
- `test_js_listener.sh` : test d'intégration local.
- `.venv/` : environnement Python utilisé pour exécuter Playwright.

## 3.1 Commandes globales

Les commandes suivantes peuvent être installées dans `~/.local/bin`, qui doit être présent dans le `PATH` :

| Commande | Fonction |
|---|---|
| `js-listener` | Lance `JS_listener.py`. |
| `jslistener-db-reader` | Lance `JSlistenerDB_reader.py`. |
| `jslistener-secret-scan` | Lance `secret_scan.py`. |
| `jslistener-test` | Lance le test d'intégration avec le `.venv`. |

Après avoir créé l'environnement `.venv` et installé Playwright :

```bash
./install_cli.sh
```

Elles peuvent être utilisées depuis n'importe quel répertoire :

```bash
js-listener --help
jslistener-db-reader --db /tmp/js_listener.sqlite3
jslistener-secret-scan --history --output /tmp/js_listener_secret_scan.json
jslistener-test
```

Pour une nouvelle machine, créer des lanceurs dans `~/.local/bin` qui pointent vers l'interpréteur `.venv/bin/python` et les fichiers du dépôt. Vérifier ensuite :

```bash
command -v js-listener jslistener-db-reader jslistener-secret-scan jslistener-test
```

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
| `--ignore-https-errors` | Désactive explicitement la vérification TLS. Déconseillé ; désactivé par défaut. |
| `--no-ignore-https-errors` | Force la vérification TLS. C'est le comportement par défaut. |
| `--no-sandbox` | Désactive le sandbox Chromium. Déconseillé ; le sandbox reste actif par défaut. |
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

La base SQLite et ses fichiers auxiliaires sont forcés en permissions `600`. Les journaux et fichiers de secrets produits par le listener utilisent également des permissions restrictives. Ces protections ne chiffrent pas les données : l'accès au compte système ou aux sauvegardes peut toujours exposer leur contenu.

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

`--capture-cookie-values` est désactivé par défaut et doit rester désactivé sauf nécessité absolue. Préférer `--capture-cookies` si seules les métadonnées sont nécessaires.

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

Les corps de réponses peuvent contenir des données personnelles, des tokens ou des informations métier. Cette option doit rester désactivée sauf besoin documenté, avec une taille maximale limitée et un dossier de sortie privé.

## 14. Risques d'exécution et options sûres

JSL est un outil d'observation : même sans modification volontaire de la cible, les URLs, requêtes, ressources, cookies et réponses observées peuvent contenir des informations confidentielles.

- Utiliser uniquement une cible et un fichier `--in-scope` explicitement autorisés.
- Garder `--capture-cookie-values` désactivé par défaut.
- Garder `--capture-response-bodies` désactivé par défaut.
- Garder `--ignore-https-errors` désactivé. Le comportement normal vérifie les certificats TLS.
- Utiliser `--headless` et `--no-sandbox` uniquement dans un environnement dédié et sans privilèges.
- Stocker la base, les logs et les rapports dans un dossier privé, puis les supprimer après analyse.
- Ne jamais déposer une base, un secret, un rapport client ou un fichier de périmètre dans Git.

Les protections détaillées, les options à risque et la clause de non-responsabilité sont dans [SECURITY.md](SECURITY.md).

## 15. Scanner avant publication

Avant chaque commit ou publication, lancer le scanner sans publier son rapport :

```bash
.venv/bin/python secret_scan.py \
  --history \
  --output /tmp/js_listener_secret_scan.json
```

Le scanner examine l'arbre local, les artefacts sensibles connus et, avec `--history`, les commits Git accessibles. Il masque les valeurs et produit un rapport d'exposition JSON. Un rapport sans finding ne prouve pas l'absence de données sensibles : une revue manuelle reste obligatoire.

## 16. Test d'intégration

Le test vérifie le démarrage du navigateur, les signaux `SIGUSR1`, la création SQLite et l'arrêt propre :

```bash
PYTHON="$PWD/.venv/bin/python" ./test_js_listener.sh
```

Le test utilise `https://example.com`. Il peut donc produire zéro ressource et zéro événement réseau, ce qui reste valide pour vérifier le cycle de vie et les changements de mode.

## 17. Dépannage

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
