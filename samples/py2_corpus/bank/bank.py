# -*- coding: utf-8 -*-
"""Mini application bancaire (Python 2)."""
import sys


class InsufficientFunds(Exception):
    pass


class Account(object):
    def __init__(self, owner, balance=0L):
        self.owner = owner
        self.balance = balance

    def __nonzero__(self):
        return self.balance <> 0

    def __cmp__(self, other):
        return cmp(self.balance, other.balance)

    def __unicode__(self):
        return u"%s: %d" % (self.owner, self.balance)

    def withdraw(self, amount):
        if amount > self.balance:
            raise InsufficientFunds, "solde insuffisant"
        self.balance -= amount

    def monthly_interest(self):
        return self.balance * 3 / 100


def transfer(src, dst, amount):
    try:
        src.withdraw(amount)
    except InsufficientFunds, e:
        print >>sys.stderr, "Erreur :", e
        return False
    dst.balance += amount
    return True


def debug(obj):
    return `obj`


def run(code):
    exec code


def main():
    a = Account("Ali", 1000)
    b = Account("Sara")
    print transfer(a, b, 300)
    print a.monthly_interest(), debug(b.balance)
    print a > b


main()