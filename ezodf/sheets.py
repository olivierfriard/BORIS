#!/usr/bin/env python
#coding:utf-8
# Purpose: sheets object
# Created: 29.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .xmlns import CN
from .pagecontainer import AbstractPageContainer

class Sheets(AbstractPageContainer):
    def __init__(self, xmlbody):
        super(Sheets, self).__init__(xmlbody, childtag=CN('table:table'),
                                     nametag=CN('table:name'))

