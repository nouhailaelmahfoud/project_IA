<?php
// Panier d'achat (PHP 7)

class Cart {
    var $items = array();

    function Cart() {
        $this->items = array();
    }

    function add($name, $price = 0, $qty) {
        $this->items[$name] = array('price' => $price, 'qty' => $qty);
    }

    function total() {
        $total = 0;
        while (list($name, $item) = each($this->items)) {
            $total += $item['price'] * $item['qty'];
        }
        return $total;
    }

    function label($name) {
        return strtoupper($name{0}) . substr($name, 1);
    }

    function has_stock($qty) {
        if ($qty == "all") {
            return true;
        }
        return $qty > 0;
    }

    function double_price($price) {
        return $price * 2;
    }
}

$cart = new Cart();
$cart->add("stylo", 2, 10);
echo money_format('%i', $cart->total());
echo $cart->double_price("abc");