# Politique de securite - JSL

## Usage autorise uniquement

JSL doit etre utilise uniquement sur des systemes et des domaines explicitement autorises par leur proprietaire, par exemple dans le cadre d'un contrat, d'un test interne ou d'un programme Bug Bounty dont le perimetre est clair.

L'utilisateur est responsable de verifier le perimetre avant chaque session. Un fichier `--in-scope` ne remplace pas cette autorisation juridique et operationnelle.

## Donnees potentiellement exposees

JSL observe une navigation reelle et peut enregistrer localement :

- URLs, domaines, chemins, methodes et statuts HTTP ;
- noms de pages, frames, ressources et dependances ;
- requetes `fetch` et `XHR` en mode `ctv` ;
- ressources JavaScript, MJS et JSON en mode `ctg` ;
- metadonnees de cookies si `--capture-cookies` est active ;
- valeurs de cookies, donc potentiellement des jetons de session, si `--capture-cookie-values` est active ;
- corps de reponses JS/JSON si `--capture-response-bodies` est active ;
- rapports JSON et journaux JSONL selon les options utilisees.

La base SQLite n'est pas chiffree. Toute personne pouvant lire les fichiers de sortie peut potentiellement lire les donnees collectees.

## Options a risque et protections

| Option ou comportement | Risque | Protection recommandee |
|---|---|---|
| `--capture-cookie-values` | Expose des cookies de session et des jetons reutilisables. | Ne pas l'utiliser par defaut. L'activer uniquement pour un besoin documente, avec `--secrets` dans un dossier prive, permissions `600`, acces limite et suppression immediate apres analyse. |
| `--capture-cookies` | Expose les domaines, noms et attributs de cookies. | Laisser desactive si les cookies ne sont pas necessaires. Utiliser un fichier de sortie prive et supprimer le journal apres usage. |
| `--capture-response-bodies` | Peut enregistrer des donnees personnelles, tokens, reponses metier ou contenu confidentiel. | Laisser desactive par defaut, limiter `--max-response-size`, utiliser un `--response-dir` prive et supprimer les corps apres analyse. |
| `-o`, `--output` ou `-j`, `--json` | Peut exporter une synthese contenant des URLs, erreurs, domaines et ressources. | Ecrire dans un dossier prive, ne pas partager le rapport sans revue et supprimer les exports inutiles. |
| `--ignore-https-errors` | Desactive la validation des certificats TLS et facilite une interception ou une mauvaise configuration non detectee. | Ne jamais l'utiliser en production. Le comportement par defaut verifie TLS ; reserver cette option a un environnement de test explicitement controle. |
| `--headless` | Peut rendre moins visible la navigation et les donnees collectees. | Utiliser seulement avec une supervision claire et conserver les journaux d'execution hors des dossiers partages. |
| `--user-agent` | Peut modifier le comportement de la cible et produire une identification trompeuse. | Utiliser une valeur approuvee par le proprietaire de la cible et la documenter. |
| `--in-scope` absent ou incorrect | Peut faire manquer des donnees autorisees ou, selon l'autorisation et la configuration, provoquer une collecte inattendue. | Fournir un fichier de perimetre relu et tester les motifs avant la session. |
| `--no-sandbox` | Reduit l'isolation du navigateur. | Ne pas l'utiliser par defaut. Le sandbox Chromium reste actif ; si l'option est necessaire, executer dans une machine ou un conteneur dedie, avec un compte sans privileges et sans autres donnees sensibles. |

## Mesures de protection appliquees

- La verification TLS est active par defaut.
- `--ignore-https-errors` est une option explicite d'exception.
- Le sandbox Chromium est actif par defaut ; `--no-sandbox` est une exception explicite.
- Le processus utilise un umask restrictif `077`.
- La base SQLite et ses fichiers `-wal` et `-shm` sont forces en permissions `600`.
- Les journaux et fichiers de secrets produits par JSL sont forces en permissions `600`.
- `.gitignore` exclut les bases, secrets, rapports, journaux, fichiers de perimetre, reponses capturees et environnements locaux.
- `secret_scan.py` permet de rechercher les motifs de secrets et les artefacts sensibles dans l'arbre local et dans l'historique Git.

Ces protections ne chiffrent pas les donnees et ne remplacent pas les controles du systeme d'exploitation, du stockage, des sauvegardes et des comptes utilisateurs.

## Procedure avant publication

Depuis le dossier JSL :

```bash
.venv/bin/python secret_scan.py --history --output /tmp/js_listener_secret_scan.json
```

Puis :

1. Examiner le rapport sans le publier.
2. Verifier manuellement les fichiers de perimetre, bases SQLite, logs, rapports JSON et corps de reponses.
3. Verifier l'historique Git, car supprimer un secret d'un fichier ne le retire pas automatiquement des anciens commits.
4. Ne publier que les fichiers necessaires.
5. Revoquer tout secret detecte et republier l'historique seulement avec un outil de nettoyage adapte.

Le scanner est heuristique. Un rapport sans finding ne prouve pas l'absence de donnees client ou de secrets encodes autrement.

## Signaler une vulnerabilite

Ne publiez pas de credential, token, cookie, base ou preuve sensible dans une issue publique. Pour un depot prive, transmettez les details par un canal prive au proprietaire du depot et revoquez immediatement tout secret expose.

## Clause de non-responsabilite

JSL est fourni a titre d'outil technique et educatif, sans garantie d'adequation, d'exhaustivite ou de securite absolue. L'utilisateur assume seul la verification des autorisations, du perimetre, de la conformite legale, de la protection des donnees et de la securite de son environnement. Les auteurs ne sont pas responsables des dommages, collectes non autorisees, pertes de donnees, interruptions, divulgations ou consequences juridiques resultant de l'utilisation ou d'une mauvaise configuration de JSL.
