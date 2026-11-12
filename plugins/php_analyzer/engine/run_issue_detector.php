<?php
/**
 * Détecte les constructions PHP 7 supprimées ou dépréciées en PHP 8.
 *
 * Usage : php run_issue_detector.php fichier.php
 * Sortie : un tableau JSON de problèmes sur la sortie standard.
 */

require __DIR__ . '/../vendor/autoload.php';

use PhpParser\Error;
use PhpParser\Node;
use PhpParser\NodeTraverser;
use PhpParser\NodeVisitorAbstract;
use PhpParser\ParserFactory;

// Fonctions supprimées : nom => [règle, gravité, message, recommandation]
const REMOVED_FUNCTIONS = [
    'each' => ['PHP8_EACH', 'critical',
        'each() est supprimée en PHP 8',
        'Utiliser une boucle foreach'],
    'create_function' => ['PHP8_CREATE_FUNCTION', 'critical',
        'create_function() est supprimée en PHP 8',
        'Utiliser une fonction anonyme (closure)'],
    'ereg' => ['PHP7_EREG', 'critical',
        'Les fonctions ereg sont supprimées', 'Utiliser preg_match()'],
    'eregi' => ['PHP7_EREG', 'critical',
        'Les fonctions ereg sont supprimées', 'Utiliser preg_match()'],
    'ereg_replace' => ['PHP7_EREG', 'critical',
        'Les fonctions ereg sont supprimées', 'Utiliser preg_replace()'],
    'eregi_replace' => ['PHP7_EREG', 'critical',
        'Les fonctions ereg sont supprimées', 'Utiliser preg_replace()'],
    'split' => ['PHP7_SPLIT', 'critical',
        'split() est supprimée', 'Utiliser explode() ou preg_split()'],
    'money_format' => ['PHP8_MONEY_FORMAT', 'critical',
        'money_format() est supprimée en PHP 8',
        'Utiliser NumberFormatter'],
    'get_magic_quotes_gpc' => ['PHP8_MAGIC_QUOTES', 'critical',
        'get_magic_quotes_gpc() est supprimée en PHP 8',
        'Supprimer l\'appel (les magic quotes n\'existent plus)'],
    'get_magic_quotes_runtime' => ['PHP8_MAGIC_QUOTES', 'critical',
        'get_magic_quotes_runtime() est supprimée en PHP 8',
        'Supprimer l\'appel (les magic quotes n\'existent plus)'],
];

// Fonctions internes qui ne doivent plus recevoir null (déprécié en PHP 8.1)
const NULL_SENSITIVE_FUNCTIONS = [
    'strlen', 'trim', 'ltrim', 'rtrim', 'strpos', 'stripos', 'strrpos',
    'str_replace', 'str_contains', 'htmlspecialchars', 'htmlentities',
    'explode', 'strtolower', 'strtoupper', 'substr', 'strcmp', 'md5',
    'urlencode', 'json_decode', 'preg_match', 'preg_replace',
];

function createLegacyParser()
{
    $factory = new ParserFactory();
    if (method_exists($factory, 'createForVersion')) {
        // PHP-Parser 5 : on lit le code comme du PHP 7.4
        return $factory->createForVersion(
            \PhpParser\PhpVersion::fromComponents(7, 4)
        );
    }
    // PHP-Parser 4
    return $factory->create(ParserFactory::PREFER_PHP7);
}

function makeIssue($line, $rule, $severity, $message, $recommendation)
{
    return [
        'line' => (int) $line,
        'rule_id' => $rule,
        'severity' => $severity,
        'message' => $message,
        'recommendation' => $recommendation,
    ];
}

function isNullConstant($expr)
{
    return $expr instanceof Node\Expr\ConstFetch
        && strtolower($expr->name->toString()) === 'null';
}

class DeprecationVisitor extends NodeVisitorAbstract
{
    public $issues = [];

    public function enterNode(Node $node)
    {
        if ($node instanceof Node\Expr\FuncCall
            && $node->name instanceof Node\Name) {
            $this->checkFunctionCall($node);
        }

        if ($node instanceof Node\Stmt\Function_) {
            if (strtolower($node->name->toString()) === '__autoload') {
                $this->issues[] = makeIssue($node->getStartLine(),
                    'PHP8_AUTOLOAD', 'critical',
                    '__autoload() est supprimée en PHP 8',
                    'Utiliser spl_autoload_register()');
            }
        }

        if ($node instanceof Node\Stmt\Function_
            || $node instanceof Node\Stmt\ClassMethod
            || $node instanceof Node\Expr\Closure) {
            $this->checkParameterOrder($node->params);
        }

        if ($node instanceof Node\Stmt\Class_ && $node->name !== null) {
            $this->checkOldConstructor($node);
        }

        return null;
    }

