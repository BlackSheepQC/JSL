# Rapport d’audit — Projet JSL

Date : 2026-09-21
Projet : JSL (JS Listener)
Chemin du dépôt : /home/riftx56/Documents/Scripts/Upload/JSL

---

## 1. Résumé exécutif

Cet audit évalue la posture de sécurité, le périmètre d’usage, la qualité de la documentation et le niveau de préparation à une publication publique du projet JSL. Le projet est un outil Python reposant sur Playwright et SQLite, destiné à l’observation d’une navigation web autorisée et à la cartographie technique dans un périmètre contrôlé.

Le projet présente une base de code bien structurée, une documentation cohérente, des consignes de sécurité explicites et un processus de détection des secrets réaliste. Le dépôt peut être publié en tant que code source, à condition que les artefacts d’exécution et toute donnée collectée restent privés et ne soient jamais ajoutés au dépôt ni partagés publiquement.

Le principal risque n’est pas l’exposition du code lui-même, mais une mauvaise utilisation opérationnelle : si l’outil est exécuté sur des domaines non autorisés, ou avec des options de collecte étendue telles que `--capture-cookie-values` ou `--capture-response-bodies`, il peut capturer des données sensibles en temps réel. Ces risques sont clairement décrits dans la documentation du projet et ne sont pas activés par défaut.

Le constat global est le suivant :

- posture de sécurité : acceptable pour une publication publique contrôlée ;
- qualité du code : bonne ;
- qualité de la documentation : bonne ;
- risque de fuite de secrets dans le dépôt : faible ;
- risque de mauvaise utilisation opérationnelle : moyen, selon le contexte d’usage.

---

## 2. Périmètre de l’audit

Les domaines suivants ont été évalués :

- structure du dépôt et pertinence des fichiers ;
- objectif du projet et limites opérationnelles ;
- valeurs par défaut de sécurité et exceptions explicites ;
- gestion des données sensibles et protection de la vie privée ;
- exhaustivité de la documentation et qualité du support utilisateur ;
- couverture de la détection des secrets et des artefacts sensibles ;
- état du dépôt Git et éléments de validation technique.

---

## 3. Description du projet

JSL est conçu pour :

- ouvrir une session de navigateur locale avec Playwright ;
- observer une navigation manuelle dans un périmètre de cibles autorisé ;
- détecter les activités réseau, les dépendances entre ressources et les schémas de trafic ;
- enregistrer les résultats dans une base SQLite locale et dans des sorties JSON ou JSONL optionnelles ;
- produire une cartographie technique des fichiers JavaScript et des ressources associées.

Le projet cible explicitement des domaines web autorisés et encourage l’usage d’un fichier de périmètre afin de limiter la collecte aux hôtes ou aux motifs d’URL autorisés.

---

## 4. Méthodologie

L’audit a été mené à partir d’une revue des fichiers du projet et d’une validation directe de l’état du dépôt.

Validations réalisées :

1. vérification de la propreté du dépôt Git ;
2. validation syntaxique du code Python au moyen de `py_compile` ;
3. analyse des secrets et des artefacts sensibles au moyen du scanner du projet ;
4. analyse de l’historique Git afin de détecter des motifs sensibles.

Éléments de preuve recueillis :

- `git status --short --branch` a renvoyé un dépôt propre sur la branche courante ;
- la compilation des scripts Python principaux s’est déroulée sans erreur ;
- `secret_scan.py --history` n’a produit aucun résultat.

Résumé de la vérification :

- détections critiques : 0 ;
- détections élevées : 0 ;
- détections moyennes : 0 ;
- total : 0.

Cela confirme qu’aucun secret ni aucun artefact sensible évident n’a été détecté dans le dépôt ni dans l’historique Git accessible au moment de l’audit.

---

## 5. Éléments détaillés de l’analyse

### 5.1. Structure du dépôt et clarté du code

Le dépôt présente une séparation cohérente des responsabilités :

- `JS_listener.py` : moteur principal d’exécution et d’observation du navigateur ;
- `JSlistenerDB_reader.py` : lecture de la base SQLite et synthèse hors ligne ;
- `secret_scan.py` : utilitaire de détection des secrets et des artefacts sensibles ;
- `setup_env.sh` et `install_cli.sh` : installation et préparation de l’environnement ;
- `test_js_listener.sh` : validation fonctionnelle locale ;
- `README.md`, `SECURITY.md` et `CHEAT_SHEET.md` : documentation utilisateur et documentation de sécurité.

Évaluation : structure solide et maintenable pour un projet ciblé.

### 5.2. Qualité de la documentation

Le dépôt comprend un manuel d’utilisation pratique, une politique de sécurité et un aide-mémoire, qui fournissent ensemble :

- les informations d’installation ;
- les usages en ligne de commande et des exemples ;
- la gestion du périmètre de collecte ;
- la définition des modes (`ctv` et `ctg`) ;
- des avertissements sur le traitement des données ;
- des recommandations pour un usage sûr.

Évaluation : la documentation se situe au-dessus de la moyenne pour un outil sensible sur le plan de la sécurité et convient à une lecture publique.

### 5.3. Valeurs par défaut de sécurité

Le projet applique des valeurs par défaut prudentes, notamment :

