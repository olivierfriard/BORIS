#!/usr/bin/env python
#coding:utf-8
# Purpose: table-row container
# Created: 02.02.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

import copy

from .xmlns import CN, etree
from .nodestructuretags import TABLE_COLUMNS, TABLE_PRELUDE
from .nodeorganizer import PreludeTagBlock
from .tableutils import is_table, RepetitionAttribute
from .conf import config

def new_empty_column():
    return etree.Element(CN('table:table-column'))

class _ExpandAll(object):
    def expand_element(self, count, xmlnode):
        while count > 1:
            clone = copy.deepcopy(xmlnode)
            xmlnode.addnext(clone)
            count -= 1

    def expand_column(self, xmlcolumn, maxcols):
        repeat = RepetitionAttribute(xmlcolumn)
        count = repeat.cols
        if count > 1:
            del repeat.cols
            self.expand_element(count, xmlcolumn)

    def expand_columns(self, xmlcolumns, maxcols):
        for xmlcolumn in xmlcolumns:
            self.expand_column(xmlcolumn, maxcols)

class _ExpandAllButLast(_ExpandAll):
    def do_not_expand_column(self, xmlcolumn):
        repeat = RepetitionAttribute(xmlcolumn)
        if repeat.cols > 1:
            del repeat.cols

    def expand_columns(self, xmlcolumns, maxcols):
        for xmlcolumn in xmlcolumns[:-1]:
            self.expand_column(xmlcolumn, maxcols)
        if len(xmlcolumns):
            self.do_not_expand_column(xmlcolumns[-1])

class _ExpandAllLessMaxCount(_ExpandAll):
    def expand_column(self, xmlcolumn, maxcols):
        repeat = RepetitionAttribute(xmlcolumn)
        count = repeat.cols
        if 1 < count < maxcols:
            del repeat.cols
            self.expand_element(count, xmlcolumn)
        elif count >= maxcols:
            del repeat.cols # column just appears only one time

expand_strategies = {
    'all': _ExpandAll(),
    'all_but_last': _ExpandAllButLast(),
    'all_less_maxcount': _ExpandAllLessMaxCount(),
    }

class TableColumnController(object):
    def __init__(self, xmlnode):
        if not is_table(xmlnode):
            raise ValueError('invalid xmlnode')
        self.xmlnode = xmlnode
        self._expand_repeated_content()
        self.update()

    def update(self):
        self._columns = self.xmlnode.findall('.//'+CN('table:table-column'))

    def reset(self, ncols):
        if ncols < 1:
            raise ValueError('ncols has to be >= 1.')
        self._remove_existing_columns()
        insert_position = PreludeTagBlock(self.xmlnode, TABLE_PRELUDE).insert_position_after()
        for _ in range(ncols):
            self.xmlnode.insert(insert_position, new_empty_column())
        self.update()

    def _remove_existing_columns(self):
        for child in self.xmlnode.getchildren():
            if child.tag in TABLE_COLUMNS:
                self.xmlnode.remove(child)

    def _expand_repeated_content(self):
        maxcols = config.table_expand_strategy.get_maxcols()
        expand = config.table_expand_strategy.get_strategy()
        try:
            strategy = expand_strategies[expand]
        except KeyError:
            raise TypeError("Unknown expand strategy: %s" % expand)
        strategy.expand_columns(self.xmlnode.findall('.//'+CN('table:table-column')), maxcols)

    def __len__(self):
        return len(self._columns)

    def __getitem__(self, pos):
        return self._columns[pos]

    def __setitem__(self, pos, element):
        self._check_column_type(element)
        oldcolumn = self._columns[pos]
        newcolumn = copy.deepcopy(element)
        oldcolumn.getparent().replace(oldcolumn, newcolumn)
        self._columns[pos] = newcolumn

    def _check_column_type(self, column):
        if column.tag != CN('table:table-column'):
            raise TypeError('element-tag is not <table:table-column>')

    def get_table_column(self, index):
        return self._columns[index]

    def is_consistent(self):
        # just for testing
        xmlcols = self.xmlnode.findall('.//'+CN('table:table-column'))
        if len(xmlcols) != len(self):
            return False
        for col1, col2 in zip(self._columns, xmlcols):
            if col1 != col2:
                return False
        return True

    def append(self, count=1):
        if count < 1:
            raise ValueError('count < 1')
        for _ in range(count):
            column = new_empty_column()
            self._columns[-1].addnext(column)
            self._columns.append(column)

    def insert(self, index, count=1):
        if count < 1:
            raise ValueError('count < 1')
        if index < 0:
            index += len(self)
        for _ in range(count):
            column = new_empty_column()
            insertpos = self._columns[index]
            insertpos.addprevious(column)
            self._columns.insert(index, column)

    def delete(self, index, count=1):
        if count < 1:
            raise ValueError('count < 1')
        if index < 0:
            index += len(self)
        for _ in range(count):
            column = self._columns[index]
            column.getparent().remove(column)
            del self._columns[index]
