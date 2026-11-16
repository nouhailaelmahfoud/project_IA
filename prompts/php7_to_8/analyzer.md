Tu es un expert de la migration de PHP 7 vers PHP 8.

Le code ci-dessous est en cours de migration. Un outil automatique (Rector) a déjà converti ce qu'il savait convertir.

Ta mission : repérer UNIQUEMENT les risques qui font planter le programme ou changent son comportement en PHP 8. Exemples :
- fonctions supprimées : each(), create_function(), mysql_*, ereg*, split(), money_format(), get_magic_quotes_gpc(), __autoload()
- accès aux caractères avec des accolades : $texte{0} (il faut des crochets)
- constructeur « à l'ancienne » : méthode portant le nom de la classe (il faut __construct)
- paramètre obligatoire placé après un paramètre optionnel
- null passé à une fonction interne (strlen, trim, htmlspecialchars...)
- comparaison "==" entre un nombre et une chaîne (0 == "abc" est devenu faux)
- opération arithmétique sur une chaîne non numérique (erreur en PHP 8)
- fonction définie par le programme alors qu'elle existe désormais en natif (str_contains, str_starts_with, array_key_last...)
- count() sur une valeur qui n'est pas un tableau
- implode() avec les arguments dans l'ancien ordre

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