- vérification des certificats TLS activée par défaut ;
- sandbox Chromium activé par défaut ;
- activation explicite exigée pour les exceptions moins sûres telles que `--ignore-https-errors` et `--no-sandbox` ;
- permissions restrictives sur les fichiers générés et sur les artefacts SQLite ;
- `.gitignore` excluant les fichiers de sortie sensibles et les fichiers d’environnement local.

Évaluation : posture par défaut saine et responsable pour un outil capable de capturer des données réseau réelles.

### 5.4. Gestion des données sensibles

Le projet reconnaît et documente explicitement plusieurs catégories de risque :

- capture des métadonnées de cookies ;
- capture des valeurs de cookies ;
- capture des corps de réponse ;
- exports JSON et JSONL ;
- exports de la base de données et rapports.

Ces fonctionnalités ne sont pas dangereuses en soi lorsqu’elles sont utilisées correctement, mais elles imposent une discipline opérationnelle stricte. La documentation met clairement en garde contre le fait qu’elles peuvent exposer des jetons de session, des données métier ou du contenu propre au client.

Évaluation : le modèle de sécurité est réaliste et transparent. Le projet ne masque pas la sensibilité de ces sorties.

### 5.5. Analyse des secrets et hygiène du dépôt

Le dépôt contient un scanner dédié aux secrets probables et aux artefacts d’exécution. Il vérifie à la fois les fichiers locaux et l’historique Git. L’audit a confirmé qu’aucune détection critique ou à forte confiance n’avait été remontée au moment de l’évaluation.

Le fichier `.gitignore` exclut également les bases de données, les journaux, les fichiers de périmètre local, les corps JSON, les dossiers de sortie et les environnements virtuels locaux.

Évaluation : l’hygiène du dépôt est bonne, ce qui est important en vue d’une publication publique.

---

## 6. Évaluation des risques

### 6.1. Risques intrinsèques

Les principaux risques sont opérationnels et non techniques :

- usage sur des cibles non autorisées ;
- collecte des valeurs de cookies sans autorisation explicite ni besoin clairement établi ;
- activation de la capture des corps de réponse sur du contenu métier sensible ;
- publication d’artefacts d’exécution ou de rapports avec le code source.

### 6.2. Évaluation du risque résiduel

| Zone de risque | Évaluation | Remarques |
|---|---|---|
| Fuite de secrets dans le dépôt | Faible | Le scanner n’a remonté aucune détection. |
| Comportement risqué par défaut | Faible | Des valeurs par défaut prudentes sont appliquées. |
| Mauvaise utilisation opérationnelle | Moyenne | Dépend de l’autorisation et de la politique de la cible. |
| Exposition par les journaux d’exécution | Moyenne | Nécessite une gestion stricte des sorties. |
| Publication publique du code | Acceptable | Le code peut être public ; les données d’exécution restent privées. |

---

## 7. Préparation à la publication publique

### Recommandation

Le projet peut être publié sous la forme d’un dépôt de code, sous réserve des conditions suivantes :

1. ne pas publier de données générées à l’exécution ;
2. conserver privés toutes les bases SQLite, tous les journaux, tous les corps de réponse et tous les exports de session ;
3. continuer à utiliser un fichier `--in-scope` explicite afin de limiter l’observation aux hôtes autorisés ;
4. éviter d’activer la capture des valeurs de cookies, sauf si elle est strictement nécessaire et correctement maîtrisée ;
5. maintenir les avertissements de sécurité visibles dans la documentation publique.

### Conclusion

Le projet n’est pas un « outil prêt à l’emploi pour une collecte illimitée ». C’est un outil contrôlé, soumis à autorisation et orienté vers la cartographie et l’observation technique. Il s’agit d’une posture légitime pour du code public, à condition que le projet soit clairement présenté comme un outil défensif ou de recherche autorisée, exigeant un périmètre défini et une autorisation explicite.

---

## 8. Évaluation formelle

### Classification de sécurité

Code source publiable : oui
Données d’exécution publiables : non
Sécurisé par défaut : oui pour le dépôt source, non pour les sorties générées lors de l’exécution
Exigence opérationnelle : l’usage doit rester limité à des cibles explicitement autorisées

### Statut global

Statut : validé pour la publication du code source
Condition : les artefacts d’exécution restent privés et hors de la diffusion publique

---

## 9. Validation

Préparé par : audit assisté par IA
Date : 2026-09-21

Résumé de l’évaluation :

- structure du projet : satisfaisante ;
- documentation : satisfaisante ;
- posture de sécurité : satisfaisante pour une publication publique contrôlée ;
- contrôles de gestion des données : satisfaisants lorsqu’ils sont utilisés comme prévu ;
- recommandation finale : la publication du code source est acceptable, avec une séparation stricte des artefacts issus de la collecte en session.

Signature :

[Préparé et vérifié en vue d’une décision de publication par l’assistant d’audit]

---

## 10. Déclaration finale

Le projet JSL peut être publié publiquement de manière responsable. La base de code témoigne d’une bonne prise en compte de la sécurité, d’une documentation soignée et de garde-fous opérationnels. Le dépôt principal peut être publié tel quel, tandis que toute donnée collectée lors de l’exécution, y compris les bases SQLite, les journaux, les corps de réponse, les cookies et les rapports de session, doit rester privée et hors du périmètre public.