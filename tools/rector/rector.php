<?php
// Règles Rector choisies pour la migration PHP 7 -> PHP 8.
// Volontairement peu nombreuses : uniquement ce qui est supprimé ou changé en PHP 8.
// Le reste (constructeurs à l'ancienne, mysql_*, etc.) est traité par les
// détecteurs fixes et le modèle de langage.
use Rector\CodingStyle\Rector\FuncCall\ConsistentImplodeRector;
use Rector\Config\RectorConfig;
use Rector\Php70\Rector\FuncCall\EregToPregMatchRector;
use Rector\Php72\Rector\FuncCall\CreateFunctionToAnonymousFunctionRector;
use Rector\Php72\Rector\While_\WhileEachToForeachRector;
use Rector\Php74\Rector\ArrayDimFetch\CurlyToSquareBracketArrayStringRector;
use Rector\Php74\Rector\FuncCall\MoneyFormatToNumberFormatRector;

return RectorConfig::configure()
    ->withoutParallel()
    ->withRules([
        WhileEachToForeachRector::class,              // each() supprimée
        CreateFunctionToAnonymousFunctionRector::class, // create_function() supprimée
        CurlyToSquareBracketArrayStringRector::class,   // $texte{0} -> $texte[0]
        EregToPregMatchRector::class,                   // ereg*(), split() supprimées
        MoneyFormatToNumberFormatRector::class,         // money_format() supprimée
        ConsistentImplodeRector::class,                 // implode($tableau, $sep) -> implode($sep, $tableau)
    ]);
