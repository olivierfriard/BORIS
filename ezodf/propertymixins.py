#!/usr/bin/env python
#coding:utf-8
# Purpose: property mixins
# Created: 30.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .compatibility import tostr
from .xmlns import CN, subelement


def StringProperty(name, doc=None):
    def getter(self):
        return self.xmlnode.get(name)
    def setter(self, value):
        self.xmlnode.set(name, value)
    def deleter(self):
        del self.xmlnode.attrib[name]
    return property(getter, setter, deleter, doc)

def BooleanProperty(name, doc=None):
    def getter(self):
        return self.xmlnode.get(name) == 'true'
    def setter(self, value):
        value = 'true' if value else 'false'
        self.xmlnode.set(name, value)
    def deleter(self):
        del self.xmlnode.attrib[name]
    return property(getter, setter, deleter, doc)

def FloatProperty(name, doc=None):
    def getter(self):
        value = self.xmlnode.get(name)
        if value is None:
            return None
        else:
            return float(value)
    def setter(self, value):
        self.xmlnode.set(name, tostr(value))
    def deleter(self):
        del self.xmlnode.attrib[name]
    return property(getter, setter, deleter, doc)

def IntegerProperty(name, doc=None):
    def getter(self):
        value = self.xmlnode.get(name)
        if value is None:
            return None
        else:
            return int(value)
    def setter(self, value):
        self.xmlnode.set(name, tostr(value))
    def deleter(self):
        del self.xmlnode.attrib[name]
    return property(getter, setter, deleter, doc)

def IntegerWithLowerLimitProperty(name, lower_limit=0, doc=None):
    def getter(self):
        value = self.xmlnode.get(name)
        if value is None:
            return lower_limit
        else:
            return max(lower_limit, int(value))
    def setter(self, value):
        value = int(value)
        self.xmlnode.set(name, tostr(max(lower_limit, value)))
    def deleter(self):
        del self.xmlnode.attrib[name]
    return property(getter, setter, deleter, doc)

class TextNumberingMixin(object):
    @property
    def start_value(self):
        value = self.get_attr(CN('text:start-value'))
        return int(value) if value is not None else None
    @start_value.setter
    def start_value(self, value):
        value = tostr(max(int(value), 1))
        self.set_attr(CN('text:start-value'), value)

    @property
    def formatted_number(self):
        formatted_number = self.xmlnode.find(CN('text:number'))
        return formatted_number.text if formatted_number is not None else None
    @formatted_number.setter
    def formatted_number(self, value):
        formatted_number = subelement(self.xmlnode, CN('text:number'))
        formatted_number.text = tostr(value)

class TableVisibilityMixin(object):
    VALID_VISIBILITY_STATES = frozenset( ('visible', 'collapse', 'filter') )
    @property
    def visibility(self):
        value = self.get_attr(CN('table:visibility'))
        if value is None:
            value = 'visible'
        return value
    @visibility.setter
    def visibility(self, value):
        if value not in self.VALID_VISIBILITY_STATES:
            raise ValueError("allowed values are: 'visible', 'collapse', 'filter'")
        self.set_attr(CN('table:visibility'), value)
