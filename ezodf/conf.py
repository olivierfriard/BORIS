#!/usr/bin/env python
#coding:utf-8
# Purpose: global config
# Created: 06.06.2012
# Copyright (C) 2012, Manfred Moitzi
# License: MIT license

from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .const import DEFAULT_MAXCOUNT, DEFAULT_TABLE_EXPAND_STRATEGY

class TableExpandStrategyConfig(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.set_strategy(DEFAULT_TABLE_EXPAND_STRATEGY, DEFAULT_MAXCOUNT)

    def set_strategy(self, strategy, maxcount=DEFAULT_MAXCOUNT):
        self._strategy = strategy
        self._maxcount = maxcount

    def get_strategy(self):
        return self._strategy

    def get_maxcount(self):
        return self._maxcount

    def get_maxrows(self):
        return self._maxcount[0]

    def get_maxcols(self):
        return self._maxcount[1]
    
class Config(object):
    """ The global configuration class/object.
    """
    def __init__(self):
        self.table_expand_strategy = TableExpandStrategyConfig()

    def set_table_expand_strategy(self, strategy, maxcount=DEFAULT_MAXCOUNT):
        """ Set the global Spreadsheet/Table expand strategy for repeated rows
        and columns.

        :param str strategy: ``'all' | 'all_but_last' | 'all_less_maxcount'`` see :ref:`openods`
        :param 2-tuple maxcount: additional parameter for the strategy ``'all_less_maxcount'``;
          maxcount=(10, 20) means: expand all rows with a repetition parameter less 10 and
          expand all columns with a repetition parameter less 20, all rows/columns
          with greater repetition parameters were replaced by **one** row/column.

        """
        self.table_expand_strategy.set_strategy(strategy, maxcount)

    def reset_table_expand_strategy(self):
        """ Reset the global Spreadsheet/Table expand strategy for repeated rows
        and columns. Set *strategy* to ``'all_less_maxcount'`` and *maxcount* to ``(32, 32)``.

        """
        self.table_expand_strategy.reset()

# the real global configuration object
config = Config()
