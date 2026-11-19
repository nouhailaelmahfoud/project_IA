Tu es un ingénieur QA. Écris des tests de CARACTÉRISATION pour le code Python 2 ci-dessous : ils doivent décrire ce que le code FAIT aujourd'hui en Python 2.7, pas ce qu'il devrait faire.

Contraintes :
- Utilise pytest. Le module à tester s'appelle `{module}` : commence par `import {module}`.
- Les tests doivent donner le même résultat en Python 2.7 ET en Python 3 : écris `from __future__ import print_function`, n'utilise ni f-string ni instruction print sans parenthèses.
- Écris les valeurs attendues en littéraux (nombres, chaînes), calculées en lisant le code avec la sémantique de Python 2 (par exemple la division `/` entre deux entiers est entière).
- Pas de réseau, pas d'aléatoire, pas de date ou d'heure, pas de fichier en dehors du dossier courant.
- De 5 à 12 tests courts, qui couvrent les fonctions et méthodes principales.
- Ne teste pas les erreurs qui n'existent qu'en Python 2.

Réponds UNIQUEMENT avec le fichier de test, dans un seul bloc de code Python.

{feedback}

Fichier `{filename}` :
<code>
{code}
</code>