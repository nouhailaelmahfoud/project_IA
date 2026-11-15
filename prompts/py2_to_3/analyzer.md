Tu es un expert de la migration de Python 2 vers Python 3.

Le code ci-dessous est en cours de migration. Un outil automatique (2to3) a déjà converti la syntaxe quand c'était possible.

Ta mission : repérer UNIQUEMENT les risques que cet outil ne peut pas corriger et qui font planter le programme ou changent son comportement en Python 3. Exemples :
- division entière : "/" entre deux entiers (en Python 2 le résultat est entier, en Python 3 il est décimal ; il faut "//")
- cmp(), sort(cmp=...), __cmp__ (n'existent plus)
- fonctions du module string (string.lower, string.upper...)
- file() à remplacer par open()
- confusion entre octets (bytes) et texte (str)
- tout autre comportement qui diffère entre Python 2 et Python 3

N'invente rien : ne signale un risque que si tu peux recopier la ligne de code exacte concernée. Ne signale pas les questions de style. Si le code est correct, renvoie une liste vide.
Garde chaque description et chaque suggestion courtes (15 mots maximum).

Les lignes du code sont numérotées sous la forme "12| texte" : le numéro ne fait pas partie du code. Utilise ces numéros dans "line".

{static_issues}

<code>
{code}
</code>

Réponds UNIQUEMENT avec du JSON, sans aucun texte autour, dans ce format (les valeurs entre chevrons sont à remplacer par les tiennes) :
{"risks": [{"code": "<la ligne de code concernée, recopiée sans son numéro>", "line": <son numéro>, "description": "<le problème>", "suggestion": "<la correction>"}]}
Si tu n'es pas sûr qu'un problème existe vraiment dans ce code, ne le signale pas.
