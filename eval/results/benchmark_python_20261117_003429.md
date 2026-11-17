# Comparatif python (ollama, modèle par défaut)

| Fichier | Mode | Syntaxe | S'exécute | = attendu | Pièges bloquants | Retour arrière | Appels | Tokens (e/s) | Durée |
|---|---|---|---|---|---|---|---|---|---|
| inventory | rules_only | oui | oui | non | 0 | non | 0 | 0/0 | 0.3 s |
| inventory | llm_only | non | non | non | 0 | oui | 3 | 2311/684 | 241.5 s |
| inventory | hybrid-sans-detecteurs | oui | oui | non | 0 | non | 1 | 921/7 | 34.3 s |
| inventory | hybrid | oui | oui | oui | 0 | non | 2 | 1450/52 | 74.0 s |
| textstats | rules_only | oui | non | non | 4 | non | 0 | 0/0 | 0.2 s |
| textstats | llm_only | oui | non | non | 1 | non | 3 | 2730/1758 | 403.4 s |
| textstats | hybrid-sans-detecteurs | oui | non | non | 4 | non | 1 | 938/55 | 52.9 s |
| textstats | hybrid | oui | non | non | 4 | oui | 2 | 1598/324 | 101.2 s |
| bank | rules_only | oui | non | non | 3 | non | 0 | 0/0 | 0.1 s |
| bank | llm_only | non | non | non | 0 | oui | 3 | 2446/109 | 99.1 s |
| bank | hybrid-sans-detecteurs | oui | non | non | 3 | oui | 5 | 3841/214 | 141.8 s |
| bank | hybrid | oui | non | non | 3 | oui | 4 | 3735/455 | 183.1 s |
