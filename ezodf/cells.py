#!/usr/bin/env python
#coding:utf-8
# Purpose: table cell objects
# Created: 03.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .xmlns import register_class, CN
from .base import GenericWrapper
from .text import Paragraph, Span
from .propertymixins import StringProperty, BooleanProperty
from .compatibility import tostr, is_string

VALID_VALUE_TYPES = frozenset( ('float', 'percentage', 'currency', 'date', 'time',
                                'boolean', 'string') )
NUMERIC_TYPES = frozenset( ('float', 'percentage', 'currency') )

TYPE_VALUE_MAP = {
    'string': CN('office:string-value'),
    'float': CN('office:value'),
    'percentage': CN('office:value'),
    'currency': CN('office:value'),
    'date': CN('office:date-value'),
    'time': CN('office:time-value'),
    'boolean': CN('office:boolean-value'),
}

# These Classes are supported to read their plaintext content from the
# cell-content.
SUPPORTED_CELL_CONTENT = ("Paragraph", "Heading")

@register_class
class Cell(GenericWrapper):
    CELL_ONLY_ATTRIBS = (CN('table:number-rows-spanned'),
                         CN('table:number-columns-spanned'),
                         CN('table:number-matrix-columns-spanned'),
                         CN('table:number-matrix-rows-spanned'))

    TAG = CN('table:table-cell')
    style_name = StringProperty(CN('table:style-name'))
    formula = StringProperty(CN('table:formula'))
    protected = BooleanProperty(CN('table:protect'))
    content_validation_name = StringProperty(CN('table:content-validation-name'))

    def __init__(self, value=None, value_type=None, currency=None, style_name=None, xmlnode=None):
        super(Cell, self).__init__(xmlnode=xmlnode)
        if xmlnode is None:
            if style_name is not None:
                self.style_name = style_name
            if value is not None:
                self.set_value(value, value_type, currency)
            elif value_type is not None:
                self._set_value_type(value_type)

    @property
    def value_type(self):
        return self.get_attr(CN('office:value-type'))

    @property
    def value(self):
        def convert(value, value_type):
            if value is None:
                pass
            elif value_type in NUMERIC_TYPES:
                value = float(value)
            elif value_type == 'boolean':
                value = True if value == 'true' else False
            return value

        t = self.value_type
        if  t is None:
            result = None
        elif t == 'string':
            result = self.plaintext()
        else:
            result = convert(self.xmlnode.get(TYPE_VALUE_MAP[t]), t)
        return result

    def set_value(self, value, value_type=None, currency=None):

        def is_valid_value(value):
            result = True
            if value is None:
                result = False
            elif isinstance(value, GenericWrapper):
                if value.kind not in SUPPORTED_CELL_CONTENT:
                    result = False
            return result

        def is_valid_type(value_type):
            return True if value_type in VALID_VALUE_TYPES else False

        def determine_value_type(value):
            if type(value) == bool:
                value_type = 'boolean'
            elif isinstance(value, (float, int)):
                value_type = 'float'
            else:
                value_type = 'string'
            return value_type

        def convert(value, value_type):
            if isinstance(value, GenericWrapper):
                pass
            elif value_type == 'string':
                value = Paragraph(tostr(value))
            elif value_type == 'boolean':
                value = 'true' if value else 'false'
            else:
                value = tostr(value)
            return value

        if not is_valid_value(value):
            raise ValueError("invalid value: %s" % tostr(value))
        if is_string(currency):
            value_type = 'currency'
        if value_type is None:
            value_type = determine_value_type(value)
        if not is_valid_type(value_type):
            raise TypeError(value_type)

        value = convert(value, value_type)
        self._clear_old_value()
        self._set_new_value(value, value_type, currency)

    def _set_new_value(self, value, value_type, currency):
        if isinstance(value, GenericWrapper):
            value_type = 'string'
            self.append(value)
        else:
            self.set_attr(TYPE_VALUE_MAP[value_type], value)
        self._set_value_type(value_type)

        if currency and (value_type == 'currency'):
            self.set_attr(CN('office:currency'), currency)

    def _set_value_type(self, value_type):
        self.set_attr(CN('office:value-type'), value_type)

    def _clear_old_value(self):
        self._clear_value_attribute(self.value_type)
        self._clear_content()

    def _clear_content(self):
        xmlnode = self.xmlnode
        for _ in range(len(xmlnode)):
            del xmlnode[0]

    def _clear_value_attribute(self, value_type):
        try:
            attribute_name = TYPE_VALUE_MAP[value_type]
            del self.xmlnode.attrib[attribute_name]
        except KeyError:
            pass

    @property
    def display_form(self):
        return self.plaintext()
    @display_form.setter
    def display_form(self, text):
        t = self.value_type
        if t is None or t == 'string':
            raise TypeError("not supported for value type 'None' and  'string'")
        display_form = Paragraph(text)
        first_paragraph = self.find(Paragraph.TAG)
        if first_paragraph is None:
            self.append(display_form)
        else:
            self.replace(first_paragraph, display_form)

    def plaintext(self):
        return "\n".join([p.plaintext() for p in iter(self)
                          if p.kind in SUPPORTED_CELL_CONTENT])

    def append_text(self, text, style_name=None):
        if self.value_type != 'string':
            raise TypeError('invalid cell type: %s' % self.value_type)
        try:
            last_child = self.get_child(-1)
            if last_child.kind in ("Paragraph", "Heading"):
                last_child.append(Span(text, style_name=style_name))
                return
        except IndexError:
            pass
        self.append(Paragraph(text, style_name=style_name))

    @property
    def currency(self):
        return self.xmlnode.get(CN('office:currency'))

    @property
    def span(self):
        rows = self.xmlnode.get(CN('table:number-rows-spanned'))
        cols = self.xmlnode.get(CN('table:number-columns-spanned'))
        rows = 1 if rows is None else max(1, int(rows))
        cols = 1 if cols is None else max(1, int(cols))
        return (rows, cols)

    def _set_span(self, value):
        rows, cols = value
        rows = max(1, int(rows))
        cols = max(1, int(cols))
        if rows == 1 and cols == 1:
            self._del_span_attributes()
        else:
            self._set_span_attributes(rows, cols)

    def _del_span_attributes(self):
        del self.xmlnode.attrib[CN('table:number-rows-spanned')]
        del self.xmlnode.attrib[CN('table:number-columns-spanned')]

    def _set_span_attributes(self, rows, cols):
        self.xmlnode.set(CN('table:number-rows-spanned'), tostr(rows))
        self.xmlnode.set(CN('table:number-columns-spanned'), tostr(cols))

    @property
    def covered(self):
        return self.xmlnode.tag == CN('table:covered-table-cell')

    def _set_covered(self, value):
        if value:
            self.TAG = CN('table:covered-table-cell')
            self.xmlnode.tag = self.TAG
            self._remove_exclusive_cell_attributes()
        else:
            self.TAG = CN('table:table-cell')
            self.xmlnode.tag = self.TAG

    def _remove_exclusive_cell_attributes(self):
        for key in self.CELL_ONLY_ATTRIBS:
            if key in self.xmlnode.attrib:
                del self.xmlnode.attrib[key]

@register_class
class CoveredCell(Cell):
    TAG = CN('table:covered-table-cell')

    @property
    def kind(self):
        return 'Cell'
