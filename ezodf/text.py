#!/usr/bin/env python
#coding:utf-8
# Purpose: text objects
# Created: 03.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from.compatibility import is_string
from .xmlns import CN, register_class, subelement, wrap
from .base import GenericWrapper, safelen
from .whitespaces import encode_whitespaces
from .protection import random_protection_key
from .propertymixins import StringProperty, TextNumberingMixin, BooleanProperty
from .propertymixins import IntegerWithLowerLimitProperty


@register_class
class Span(GenericWrapper):
    TAG = CN('text:span')
    style_name = StringProperty(CN('text:style-name'))

    def __init__(self, text="", style_name="", xmlnode=None):
        super(Span, self).__init__(xmlnode)
        if xmlnode is None:
            if style_name:
                self.style_name = style_name
            if text:
                self.append_text(text)

    @property
    def textlen(self):
        # NOTE: do not cache this value before you can guarantee that
        # you detect ALL text changes in this node and all of it child nodes.
        length = safelen(self.xmlnode.text)
        for element in iter(self):
            length += (element.textlen + safelen(element.xmlnode.tail))
        return length

    def plaintext(self):
        # NOTE: do not cache this value before you can guarantee that
        # you detect ALL text changes in this node and all of it child nodes.
        text = [self.xmlnode.text]
        for element in iter(self):
            text.append(element.plaintext())
            text.append(element.xmlnode.tail)
        return "".join(filter(None, text))

    def append_text(self, text):
        def append(text, new):
            return text + new if text else new

        for tag in encode_whitespaces(text):
            if is_string(tag):
                if len(self.xmlnode) > 0:
                    lastchild = self[-1]
                    lastchild.tail = append(lastchild.tail, tag)
                else:
                    self.text = append(self.text, tag)
            else:
                self.append(tag)


@register_class
class Paragraph(Span):
    TAG = CN('text:p')
    cond_style_name = StringProperty(CN('text:cond-style-name'))
    ID = StringProperty(CN('text:id'))

@register_class
class NumberedParagraph(GenericWrapper, TextNumberingMixin):
    TAG = CN('text:numbered-paragraph')
    level = IntegerWithLowerLimitProperty(CN('text:level'), 1)

    def __init__(self, paragraph=None, xmlnode=None):
        super(NumberedParagraph, self).__init__(xmlnode)
        if xmlnode is None:
            if paragraph is not None:
                if isinstance(paragraph, GenericWrapper):
                    self.append(paragraph)
                else:
                    raise TypeError("Parameter 'paragraph' has to be a subclass of class 'GenericWrapper'")

    @property
    def content(self):
        p = self.xmlnode.find(CN('text:h'))
        if p is None:
            p = subelement(self.xmlnode, CN('text:p'))
        return wrap(p)

@register_class
class Heading(Span, TextNumberingMixin):
    TAG = CN('text:h')
    outline_level = IntegerWithLowerLimitProperty(CN('text:outline-level'), 1)
    restart_numbering = BooleanProperty(CN('text:restart-numbering'))
    suppress_numbering = BooleanProperty(CN('text:is-list-header'))

    def __init__(self, text="", outline_level=1, style_name="", xmlnode=None):
        super(Heading, self).__init__(text, style_name, xmlnode)
        if xmlnode is None:
            self.outline_level = outline_level

@register_class
class Hyperlink(Span):
    TAG = CN('text:a')
    name = StringProperty(CN('office:name'))
    href = StringProperty(CN('xlink:href'))

    def __init__(self, href="", text="", style_name="", xmlnode=None):
        super(Hyperlink, self).__init__(text, style_name, xmlnode)
        if xmlnode is None:
            if href: self.href = href
            self.target_frame = '_blank'

    @property
    def target_frame(self):
        return self.get_attr(CN('office:target-frame-name'))
    @target_frame.setter
    def target_frame(self, framename):
        self.set_attr(CN('office:target-frame-name'), framename)
        show = 'new' if framename == '_blank' else 'replace'
        self.set_attr(CN('xlink:show'), show)


@register_class
class ListHeader(GenericWrapper):
    TAG = CN('text:list-header')

    def __init__(self, text="", xmlnode=None):
        super(ListHeader, self).__init__(xmlnode)
        if xmlnode is None:
            if text:
                self.append(Paragraph(text))

    def plaintext(self):
        return '\n'.join([e.plaintext() for e in iter(self)])


@register_class
class ListItem(ListHeader, TextNumberingMixin):
    TAG = CN('text:list-item')


@register_class
class List(GenericWrapper):
    TAG = CN('text:list')
    style_name = StringProperty(CN('text:style-name'))
    continue_numbering = BooleanProperty(CN('text:continue-numbering'))

    def __init__(self, style_name="", xmlnode=None):
        super(List, self).__init__(xmlnode)
        if xmlnode is None:
            if style_name:
                self.style_name = style_name

    @property
    def header(self):
        h = self.xmlnode.find(CN('text:list-header'))
        return wrap(h) if h is not None else None
    @header.setter
    def header(self, header):
        if header.kind != 'ListHeader':
            raise TypeError("param 'header' is not a list header.")
        oldheader = self.xmlnode.find(CN('text:list-header'))
        if oldheader is not None:
            self.xmlnode.remove(oldheader)
        self.insert(0, header) # should be first child node

    def iteritems(self):
        return self.findall(CN('text:list-item'))


@register_class
class Section(GenericWrapper):
    TAG = CN('text:section')
    style_name = StringProperty(CN('text:style-name'))
    name = StringProperty(CN('text:name'))

    def __init__(self, name="", style_name="", xmlnode=None):
        super(Section, self).__init__(xmlnode)
        if xmlnode is None:
            if style_name:
                self.style_name = style_name
            if name:
                self.name = name

    @property
    def protected(self):
        return self.get_bool_attr(CN('text:protected'))
    @protected.setter
    def protected(self, value):
        self.set_bool_attr(CN('text:protected'), value)
        if self.protected:
            self.set_attr(CN('text:protection-key'), random_protection_key())
