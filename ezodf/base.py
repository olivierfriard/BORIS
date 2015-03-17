#!/usr/bin/env python
#coding:utf-8
# Purpose: GenericWrapper for ODF content objects
# Created: 03.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .xmlns import etree, register_class, wrap
from .compatibility import itermap, tostr

def safelen(text):
    return len(text) if text else 0

@register_class
class GenericWrapper(object):
    TAG = 'GenericWrapper'

    def __init__(self, xmlnode=None):
        if xmlnode is not None:
            self.xmlnode = xmlnode
        else:
            self.xmlnode = etree.Element(self.TAG)

    def __iter__(self):
        return itermap(wrap, self.xmlnode.iterchildren())

    def __len__(self):
        return len(self.xmlnode)

    @property
    def text(self):
        return self.xmlnode.text
    @text.setter
    def text(self, value):
        self.xmlnode.text = value

    @property
    def tail(self):
        return self.xmlnode.tail
    @tail.setter
    def tail(self, value):
        self.xmlnode.tail = value

    @property
    def kind(self):
        return self.__class__.__name__

    def get_xmlroot(self):
        xmlroot = parent = self.xmlnode
        while parent is not None:
            xmlroot = parent
            parent = parent.getparent()
        return xmlroot

    ## Index operations

    def __getitem__(self, index):
        return self.get_child(index)

    def __setitem__(self, index, element):
        self.set_child(index, element)

    def __delitem__(self, index):
        self.del_child(index)

    def __iadd__(self, other):
        self.append(other)
        return self

    def index(self, child):
        """ Get numeric index of `child`. """
        return self.xmlnode.index(child.xmlnode)

    def insert(self, index, child):
        """ Insert child at position `index`. """
        self.xmlnode.insert(int(index), child.xmlnode)
        return child # pass through

    def get_child(self, index):
        """ Get children at `index` as wrapped object. """
        xmlelement = self.xmlnode[int(index)]
        return wrap(xmlelement)

    def set_child(self, index, element):
        """ Set (replace) the child at position `index` by element. """
        found = self.xmlnode[int(index)]
        self.xmlnode.replace(found, element.xmlnode)

    def del_child(self, index):
        """ Delete child at position `index`. """
        del self.xmlnode[int(index)]

    def findall(self, tag):
        """ Find all subelements by xml-tag (in Clark Notation). """
        return (wrap(xmlnode) for xmlnode in self.xmlnode.findall(tag))

    def find(self, tag):
        """ Find first subelements by xml-tag (in Clark Notation). """
        found = self.xmlnode.find(tag)
        return wrap(found) if found is not None else None

    ## Attribute access for the xmlnode element

    def get_attr(self, key, default=None):
        """ Get the `key` attribute value of the xmlnode element or `default`
        if `key` does not exist.
        """
        value = self.xmlnode.get(key)
        return default if value is None else value

    def get_bool_attr(self, key):
        value = self.xmlnode.get(key)
        if value:
            return True if value == 'true' else False
        else:
            return False

    def set_attr(self, key, value):
        """ Set the `key` attribute of the xmlnode element to `value`. """
        if value:
            self.xmlnode.set(key, tostr(value))
        else:
            raise ValueError(value)

    def set_bool_attr(self, key, value):
        self.xmlnode.set(key, 'true' if value else 'false')

    ## List operations

    def append(self, child):
        """ Append `child` as to node. """
        self.xmlnode.append(child.xmlnode)
        return child # pass through

    def insert_before(self, target, child):
        """ Insert `child` before to `target`. """
        position = self.index(target)
        self.insert(position, child)
        return child # pass through

    def remove(self, child):
        """ Remove `child` object from node. """
        self.xmlnode.remove(child.xmlnode)

    def replace(self, child, newchild):
        self.xmlnode.replace(child.xmlnode, newchild.xmlnode)

    def clear(self):
        """ Remove all content from node. """
        self.xmlnode.clear()

    ## production code

    @property
    def textlen(self):
        """ Returns the character count of the plain text content as int. """
        return safelen(self.xmlnode.text)

    def plaintext(self):
        """ Get content of node as plain (unformatted) text string. """
        text = self.xmlnode.text
        return text if text else ""
