import urllib2

def main():
    print "hello"
    for i in xrange(3):
        print i
    d = {}
    if d.has_key("a"):
        print d.keys()
    try:
        x = unicode("abc")
    except ValueError, e:
        raise ValueError, "bad"
    if 1 <> 2:
        name = raw_input("name? ")

main()

from __future__ import print_function
import sys

class Flag(object):
    def __nonzero__(self):
        return True

def more():
    d = {"a": 1}
    for k, v in d.iteritems():
        print >>sys.stderr, k
    n = 10L
    s = `n`
    exec "x = 1"
    return u"texte"