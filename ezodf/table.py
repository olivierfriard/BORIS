#!/usr/bin/env python
#coding:utf-8
# Purpose: table objects
# Created: 03.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

import copy

from .compatibility import is_string
from .xmlns import register_class, CN, wrap, etree
from . import wrapcache
from .base import GenericWrapper
from .protection import random_protection_key
from .propertymixins import TableVisibilityMixin
from .propertymixins import StringProperty, BooleanProperty
from .tableutils import address_to_index, get_cell_index
from .tablerowcontroller import TableRowController
from .tablecolumncontroller import TableColumnController
from .cellspancontroller import CellSpanController

@register_class
class Table(GenericWrapper):
    TAG = CN('table:table')
    style_name = StringProperty(CN('table:style-name'))
    print_ = BooleanProperty(CN('table:print'))

    def __init__(self, name='NEWTABLE', size=(10, 10), xmlnode=None):
        def init_attributes_by_xmlnode():
            self._cellmatrix = TableRowController(self.xmlnode)
            self._columns_info = TableColumnController(self.xmlnode)
            self._cell_span_controller = CellSpanController(self._cellmatrix)

        def set_new_table_metrics():
            self.name = name
            self._cellmatrix.reset(size)
            self._columns_info.reset(size[1])

        super(Table, self).__init__(xmlnode=xmlnode)
        init_attributes_by_xmlnode()
        if xmlnode is None:
            set_new_table_metrics()
        wrapcache.add(self)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.get_child(key)
        else:
            return self.get_cell(get_cell_index(key))

    def __setitem__(self, key, cell):
        if isinstance(key, int):
            self.set_child(key, cell)
        else:
            self.set_cell(get_cell_index(key), cell)

    @property
    def name(self):
        return self.get_attr(CN('table:name'))
    @name.setter
    def name(self, value):
        return self.set_attr(CN('table:name'), self._normalize_sheet_name(value))

    @staticmethod
    def _normalize_sheet_name(name):
        for subst in "\t\r'\"":
            name = name.replace(subst, ' ')
        return name.strip()

    @property
    def protected(self):
        return self.get_bool_attr(CN('table:protected'))
    @protected.setter
    def protected(self, value):
        self.set_bool_attr(CN('table:protected'), value)
        if self.protected:
            self.set_attr(CN('table:protection-key'), random_protection_key())

    def nrows(self):
        """ Count of table rows. """
        return self._cellmatrix.nrows()

    def ncols(self):
        """ Count of table columns. """
        return self._cellmatrix.ncols()

    def reset(self, size=(10, 10)):
        preserve_name = self.name
        super(Table, self).clear()

        self.name = preserve_name
        self._cellmatrix.reset(size)
        self._columns_info.reset(size[1])

    def clear(self):
        size = (self.nrows(), self.ncols())
        self.reset(size)

    def copy(self, newname=None):
        newtable = Table(xmlnode=copy.deepcopy(self.xmlnode))
        if newname is None:
            newname = 'CopyOf' + self.name
        newtable.name = newname
        return newtable

    def get_cell(self, pos):
        """ Get cell at position 'pos', where 'pos' is a tuple (row, column). """
        return wrap(self._cellmatrix.get_cell(pos))

    def set_cell(self, pos, cell):
        """ Set cell at position 'pos', where 'pos' is a tuple (row, column). """
        if not hasattr(cell, 'kind') or cell.kind != 'Cell':
            raise TypeError("invalid type of 'cell'.")
        self._cellmatrix.set_cell(pos, cell.xmlnode)

    def itercells(self):
        """ Iterate over all cells, returns tuples (pos, cell). """
        for irow, row in enumerate(self.rows()):
            for icol, cell in enumerate(row):
                yield ((irow, icol), cell)

    def row(self, index):
        if is_string(index):
            index, column = address_to_index(index)
        return [wrap(e) for e in self._cellmatrix.row(index)]

    def rows(self):
        for index in range(self.nrows()):
            yield self.row(index)

    def column(self, index):
        if is_string(index):
            row, index = address_to_index(index)
        return [wrap(e) for e in self._cellmatrix.column(index)]

    def columns(self):
        for index in range(self.ncols()):
            yield self.column(index)

    def row_info(self, index):
        if is_string(index):
            index, column = address_to_index(index)
        return wrap(self._cellmatrix.row(index))

    def column_info(self, index):
        if is_string(index):
            row, index = address_to_index(index)
        return wrap(self._columns_info.get_table_column(index))

    def append_rows(self, count=1):
        self._cellmatrix.append_rows(count)

    def insert_rows(self, index, count=1):
        # CAUTION: this will break refernces in formulas!
        self._cellmatrix.insert_rows(index, count)

    def delete_rows(self, index, count=1):
        # CAUTION: this will break refernces in formulas!
        self._cellmatrix.delete_rows(index, count)

    def append_columns(self, count=1):
        self._cellmatrix.append_columns(count)
        self._columns_info.append(count)

    def insert_columns(self, index, count=1):
        # CAUTION: this will break refernces in formulas!
        self._cellmatrix.insert_columns(index, count)
        self._columns_info.insert(index, count)

    def delete_columns(self, index, count=1):
        # CAUTION: this will break refernces in formulas!
        self._cellmatrix.delete_columns(index, count)
        self._columns_info.delete(index, count)

    def set_cell_span(self, pos, size):
        self._cell_span_controller.set_span(get_cell_index(pos), size)

    def remove_cell_span(self, pos):
        self._cell_span_controller.remove_span(get_cell_index(pos))

@register_class
class TableColumn(GenericWrapper, TableVisibilityMixin):
    TAG = CN('table:table-column')
    style_name = StringProperty(CN('table:style-name'))
    default_cell_style_name = StringProperty(CN('table:default-cell-style-name'))

@register_class
class TableRow(TableColumn):
    TAG = CN('table:table-row')

    def __init__(self, ncols=10, xmlnode=None):
        super(TableRow, self).__init__(xmlnode=xmlnode)
        if xmlnode is None:
            self._setup(ncols)

    def _setup(self, ncols):
        for col in range(ncols):
            self.xmlnode.append(etree.Element(CN('table:table-cell')))

