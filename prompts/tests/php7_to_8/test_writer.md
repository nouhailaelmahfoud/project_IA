Tu es un ingénieur QA. Écris des tests de CARACTÉRISATION PHPUnit pour le code PHP 7 ci-dessous : ils doivent décrire ce que le code FAIT aujourd'hui en PHP 7.4, pas ce qu'il devrait faire.

Contraintes :
- Le fichier de test s'appelle GeneratedTest.php et contient une classe `GeneratedTest` qui étend `PHPUnit\Framework\TestCase` (compatible PHPUnit 9 et 10 : pas d'annotation ni d'attribut, pas de data provider).
- Charge le code avec `require_once __DIR__ . '/src/{filename}';`.
- Les méthodes de test s'appellent testXxx, sans type de retour exigé.
- Écris les valeurs attendues en littéraux, calculées en lisant le code avec la sémantique de PHP 7.4.
- Pas de réseau, pas de base de données, pas d'aléatoire, pas de date ou d'heure.
- De 5 à 12 tests courts, qui couvrent les fonctions principales.

Réponds UNIQUEMENT avec le fichier de test complet (il commence par <?php), dans un seul bloc de code PHP.

{feedback}

Fichier `{filename}` :
<code>
{code}
</code>