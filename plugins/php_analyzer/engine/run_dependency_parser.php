
<?php

require __DIR__ . '/dependency_parser.php';

$filePath = $argv[1];

$includes = extractPhpIncludes($filePath);

echo json_encode($includes);
