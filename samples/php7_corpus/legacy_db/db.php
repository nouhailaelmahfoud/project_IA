<?php
// Accès base de données à l'ancienne (PHP 7)

$link = mysql_connect("localhost", "root", "");
mysql_select_db("shop", $link);

function find_user($id) {
    $res = mysql_query("SELECT * FROM users WHERE id = " . $id);
    return mysql_fetch_assoc($res);
}

function __autoload($class) {
    require $class . ".php";
}

$handler = create_function('$x', 'return strtolower($x);');

$parts = split(",", $_GET['q']);
$total = count($_GET['q']);

if (get_magic_quotes_gpc()) {
    $q = stripslashes($_GET['q']);
}

function render($user, $title = "Profil", $size) {
    return "<h1>" . $title . "</h1>" . $user['name'] . $size;
}

echo render(find_user(1), "Fiche", 12);