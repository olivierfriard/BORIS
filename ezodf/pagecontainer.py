#!/usr/bin/env python
#coding:utf-8
# Purpose: abstract page container
# Created: 12.02.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .compatibility import tostr, is_string
from . import wrapcache

class AbstractPageContainer(object):
    def __init__(self, xmlbody, childtag, nametag):
        self._childtag = childtag
        self._nametag = nametag
        self.xmlnode = xmlbody

    def __len__(self):
        return len(self._xmlchildren())

    def __iter__(self):
        return (wrapcache.wrap(child) for child in self._xmlchildren())

    def _xmlchildren(self):
        return self.xmlnode.findall(self._childtag)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._child_by_index(key)
        elif is_string(key):
            return self._child_by_name(key)
        else:
            raise TypeError('key has invalid type.')

    def __setitem__(self, key, child):
        if not self._is_valid_child(child):
            raise TypeError('child has to be a Table or Page object.')
        if isinstance(key, int):
            oldchild = self._child_by_index(key)
        elif is_string(key):
            oldchild = self._child_by_name(key)
        else:
            raise TypeError('key has invalid type.')
        self.xmlnode.replace(oldchild.xmlnode, child.xmlnode)

    def __delitem__(self, key):
        if isinstance(key, int):
            oldchild = self._child_by_index(key)
        elif is_string(key):
            oldchild = self._child_by_name(key)
        else:
            raise TypeError('key has invalid type.')
        self.xmlnode.remove(oldchild.xmlnode)

    def __iadd__(self, other):
        self.append(other)
        return self

    def _is_valid_child(self, child):
        try:
            return  child.TAG == self._childtag
        except AttributeError:
            return False

    def _child_by_name(self, name):
        for child in self._xmlchildren():
            if name == child.get(self._nametag):
                return wrapcache.wrap(child)
        raise KeyError("child '%s' not found." % name)

    def _child_by_index(self, index):
        sheets = list(self._xmlchildren())
        return wrapcache.wrap(sheets[index])

    def append(self, child):
        if self._is_valid_child(child):
            self.xmlnode.append(child.xmlnode)
            return child
        else:
            raise TypeError('Unable to append: %s' % tostr(child))

    def names(self):
        return (child.get(self._nametag) for child in self._xmlchildren())

    def index(self, child):
        return self.xmlnode.index(child.xmlnode)

    def insert(self, index, child):
        self.xmlnode.insert(int(index), child.xmlnode)
        return child
