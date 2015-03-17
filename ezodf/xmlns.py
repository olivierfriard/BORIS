#!/usr/bin/env python
#coding:utf-8
# Purpose: support module to handle xml namespaces
# Created: 27.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from lxml import etree

from .const import ALL_NSMAP

def subelement(parent, tag, new=True):
    """ Find/create SubElement `tag` in parent node.
    """
    element = parent.find(tag)
    if (element is None) and (new is True):
        element = etree.SubElement(parent, tag)
    return element

class _XMLNamespaces(object):
    def __init__(self, namespaces):
        self.prefix2uri = {}
        self.uri2prefix = {}
        self._cache = {}
        self.update(namespaces)

    def update(self, namespaces):
        for prefix, uri in namespaces.items():
            self.register_namespace(prefix, uri)

    def register_namespace(self, prefix, uri):
        self.prefix2uri[prefix] = uri
        self.uri2prefix[uri] = prefix
        self._cache.clear()

    def _prefix2clark_cached(self, tag):
        """ Convert tag in prefix notation into clark notation. """
        # cached calls
        try:
            return self._cache[tag]
        except KeyError:
            if tag[0] == '{': # tag is already in clark notation
                return tag
            else:
                cn = self._prefix2clark(tag)
                self._cache[tag] = cn
                return cn

    def _prefix2clark(self, tag):
        """ Convert tag in prefix notation into clark notation. """
        # uncached calls
        prefix, local = self._split_prefix(tag)
        return "{%s}%s" % (self.prefix2uri[prefix], local)

    def _split_prefix(self, tag):
        if tag.count(':') == 1:
            return tag.split(':')
        else:
            raise ValueError("prefix-notation required 'prefix:local': %s" % tag)

# global ODF Namespaces with OASIS prefixes
XML = _XMLNamespaces(ALL_NSMAP)
CN = XML._prefix2clark_cached

class XMLMixin(object):
    def tobytes(self, xml_declaration=None, pretty_print=False):
        """ Returns the XML representation as bytes in 'UTF-8' encoding.

        :param bool xml_declaration: create XML declaration
        :param bool pretty-print: enables formatted XML
        """
        return etree.tostring(self.xmlnode, encoding='UTF-8',
                              xml_declaration=xml_declaration,
                              pretty_print=pretty_print)

class _ClassRegistry(object):
    """ Class Registry """
    _classmap = {}

    def register(self, cls):
        """ Class registration. """
        self._classmap[cls.TAG] = cls
        return cls

    def wrap(self, element):
        """ Wrap element into a wrapper object. """
        try:
            cls = self._classmap[element.tag]
        except KeyError: # wrap it into the GenericWrapper
            cls = self._classmap['GenericWrapper']
        return cls(xmlnode=element)


_class_registry = _ClassRegistry()
register_class = _class_registry.register
wrap = _class_registry.wrap

WRAPNS = """<root
{0}
>
%s
</root>
""".format(" ".join(
    ['xmlns:%s ="%s"' % (key, value) for key, value in ALL_NSMAP.items()]
    ))

def fake_element(xmlcontent):
    element = etree.XML(WRAPNS % xmlcontent)
    return wrap(element[0])
