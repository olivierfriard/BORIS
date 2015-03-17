#!/usr/bin/env python
# coding:utf-8
# Purpose: body
# Created: 11.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .xmlns import register_class, CN, wrap, subelement
from .base import GenericWrapper
from .sheets import Sheets
from .pages import Pages
from .nodeorganizer import EpilogueTagBlock
from .nodestructuretags import TEXT_EPILOGUE


class GenericBody(GenericWrapper):
    def __init__(self, xmlnode=None):
        super(GenericBody, self).__init__(xmlnode=xmlnode)
        self.variables = wrap(subelement(self.xmlnode,
                                                CN("text:variable-decls")))
        self.userfields = wrap(subelement(self.xmlnode,
                                                CN("text:user-field-decls")))


@register_class
class TextBody(GenericBody):
    TAG = CN('office:text')
    def __init__(self, xmlnode=None):
        super(TextBody, self).__init__(xmlnode=xmlnode)
        self._epilogue = EpilogueTagBlock(self.xmlnode, TEXT_EPILOGUE)

    def append(self, child):
        self.insert(self._epilogue.insert_position_before(), child)
        return child

@register_class
class SpreadsheetBody(GenericBody):
    TAG = CN('office:spreadsheet')
    def __init__(self, xmlnode=None):
        super(SpreadsheetBody, self).__init__(xmlnode=xmlnode)
        self.sheets = Sheets(self.xmlnode)

@register_class
class DrawingBody(GenericBody):
    TAG = CN('office:drawing')
    def __init__(self, xmlnode=None):
        super(DrawingBody, self).__init__(xmlnode=xmlnode)
        self.pages = Pages(self.xmlnode)

@register_class
class PresentationBody(DrawingBody):
    TAG = CN('office:presentation')

@register_class
class ChartBody(GenericBody):
    TAG = CN('office:chart')

@register_class
class ImageBody(GenericBody):
    TAG = CN('office:image')
