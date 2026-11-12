
<?php

require __DIR__ . '/../vendor/autoload.php';
use PhpParser\ParserFactory;
use PhpParser\PhpVersion;
use PhpParser\Node;
use PhpParser\Node\Expr\Include_;


function resolveIncludeExpression($expression, $currentFile)
{
    // Cas 1 : chemin écrit directement sous forme de chaîne
    if ($expression instanceof PhpParser\Node\Scalar\String_) {
        return $expression->value;
    }

    // Cas 2 : concaténation avec le point (.)
    if ($expression instanceof PhpParser\Node\Expr\BinaryOp\Concat) {

        $left = resolveIncludeExpression(
            $expression->left,
            $currentFile
        );

        $right = resolveIncludeExpression(
            $expression->right,
            $currentFile
        );

        if ($left !== null && $right !== null) {
            return $left . $right;
        }
    }

    // Cas 3 : constante magique __DIR__
    if ($expression instanceof PhpParser\Node\Scalar\MagicConst\Dir) {
        return dirname($currentFile);
    }

    return null;
}

function normalizePath($path, $currentFile)
{
    // Si le chemin est relatif, le construire depuis le dossier courant
    if (!preg_match('/^[A-Za-z]:[\/\\\\]/', $path) && $path[0] !== '/') {
        $path = dirname($currentFile) . DIRECTORY_SEPARATOR . $path;
    }

    // Normaliser le chemin
    $realPath = realpath($path);

    if ($realPath !== false) {
        return str_replace('\\', '/', $realPath);
    }

    return str_replace('\\', '/', $path);
}

function extractPhpIncludes($filePath)
{
    $parser = (new ParserFactory())->createForVersion(
        PhpVersion::fromString('7.4')
    );

    $code = file_get_contents($filePath);
    $ast = $parser->parse($code);

   $visitor = new class($filePath) extends PhpParser\NodeVisitorAbstract {

    public $includes = [];
    private $currentFile;

    public function __construct($currentFile)
    {
        $this->currentFile = $currentFile;
    }

    public function enterNode(Node $node)
    {
        if ($node instanceof Include_) {

            $expression = $node->expr;

            $resolvedPath = resolveIncludeExpression(
                $expression,
                $this->currentFile
            );

            if ($resolvedPath !== null) {
                $this->includes[] = [
                    'type' => $node->type,
                    'path' => normalizePath($resolvedPath, $this->currentFile),
                    'exists' => file_exists(
        normalizePath($resolvedPath, $this->currentFile)
    ),
                    'line' => $node->getStartLine()
                ];
            }
        }
    }
};



    $traverser = new PhpParser\NodeTraverser();
    $traverser->addVisitor($visitor);
    $traverser->traverse($ast ?? []);

    return $visitor->includes;
}

