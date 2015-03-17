#!/usr/bin/env python
#coding:utf-8
# Purpose: table utils
# Created: 13.02.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

import re
from .compatibility import tostr, is_string
from .xmlns import CN, etree

def iter_cell_range(pos, size):
    start_row, start_column = pos
    if (start_row < 0) or (start_column < 0):
        raise ValueError("invalid start pos: %s" % tostr(pos))
    nrows, ncolumns = size
    if (nrows < 1) or (ncolumns < 1):
        raise ValueError("invalid size: %s" % tostr(size))

    for row in range(start_row, start_row + nrows):
        for column in range(start_column, start_column + ncolumns):
            yield (row, column)

def iter_cell_range_without_start_pos(pos, size):
    generator = iter_cell_range(pos, size)
    next(generator)
    return generator

CELL_ADDRESS = re.compile('^([A-Z]+)(\d+)$')

def address_to_index(address):
    def column_name_to_index(colname):
        index = 0
        power = 1
        base = ord('A') - 1
        for char in reversed(colname):
            index += (ord(char) - base) * power
            power *= 26
        return index - 1

    res = CELL_ADDRESS.match(address.upper())
    if res:
        column_name, row_name = res.groups()
        return (int(row_name)-1, column_name_to_index(column_name))
    else:
        raise ValueError('Invalid cell address: %s' % address)

def get_cell_index(reference):
    if isinstance(reference, tuple): # key => (row, column)
        return reference
    elif is_string(reference): # key => 'A1'
        return address_to_index(reference)
    else:
        raise TypeError(tostr(type(key)))

def get_min_max_cell_count(xmltable):
    count = [count_cells_in_row(xmlrow) for xmlrow in get_table_rows(xmltable)]
    if len(count) > 0:
        return min(count), max(count)
    else:
        return (0, 0)

def get_table_rows(xmltable):
    return xmltable.findall('.//'+CN('table:table-row'))

def count_cells_in_row(xmlrow):
    return sum( (RepetitionAttribute(xmlcell).cols for xmlcell in xmlrow) )

def new_empty_cell():
    return etree.Element(CN('table:table-cell'))

def is_table(xmlnode):
    if (xmlnode is None) or (xmlnode.tag != CN('table:table')):
        return False
    else:
        return True

class RepetitionAttribute(object):
    def __init__(self, xmlnode):
        self.xmlnode = xmlnode

    @property
    def cols(self):
        count = self.xmlnode.get(CN('table:number-columns-repeated'))
        return 1 if count is None else int(count)

    @property
    def rows(self):
        count = self.xmlnode.get(CN('table:number-rows-repeated'))
        return 1 if count is None else int(count)

    @cols.deleter
    def cols(self):
        del self.xmlnode.attrib[CN('table:number-columns-repeated')]

    @rows.deleter
    def rows(self):
        del self.xmlnode.attrib[CN('table:number-rows-repeated')]
