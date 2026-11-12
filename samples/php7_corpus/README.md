# Corpus PHP 7 : pièges non détectés par les règles

| Projet | Fichier:ligne | Piège | Comportement en PHP 8 |
|---|---|---|---|
| shop | cart.php:28 | `$qty == "all"` | `0 == "all"` était vrai en PHP 7, faux en PHP 8 |
| shop | cart.php:42 | `double_price("abc")` | Calcul avec une chaîne non numérique : TypeError |
| blog | blog.php:4 | `function str_contains` | Cette fonction existe désormais en natif : erreur de redéclaration |
| blog | blog.php:9 | `implode($posts, ", ")` | Ancien ordre des arguments supprimé : TypeError |
| legacy_db | db.php:19 | `count($_GET['q'])` | `count()` sur une chaîne : TypeError |