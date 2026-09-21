# Politique de sécurité — JSL

## Usage autorisé uniquement

JSL doit être utilisé uniquement sur des systèmes et des domaines explicitement autorisés par leur propriétaire, par exemple dans le cadre d'un contrat, d'un test interne ou d'un programme Bug Bounty dont le périmètre est clair.

L'utilisateur est responsable de vérifier le périmètre avant chaque session. Un fichier `--in-scope` ne remplace pas cette autorisation juridique et opérationnelle.

## Données potentiellement exposées

JSL observe une navigation réelle et peut enregistrer localement :

- URL, domaines, chemins, méthodes et statuts HTTP ;
- noms de pages, frames, ressources et dépendances ;
- requêtes `fetch` et `XHR` en mode `ctv` ;
- ressources JavaScript, MJS et JSON en mode `ctg` ;
- métadonnées de cookies si `--capture-cookies` est activé ;
- valeurs de cookies, donc potentiellement des jetons de session, si `--capture-cookie-values` est activé ;
- corps de réponses JS/JSON si `--capture-response-bodies` est activé ;
- rapports JSON et journaux JSONL selon les options utilisées.

La base SQLite n'est pas chiffrée. Toute personne pouvant lire les fichiers de sortie peut potentiellement lire les données collectées.

## Options à risque et protections

| Option ou comportement | Risque | Protection recommandée |
|---|---|---|
| `--capture-cookie-values` | Expose des cookies de session et des jetons réutilisables. | Ne pas l'utiliser par défaut. L'activer uniquement pour un besoin documenté, avec `--secrets` dans un dossier privé, permissions `600`, accès limité et suppression immédiate après analyse. |
| `--capture-cookies` | Expose les domaines, les noms et les attributs de cookies. | Laisser désactivé si les cookies ne sont pas nécessaires. Utiliser un fichier de sortie privé et supprimer le journal après usage. |
| `--capture-response-bodies` | Peut enregistrer des données personnelles, des jetons, des réponses métier ou du contenu confidentiel. | Laisser désactivé par défaut, limiter `--max-response-size`, utiliser un `--response-dir` privé et supprimer les corps après analyse. |
| `-o`, `--output` ou `-j`, `--json` | Peut exporter une synthèse contenant des URL, des erreurs, des domaines et des ressources. | Écrire dans un dossier privé, ne pas partager le rapport sans revue et supprimer les exports inutiles. |
| `--ignore-https-errors` | Désactive la validation des certificats TLS et facilite une interception ou une mauvaise configuration non détectée. | Ne jamais l'utiliser en production. Le comportement par défaut vérifie TLS ; réserver cette option à un environnement de test explicitement contrôlé. |
| `--headless` | Peut rendre moins visibles la navigation et les données collectées. | Utiliser seulement avec une supervision claire et conserver les journaux d'exécution hors des dossiers partagés. |
| `--user-agent` | Peut modifier le comportement de la cible et produire une identification trompeuse. | Utiliser une valeur approuvée par le propriétaire de la cible et la documenter. |
| `--in-scope` absent ou incorrect | Peut faire manquer des données autorisées ou, selon l'autorisation et la configuration, provoquer une collecte inattendue. | Fournir un fichier de périmètre relu et tester les motifs avant la session. |
| `--no-sandbox` | Réduit l'isolation du navigateur. | Ne pas l'utiliser par défaut. Le sandbox Chromium reste actif ; si l'option est nécessaire, exécuter dans une machine ou un conteneur dédié, avec un compte sans privilèges et sans autres données sensibles. |

## Mesures de protection appliquées

- La vérification TLS est active par défaut.
- `--ignore-https-errors` est une option d'exception explicite.
- Le sandbox Chromium est actif par défaut ; `--no-sandbox` est une exception explicite.
- Le processus utilise un umask restrictif `077`.
- La base SQLite et ses fichiers `-wal` et `-shm` sont forcés en permissions `600`.
- Les journaux et les fichiers de secrets produits par JSL sont forcés en permissions `600`.
- `.gitignore` exclut les bases, les secrets, les rapports, les journaux, les fichiers de périmètre, les réponses capturées et les environnements locaux.
- `secret_scan.py` permet de rechercher les motifs de secrets et les artefacts sensibles dans l'arborescence locale et dans l'historique Git.

Ces protections ne chiffrent pas les données et ne remplacent pas les contrôles du système d'exploitation, du stockage, des sauvegardes et des comptes utilisateurs.

## Procédure avant publication

Depuis le dossier JSL :

```bash
.venv/bin/python secret_scan.py --history --output /tmp/js_listener_secret_scan.json
```

Puis :

1. Examiner le rapport sans le publier.
2. Vérifier manuellement les fichiers de périmètre, les bases SQLite, les journaux, les rapports JSON et les corps de réponses.
3. Vérifier l'historique Git, car supprimer un secret d'un fichier ne le retire pas automatiquement des anciens commits.
4. Ne publier que les fichiers nécessaires.
5. Révoquer tout secret détecté et ne republier l'historique qu'avec un outil de nettoyage adapté.

Le scanner est heuristique. Un rapport sans résultat ne prouve pas l'absence de données client ou de secrets encodés autrement.

## Signaler une vulnérabilité

Ne publiez pas d'identifiant, de jeton, de cookie, de base de données ou de preuve sensible dans une issue publique. Pour un dépôt privé, transmettez les détails par un canal privé au propriétaire du dépôt et révoquez immédiatement tout secret exposé.

## Clause de non-responsabilité

JSL est fourni à titre d'outil technique et éducatif, sans garantie d'adéquation, d'exhaustivité ou de sécurité absolue. L'utilisateur assume seul la vérification des autorisations, du périmètre, de la conformité légale, de la protection des données et de la sécurité de son environnement. Les auteurs ne sont pas responsables des dommages, des collectes non autorisées, des pertes de données, des interruptions, des divulgations ou des conséquences juridiques résultant de l'utilisation ou d'une mauvaise configuration de JSL.
