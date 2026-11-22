# Étude Problème / Solution / ROI

## Problème

Beaucoup d'entreprises ont du code PHP 7 ou Python 2, qui n'est plus maintenu (plus de correctifs
de sécurité). Le migrer à la main est long, répétitif et risqué : on oublie des cas, on casse
le comportement sans s'en rendre compte. Le travail est souvent repoussé.

## Solution

Un agent qui enchaîne : détection des problèmes → règles automatiques → IA pour les cas
difficiles → vérification (syntaxe, analyse statique, comparaison des sorties ancien/nouveau
code) → rapport. Le développeur ne fait plus que **relire** le résultat.

## Résultats mesurés (benchmark du dépôt, `eval/results/`)

Corpus de 3 fichiers Python 2, modèle local (Ollama) :

| Mode | Durée par fichier | Remarque |
|---|---|---|
| `rules_only` | 0,1 à 0,3 s | sans IA, gratuit |
| `hybrid` | 74 à 183 s | IA + détecteurs, plus de cas résolus |
| `llm_only` | 99 à 403 s | retour arrière fréquent (code invalide) |

Dans ce benchmark, `hybrid` est le seul mode à reproduire le résultat attendu sur `inventory`.
Sur `textstats` et `bank`, des pièges bloquants restent : **l'outil ne migre pas tout**, il
signale ce qui reste. C'est important pour l'honnêteté de l'étude.

## ROI : coût manuel vs automatisé

Le calcul est volontairement simple. **Les hypothèses sont à ajuster** (barre latérale de
l'interface) ; ce sont des estimations, pas des mesures.

Hypothèses d'exemple :

- Salaire chargé d'un développeur : 400 € / jour, soit environ 50 € / heure.
- Correction manuelle d'un problème : 10 min. Relecture d'un fichier migré : 3 min.
- Projet : 200 fichiers, 1 500 problèmes détectés, 70 % corrigés automatiquement.

| | Manuel | Avec l'outil |
|---|---|---|
| Problèmes à traiter par un humain | 1 500 | 450 (les 30 % restants) |
| Temps de correction | 1 500 × 10 min = 250 h | 450 × 10 min = 75 h |
| Temps de relecture | — | 200 × 3 min = 10 h |
| **Total** | **250 h** | **85 h** |
| **Coût** (50 €/h) | **12 500 €** | **4 250 €** |
| Coût IA (API) | — | à ajouter (quelques euros avec un petit modèle) |

**Gain : environ 165 h, soit 8 250 €**, et surtout moins de risque de régression.

Formule : `gain = problèmes_corrigés_auto × minutes_manuelles − fichiers × minutes_relecture`.
C'est exactement celle du tableau de bord de l'interface.

## Limites

- Le taux de 70 % est une hypothèse : le benchmark réel est plus mitigé sur les petits modèles.
- Un humain doit toujours relire et lancer ses propres tests avant de mettre en production.
- Pas de mesure de maintenance future ni de coût d'infrastructure.
