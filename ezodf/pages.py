#!/usr/bin/env python
#coding:utf-8
# Purpose: pages object
# Created: 12.12.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .xmlns import CN
from .pagecontainer import AbstractPageContainer

class Pages(AbstractPageContainer):
    def __init__(self, xmlbody):
        super(Pages, self).__init__(xmlbody, childtag=CN('draw:page'),
                                    nametag=CN('draw:name'))
