# -*- coding: utf-8 -*-
"""Statistiques sur un texte (Python 2)."""
import string
import sys
import cPickle
from StringIO import StringIO


def clean(text):
    return string.lower(text)


def word_counts(text):
    counts = {}
    for word in clean(text).split():
        counts[word] = counts.get(word, 0) + 1
    return counts


def top_words(counts, n):
    pairs = counts.items()
    pairs.sort(lambda a, b: cmp(b[1], a[1]))
    return pairs[:n]


def longest_word(text):
    words = text.split()
    lengths = map(len, words)
    return words[lengths.index(max(lengths))]


def count_long(text):
    return len(filter(lambda w: len(w) > 5, text.split()))


def to_unicode(raw):
    return unicode(raw, "utf-8")


def save(counts, path):
    f = file(path, "wb")
    cPickle.dump(counts, f)
    f.close()


def main():
    text = "le chat et le chien et le chat"
    counts = word_counts(text)
    print top_words(counts, 1)
    print longest_word(text), count_long(text)
    print sys.maxint


main()