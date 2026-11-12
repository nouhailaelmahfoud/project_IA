<?php

class Client {
    var $name;

    function Client($name) {
        $this->name = $name;
    }

    function first($text) {
        return $text{0};
    }
}

function build($prefix = "id", $number) {
    return $prefix . $number;
}

function query_users($link) {
    $result = mysql_query("SELECT * FROM users", $link);
    while (list($key, $value) = each($row)) {
        echo $key;
    }
    $f = create_function('$a', 'return $a * 2;');
    return strlen(null);
}

function ok_function(?string $a = null, $b = 2) {
    return htmlspecialchars("texte");
}