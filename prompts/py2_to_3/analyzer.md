Tu es un expert de la migration de Python 2 vers Python 3.

Le code ci-dessous est en cours de migration. Un outil automatique (2to3) a déjà converti la syntaxe quand c'était possible.

Ta mission : repérer UNIQUEMENT les risques que cet outil ne peut pas corriger et qui font planter le programme ou changent son comportement en Python 3. Exemples :
- division entière : "/" entre deux entiers (en Python 2 le résultat est entier, en Python 3 il est décimal ; il faut "//")
- cmp(), sort(cmp=...), __cmp__ (n'existent plus)
- fonctions du module string (string.lower, string.upper...)
- file() à remplacer par open()
- confusion entre octets (bytes) et texte (str)
- tout autre comportement qui diffère entre Python 2 et Python 3

N'invente rien et ne signale pas les questions de style. Si le code est correct, renvoie une liste vide.

{static_issues}

<code>
{code}
</code>

Réponds UNIQUEMENT avec du JSON, sans aucun texte autour, dans ce format :
{"risks": [{"line": 12, "description": "ce qui pose problème", "suggestion": "comment le corriger"}]}
