#!/usr/bin/env python
#coding:utf-8
# Purpose: ODF meta.xml document management
# Created: 28.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from datetime import datetime

from .compatibility import tostr
from .xmlns import CN, subelement, etree, register_class, XMLMixin
from .const import META_NSMAP, GENERATOR, META_NS

TAGS = {
    'generator': 'meta:generator',
    'title': 'dc:title',
    'description': 'dc:description',
    'subject': 'dc:subject',
    'initial-creator': 'meta:initial-creator',
    'creator': 'dc:creator',
    'creation-date': 'meta:creation-date',
    'date': 'dc:date',
    'editing-cycles': 'meta:editing-cycles',
    'language': 'dc:language',
}

@register_class
class OfficeDocumentMeta(XMLMixin):
    TAG = CN('office:document-meta')
    generator = GENERATOR

    def __init__(self, xmlnode=None):
        if xmlnode is None:
            self.xmlnode = etree.Element(self.TAG, nsmap=META_NSMAP)
        elif xmlnode.tag == self.TAG:
            self.xmlnode = xmlnode
        else:
            raise ValueError("Unexpected root node: %s" % xmlnode.tag)

        self._setup()
        self.keywords = Keywords(self.meta)
        self.usertags = Usertags(self.meta)

        stats = self.meta.find(CN('meta:document-statistic'))
        if stats is None:
            stats = etree.SubElement(self.meta, CN('meta:document-statistic'))
        self.count = Statistic(stats)

    def _setup(self):
        self.meta = self.xmlnode.find(CN('office:meta'))
        if self.meta is None: # this is a new document
            self.meta = subelement(self.xmlnode, CN('office:meta'))
            self.xmlnode.set(CN('grddl:transformation'), "http://docs.oasis-open.org/office/1.2/xslt/odf2rdf.xsl")
            self['creation-date'] = datetime.now().isoformat()
            self.touch()

    def clear(self):
        """ Delete all metatags. """
        self.meta.clear()
        self.count.stats = etree.SubElement(self.meta, CN('meta:document-statistic'))

    def touch(self):
        self['date'] = datetime.now().isoformat()
        self['generator'] = OfficeDocumentMeta.generator

    def __setitem__(self, key, value):
        cnkey = CN(TAGS[key]) # key in clark notation
        element = subelement(self.meta, cnkey)
        element.text = value

    def __getitem__(self, key):
        element = self.meta.find(CN(TAGS[key]))
        if element is not None:
            return element.text
        else:
            raise KeyError(key)

    def inc_editing_cycles(self):
        try:
            count = self['editing-cycles']
            try:
                count = int(count) + 1
            except ValueError:
                count = 1
        except KeyError:
            count = 1
        self['editing-cycles'] = tostr(count)

class Keywords(object):
    def __init__(self, meta):
        self.meta = meta

    def __iter__(self):
        """ Iterate over all keywords. """
        for keyword in self.meta.findall(CN('meta:keyword')):
            yield keyword.text

    def __contains__(self, keyword):
        """ True if 'keyword' exists, else False. """
        return self._find(keyword) is not None

    def add(self, keyword):
        """ Add 'keyword' to meta data. """
        tag = self._find(keyword)
        if tag is None:
            tag = etree.SubElement(self.meta, CN('meta:keyword'))
            tag.text = keyword

    def remove(self, keyword):
        """ Remove 'keyword' from meta data. """
        tag = self._find(keyword)
        if tag is not None:
            self.meta.remove(tag)

    def clear(self):
        """ Delete all keywords. """
        for tag in self.meta.findall(CN('meta:keyword')):
            self.meta.remove(tag)

    def _find(self, keyword):
        """ Find XML element for `keyword`. """
        for tag in self.meta.findall(CN('meta:keyword')):
            if  keyword == tag.text:
                return tag
        return None

class Usertags(object):
    def __init__(self, meta):
        self.meta = meta

    def __iter__(self):
        """ Iterate over all user-defined metatags.

        :returns: (name, value) tuples
        """
        for metatag in self.meta.findall(CN('meta:user-defined')):
            yield (metatag.get(CN('meta:name')), metatag.text)

    def __contains__(self, name):
        return self._find(name) is not None

    def set(self, name, value, value_type=None):
        """ Set/Replace user-defined metatag.
        """
        tag = self._find(name)
        if tag is None:
            tag = etree.SubElement(self.meta, CN('meta:user-defined'))
            tag.set(CN('meta:name'), name)
        tag.text = tostr(value)
        if value_type is not None:
            tag.set(CN('meta:value-type'), value_type)

    def __setitem__(self, name, value):
        self.set(name, value)

    def __getitem__(self, name):
        """ Get value of user-defined metatag 'name'.

        Raises KeyError, if 'name' not exist.
        """
        tag = self._find(name)
        if tag is not None:
            return tag.text
        raise KeyError(name)

    def __delitem__(self, name):
        """ Remove user defined metatag 'name'.

        Raises KeyError, if 'name' not exist.
        """
        tag = self._find(name)
        if tag is not None:
            self.meta.remove(tag)
        else:
            raise KeyError(name)

    def typeof(self, name):
        """ Get type of user defined tag `name`. """
        tag = self._find(name)
        if tag is not None:
            return tag.get(CN('meta:value-type'), 'string')
        raise KeyError(name)

    def update(self, d):
        """ Set user defined tags from dict `d`. """
        for key, value in d.items():
            self.__setitem__(key, value)

    def clear(self):
        """ Delete all user defined tags. """
        for tag in self.meta.findall(CN('meta:user-defined')):
            self.meta.remove(tag)

    def _find(self, name):
        for tag in self.meta.findall(CN('meta:user-defined')):
            if name == tag.get(CN('meta:name')):
                return tag
        return None

class Statistic(object):
    TYPES = frozenset(['page', 'table', 'draw', 'image', 'object',
                       'ole-object', 'paragraph', 'word', 'character',
                       'row', 'frame', 'sentence', 'syllable',
                       'non-whitespace-character', 'cell'])
    NS = '{' + META_NS + '}%s-count'

    def __init__(self, stats):
        self.stats = stats

    def __getitem__(self, key):
        if key in Statistic.TYPES:
            val = self.stats.get(Statistic.NS % key)
            retval = 0
            try:
                retval = int(val)
            except ValueError:
                pass # it's not an int, should not happen (but shit happens)
            except TypeError:
                pass # None, no stats for `key`
            return retval
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        if key in Statistic.TYPES:
            self.stats.set(Statistic.NS % key, tostr(value))
        else:
            raise KeyError(key)

    def __iter__(self):
        """ Iterate over all statistics.

        :returns: (name, value) tulples
        """
        prefix = len(META_NS) + 2
        for key, value in self.stats.items():
            yield (key[prefix:-6], int(value))

    def update(self, d):
        """ Set statistics from dict `d`. """
        for key, value in d.items():
            self.__setitem__(key, value)

    def clear(self):
        """ Clear all statistics. """
        self.stats.clear()
