#!/usr/bin/env python
#coding:utf-8
# Purpose: cache module
# Created: 29.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .xmlns import wrap as uncached_wrap

class _WrapCache(object):
    # Should only used for big expensive objects like tables.
    _cache = {}

    def wrap(self, element):
        key = id(element)
        try:
            return self._cache[key]
        except KeyError:
            wrapped_object = uncached_wrap(element)
        self.add(wrapped_object)
        return wrapped_object

    def add(self, wrapped_object):
        self._cache[id(wrapped_object.xmlnode)] = wrapped_object

    def remove(self, wrapped_object):
        del self._cache[id(wrapped_object.xmlnode)]

    def clear(self):
        self._cache.clear()

_wrapcache = _WrapCache()
wrap = _wrapcache.wrap
clear = _wrapcache.clear
add = _wrapcache.add
remove = _wrapcache.remove
