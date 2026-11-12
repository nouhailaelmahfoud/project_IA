<?php
// Mini blog (PHP 7)

function str_contains($haystack, $needle) {
    return strpos($haystack, $needle) !== false;
}

function titles($posts) {
    return implode($posts, ", ");
}

function clean($input) {
    $input = ereg_replace("[^a-z ]", "", $input);
    return trim($input);
}

function last_char($text) {
    return $text{strlen($text) - 1};
}

function excerpt($text, $length = 20) {
    return substr($text, 0, $length) . htmlspecialchars(null);
}

echo titles(array("Un", "Deux"));
echo last_char("bonjour");