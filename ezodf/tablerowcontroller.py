#!/usr/bin/env python
#coding:utf-8
# Purpose: table-row container
# Created: 02.02.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .xmlns import CN, etree
from .nodestructuretags import TABLE_ROWS
from .tablenormalizer import normalize_table
from .tableutils import get_table_rows, new_empty_cell, is_table
from .conf import config

class TableCellAccessor(object):
    def __init__(self, xmlnode):
        if not is_table(xmlnode):
            raise ValueError('invalid xmlnode')
        self.xmlnode = xmlnode
        expand = config.table_expand_strategy.get_strategy()
        maxcount = config.table_expand_strategy.get_maxcount()
        normalize_table(xmlnode, expand, maxcount)
        self.update()

    def update(self):
        self._rows = get_table_rows(self.xmlnode)

    def nrows(self):
        return len(self._rows)

    def ncols(self):
        try:
            return len(self._rows[0])
        except IndexError:
            return 0

    def get_cell(self, pos):
        row, col = self._adjust_negative_indices(pos)
        return self._rows[row][col]

    def set_cell(self, pos, element):
        row, col = self._adjust_negative_indices(pos)
        self._rows[row][col] = element

    def _adjust_negative_indices(self, pos):
        row, col = pos
        if row < 0:
            row += self.nrows()
        if col < 0:
            col += self.ncols()
        return (row, col)

    def row(self, index):
        return self._rows[index]

    def column(self, index):
        return [row[index] for row in self._rows]

    def rows(self):
        return self._rows

class TableRowController(TableCellAccessor):
    def __init__(self, xmlnode):
        super(TableRowController, self).__init__(xmlnode)

    def reset(self, size):
        def validate_parameter(nrows, ncols):
            if nrows < 1:
                raise ValueError('nrows has to be >= 1.')
            if ncols < 1:
                raise ValueError('ncols has to be >= 1.')

        self._remove_existing_rows()
        nrows, ncols = size
        validate_parameter(nrows, ncols)
        self.xmlnode.extend( (self._build_new_row(ncols) for _ in range(nrows)) )
        self.update()

    @staticmethod
    def _build_new_row(ncols):
        row = etree.Element(CN('table:table-row'))
        row.extend( (new_empty_cell() for _ in range(ncols)) )
        return row

    def _remove_existing_rows(self):
        for child in self.xmlnode.getchildren():
            if child.tag in TABLE_ROWS:
                self.xmlnode.remove(child)

    def is_consistent(self):
        # just for testing
        xmlrows = get_table_rows(self.xmlnode)
        if len(xmlrows) != len(self._rows):
            return False
        for row1, row2 in zip(self._rows, xmlrows):
            if row1 != row2:
                return False
        return True

    def append_rows(self, count=1):
        if count < 1:
            raise ValueError('count < 1')
        for _ in range(count):
            newrow = self._build_new_row(self.ncols())
            last_row = self._rows[-1]
            last_row.addnext(newrow)
            self._rows.append(newrow)

    def insert_rows(self, index, count=1):
        if count < 1:
            raise ValueError('count < 1')
        for _ in range(count):
            newrow = self._build_new_row(self.ncols())
            insert_row = self._rows[index]
            insert_row.addprevious(newrow)
            self._rows.insert(index, newrow)

    def delete_rows(self, index, count=1):
        if count < 1 or count >= self.nrows():
            raise ValueError('invalid count')
        if index < 0:
            index += self.nrows()

        for _ in range(count):
            delete_row = self._rows.pop(index)
            delete_row.getparent().remove(delete_row)

    def append_columns(self, count=1):
        if count < 1:
            raise ValueError('count < 1')
        for row in self._rows:
            for _ in range(count):
                row.append(new_empty_cell())

    def insert_columns(self, index, count=1):
        if count < 1:
            raise ValueError('count < 1')
        if index < 0:
            index += self.ncols()

        for row in self._rows:
            for _ in range(count):
                row.insert(index, new_empty_cell())

    def delete_columns(self, index, count=1):
        if count < 1 or count >= self.ncols():
            raise ValueError('invalid count')
        if index < 0:
            index += self.ncols()

        for row in self._rows:
            for _ in range(count):
                del row[index]
