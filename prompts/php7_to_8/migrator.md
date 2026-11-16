Tu es un expert de la migration de PHP 7 vers PHP 8.

Le code ci-dessous est en cours de migration. Corrige les risques listés ET toutes les erreurs de validation signalées dans le retour, avec le moins de modifications possible, pour qu'il fonctionne en PHP 8 avec le même comportement que sous PHP 7. Une erreur de validation est obligatoire à corriger même si aucun détecteur ne l'a signalée. En particulier, si PHP signale « Cannot redeclare NOM() », supprime la définition personnalisée de cette fonction : PHP 8 fournit déjà la fonction native. Par exemple :
- mysql_* se remplace par mysqli_* (même ordre d'arguments, la connexion en premier) ;
- un constructeur à l'ancienne (méthode du nom de la classe) devient __construct ;
- une fonction définie par le programme qui existe désormais en natif doit être supprimée (le code appelle alors la version native) ;
- __autoload() devient spl_autoload_register() ;
- un paramètre obligatoire placé après un optionnel : donne-lui aussi une valeur par défaut.

Tu ne renvoies PAS le fichier entier : seulement les modifications, dans ce format exact, une par bloc :

<edit>
<old>
les lignes EXACTES du code à remplacer, copiées telles quelles (même indentation)
</old>
<new>
les lignes de remplacement
</new>
</edit>

Règles :
- "old" doit être copié mot pour mot depuis le code, avec 1 à 5 lignes.
- "old" doit être unique dans le fichier : ajoute une ligne voisine si besoin.
- Ne touche à rien d'autre. N'écris aucun texte avant ou après les blocs.

Risques à corriger :
{risks}

{feedback}

<code>
{code}
</code>