    private function checkFunctionCall($node)
    {
        $name = strtolower(ltrim($node->name->toString(), '\\'));
        $line = $node->getStartLine();

        if (isset(REMOVED_FUNCTIONS[$name])) {
            [$rule, $severity, $message, $reco] = REMOVED_FUNCTIONS[$name];
            $this->issues[] = makeIssue($line, $rule, $severity, $message, $reco);
        }

        if (strpos($name, 'mysql_') === 0) {
            $this->issues[] = makeIssue($line, 'PHP7_MYSQL_API', 'critical',
                'L\'extension mysql_* est supprimée',
                'Utiliser mysqli ou PDO');
        }

        if (in_array($name, NULL_SENSITIVE_FUNCTIONS, true)) {
            foreach ($node->args as $arg) {
                if ($arg instanceof Node\Arg && isNullConstant($arg->value)) {
                    $this->issues[] = makeIssue($line, 'PHP81_NULL_ARGUMENT',
                        'warning',
                        'null passé à une fonction interne (déprécié)',
                        'Passer une chaîne vide ou tester la valeur avant');
                    break;
                }
            }
        }
    }

    private function checkParameterOrder(array $params)
    {
        $optionalSeen = false;
        foreach ($params as $param) {
            if ($param->variadic) {
                continue;
            }
            if ($param->default !== null) {
                $implicitNullable = $param->type !== null
                    && isNullConstant($param->default);
                if (!$implicitNullable) {
                    $optionalSeen = true;
                }
            } elseif ($optionalSeen) {
                $this->issues[] = makeIssue($param->getStartLine(),
                    'PHP8_REQUIRED_AFTER_OPTIONAL', 'warning',
                    'Paramètre obligatoire placé après un paramètre optionnel',
                    'Réordonner les paramètres ou donner une valeur par défaut');
            }
        }
    }

    private function checkOldConstructor($class)
    {
        $className = strtolower($class->name->toString());
        $hasModern = false;
        $oldMethod = null;
        foreach ($class->getMethods() as $method) {
            $methodName = strtolower($method->name->toString());
            if ($methodName === '__construct') {
                $hasModern = true;
            } elseif ($methodName === $className) {
                $oldMethod = $method;
            }
        }
        if ($oldMethod !== null && !$hasModern) {
            $this->issues[] = makeIssue($oldMethod->getStartLine(),
                'PHP8_OLD_CONSTRUCTOR', 'high',
                'Constructeur à l\'ancienne (méthode du nom de la classe) : '
                . 'ce n\'est plus un constructeur en PHP 8',
                'Renommer la méthode en __construct');
        }
    }
}

/** Détecte l'accès par accolades ($chaine{0}), supprimé en PHP 8. */
function detectCurlyBraceOffsets($code)
{
    $issues = [];
    $line = 1;
    $previous = null;

    foreach (token_get_all($code) as $token) {
        if (is_array($token)) {
            $line = $token[2];
            $id = $token[0];
            $text = $token[1];
        } else {
            $id = null;
            $text = $token;
        }

        if ($id === null && $text === '{'
            && ($previous === T_VARIABLE || $previous === ']')) {
            $issues[] = makeIssue($line, 'PHP8_CURLY_BRACE_OFFSET', 'critical',
                'Accès à un index avec des accolades {} supprimé en PHP 8',
                'Utiliser des crochets []');
        }

        $previous = ($id !== null) ? $id : $text;
        $line += substr_count($text, "\n");
    }

    return $issues;
}

// ---------------------------------------------------------------- programme

if ($argc < 2) {
    fwrite(STDERR, "Usage : php run_issue_detector.php fichier.php\n");
    exit(1);
}

$file = $argv[1];
$code = @file_get_contents($file);
if ($code === false) {
    fwrite(STDERR, "Fichier illisible : $file\n");
    exit(1);
}

$issues = detectCurlyBraceOffsets($code);

try {
    $ast = createLegacyParser()->parse($code);
    $visitor = new DeprecationVisitor();
    $traverser = new NodeTraverser();
    $traverser->addVisitor($visitor);
    $traverser->traverse($ast);
    $issues = array_merge($issues, $visitor->issues);
} catch (Error $error) {
    $issues[] = makeIssue($error->getStartLine() > 0 ? $error->getStartLine() : 1,
        'PHP_PARSE_ERROR', 'warning',
        'Fichier non analysable : ' . $error->getRawMessage(),
        'Vérifier la syntaxe du fichier');
}

usort($issues, function ($a, $b) {
    return $a['line'] <=> $b['line'];
});

echo json_encode($issues, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), "\n";