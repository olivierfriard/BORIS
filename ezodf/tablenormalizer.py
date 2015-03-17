#!/usr/bin/env python
#coding:utf-8
# Purpose: table normalizer
# Created: 14.02.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

import copy

from .tableutils import new_empty_cell, get_table_rows, is_table
from .tableutils import get_min_max_cell_count, count_cells_in_row
from .tableutils import RepetitionAttribute
from . import const

class _ExpandAll:
    """ Expand all rows and columns, many repeated rows/cols blow up your ram """
    def __init__(self):
        self.set_maxcount(const.DEFAULT_MAXCOUNT)

    def set_maxcount(self, maxcount):
        self.maxrows = maxcount[0]
        self.maxcols = maxcount[1]

    def expand_element(self, xmlnode, count):
        while count > 1:
            clone = copy.deepcopy(xmlnode)
            xmlnode.addnext(clone)
            count -= 1

    def expand_cell(self, xmlcell):
        repeat = RepetitionAttribute(xmlcell)
        count = repeat.cols
        if count > 1:
            del repeat.cols
            self.expand_element(xmlcell, count)

    def expand_cells(self, xmlrow):
        for xmlcell in xmlrow:
            self.expand_cell(xmlcell)

    def expand_row(self, xmlrow):
        repeat = RepetitionAttribute(xmlrow)
        count = repeat.rows
        if count > 1:
            del repeat.rows
            self.expand_element(xmlrow, count)

    def normalize(self, xmlrows, maxcount):
        self.set_maxcount(maxcount)
        for xmlrow in xmlrows:
            self.expand_cells(xmlrow)
            self.expand_row(xmlrow)


class _ExpandAllButLast(_ExpandAll):
    """ Expand all but last row and column. """
    def expand_last_cell(self, xmlcell):
        repeat = RepetitionAttribute(xmlcell)
        if repeat.cols > 1:
            del repeat.cols

    def expand_last_row(self, xmlrow):
        repeat = RepetitionAttribute(xmlrow)
        if repeat.rows > 1:
            del repeat.rows

    def expand_cells(self, xmlrow):
        for xmlcell in xmlrow[:-1]: # do all cells except last one
            self.expand_cell(xmlcell)
        if len(xmlrow): # do last cell
            self.expand_last_cell(xmlrow[-1])

    def normalize(self, xmlrows, maxcount):
        # expand columns of all rows
        for xmlrow in xmlrows:
            self.expand_cells(xmlrow)

        for xmlrow in xmlrows[:-1]: # do all rows except last one
            self.expand_row(xmlrow)

        if len(xmlrows): # do last row
            self.expand_last_row(xmlrows[-1])

class _ExpandAllLessMaxCount(_ExpandAll):
    """ Expand all rows and columns with less than maxcount repetitions.

    Rows and cols with repetitions >= maxcount, occurs only once!
    """
    def expand_cell(self, xmlcell):
        repeat = RepetitionAttribute(xmlcell)
        count = repeat.cols
        if 1 < count < self.maxcols:
            del repeat.cols
            self.expand_element(xmlcell, count)
        elif count >= self.maxcols:
            del repeat.cols # column just appears only one time

    def expand_row(self, xmlrow):
        repeat = RepetitionAttribute(xmlrow)
        count = repeat.rows
        if 1 < count < self.maxrows:
            del repeat.rows
            self.expand_element(xmlrow, count)
        elif count >= self.maxrows:
            del repeat.rows # row just appears only one time

expand_strategies = {
    'all': _ExpandAll(),
    'all_but_last': _ExpandAllButLast(),
    'all_less_maxcount': _ExpandAllLessMaxCount(),
}

class TableNormalizer(object):
    def __init__(self, xmlnode):
        if not is_table(xmlnode):
            raise ValueError('invalid xmlnode')
        self.xmlnode = xmlnode

    def expand_repeated_table_content(self, expand, maxcount):
        """
        expand (strategy):
        'all': expand all rows and columns, many repeated rows/cols blow up your ram
        'all_but_last': expand all but last row and column
        'all_less_maxcount': expand all rows and columns with less than maxcount repetitions
            rows and cols with repetitions >= maxcount, occurs only once!

        """
        try:
            strategy = expand_strategies[expand]
        except KeyError:
            raise TypeError("Unknown expand strategy: %s" % expand)
        strategy.normalize(get_table_rows(self.xmlnode), maxcount)


    def align_table_columns(self):
        def append_cells(xmlrow, count):
            for _ in range(count):
                xmlrow.append(new_empty_cell())

        def _align_table_columns(required_cells_per_row):
            for xmlrow in get_table_rows(self.xmlnode):
                count = count_cells_in_row(xmlrow)
                if count < required_cells_per_row:
                    append_cells(xmlrow, required_cells_per_row - count)

        cmin, cmax = get_min_max_cell_count(self.xmlnode)
        if cmin != cmax:
            _align_table_columns(cmax)

def normalize_table(xmlnode, 
                    expand=const.DEFAULT_TABLE_EXPAND_STRATEGY, 
                    maxcount=const.DEFAULT_MAXCOUNT):
    normalizer = TableNormalizer(xmlnode)
    normalizer.expand_repeated_table_content(expand, maxcount)
    normalizer.align_table_columns()
