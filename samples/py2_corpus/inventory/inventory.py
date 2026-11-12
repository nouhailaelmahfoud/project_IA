# -*- coding: utf-8 -*-
"""Gestion de stock simple (Python 2)."""
import sys


class Inventory:
    def __init__(self):
        self.items = {}

    def add(self, name, qty, price):
        if self.items.has_key(name):
            self.items[name]["qty"] += qty
        else:
            self.items[name] = {"qty": qty, "price": price}

    def total_value(self):
        total = 0
        for name, data in self.items.iteritems():
            total += data["qty"] * data["price"]
        return total

    def average_price(self):
        prices = [d["price"] for d in self.items.values()]
        return sum(prices) / len(prices)

    def names_sorted(self):
        names = self.items.keys()
        names.sort()
        return names


def main():
    inv = Inventory()
    inv.add("vis", 100, 2)
    inv.add("ecrou", 50, 3)
    inv.add("vis", 20, 2)
    print "Valeur totale :", inv.total_value()
    print "Prix moyen   :", inv.average_price()
    print "Articles     :", inv.names_sorted()
    if len(sys.argv) > 1:
        name = raw_input("Article ? ")
        print name


if __name__ == "__main__":
    main()