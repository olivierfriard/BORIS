#!/usr/bin/env python
#coding:utf-8
# Purpose: cell spanning controller
# Created: 13.02.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .xmlns import wrap
from .tableutils import iter_cell_range, iter_cell_range_without_start_pos


class CellSpanController(object):
    # is not a public class
    # public access only by Table or similar classes
    # all cell references has to be 2-tuples!
    def __init__(self, row_controller):
        self._row_controller = row_controller

    def _get_cell(self, pos):
        return wrap(self._row_controller.get_cell(pos))

    def is_cell_spanning(self, pos):
        return self._get_cell(pos).span != (1, 1)

    def set_span(self, pos, size):
        self._check_pos_and_size(pos, size)
        if self._has_cell_range_spanned_cells(pos, size):
            raise ValueError("cell range contains already spanned cells")
        for cell_index in iter_cell_range_without_start_pos(pos, size):
            self._cover_cell(cell_index)
        self._set_span_attributes(pos, size)

    def _check_pos_and_size(self, pos, size):
        start_row, start_column = pos
        if start_row < 0 or start_column < 0:
            raise IndexError("invalid start pos: %s" % tostr(pos))
        nrows, ncols = size
        if nrows < 1 or ncols < 1:
            raise ValueError("invalid size parameter: %s" % tostr(size))
        if start_row + nrows > self._row_controller.nrows() or \
           start_column + ncols > self._row_controller.ncols():
            raise ValueError("cell range exceeds table limits")

    def _has_cell_range_spanned_cells(self, pos, size):
        for cell_index in iter_cell_range(pos, size):
            if self.is_cell_spanning(cell_index):
                return True
        return False

    def _cover_cell(self, pos):
        cell = self._get_cell(pos)
        if not cell.covered:
            cell._set_covered(True)

    def _uncover_cell(self, pos):
        cell = self._get_cell(pos)
        if cell.covered:
            cell._set_covered(False)

    def _set_span_attributes(self, pos, size):
        cell = self._get_cell(pos)
        cell._set_span(size)
        self._uncover_cell(pos)

    def remove_span(self, pos):
        if not self.is_cell_spanning(pos):
            return # should it raise an error?
        size = self._get_cell(pos).span
        for cell_index in iter_cell_range(pos, size):
            self._uncover_cell(cell_index)
        self._remove_span_attributes(pos)

    def _remove_span_attributes(self, pos):
        cell = self._get_cell(pos)
        cell._del_span_attributes()
        self._uncover_cell(pos)

