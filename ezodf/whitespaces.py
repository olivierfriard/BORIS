#!/usr/bin/env python
#coding:utf-8
# Purpose: whitespace processing
# Created: 06.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .compatibility import tostr
from .xmlns import register_class, CN
from .base import GenericWrapper

@register_class
class Tabulator(GenericWrapper):
    TAG = CN('text:tab')

    def __str__(self):
        return self.plaintext()

    @property
    def textlen(self):
        return 1

    def plaintext(self):
        return '\t'

@register_class
class LineBreak(Tabulator):
    TAG = CN('text:line-break')

    def plaintext(self):
        return '\n'

@register_class
class Spaces(Tabulator):
    TAG = CN('text:s')
    def __init__(self, count=1, xmlnode=None):
        super(Spaces, self).__init__(xmlnode)
        if xmlnode is None:
            self.count = count

    @property
    def count(self):
        count = self.get_attr(CN('text:c'))
        return int(count) if count is not None else 1
    @count.setter
    def count(self, value):
        if int(value) > 1:
            self.set_attr(CN('text:c'), tostr(value))

    @property
    def textlen(self):
        return self.count

    def plaintext(self):
        return ' ' * self.count

@register_class
class SoftPageBreak(Tabulator):
    TAG = CN('text:soft-page-break')
    @property
    def textlen(self):
        return 0

    def plaintext(self):
        return ''

class _WhitespaceEncoder(object):
    result = []
    stack = []
    space_counter = 0

    def encode(self, plaintext):
        self.result = []
        self.stack = []
        self.space_counter = 0
        for char in plaintext:
            if char == '\n':
                self.add_brk()
            elif char == '\t':
                self.add_tab()
            elif char == ' ':
                self.add_spc()
            else:
                self.add_char(char)
        if self.space_counter > 1:
            self.append_space()
        else:
            self.append_stack()
        return self.result

    @staticmethod
    def decode(taglist):
        return "".join( (tostr(tag) for tag in taglist) )

    def append_stack(self):
        if not self.stack:
            return
        txt = ''.join(self.stack)
        self.stack = []
        self.result.append(txt)

    def append_space(self):
        spaces = self.space_counter - 1
        # remove last spaces from stack
        self.stack = self.stack[: -spaces]
        self.append_stack()
        self.result.append(Spaces(spaces))
        self.space_counter = 0

    def add_brk(self):
        if self.space_counter > 1:
            self.append_space()
        else:
            self.append_stack()
        self.space_counter = 0
        self.result.append(LineBreak())

    def add_tab(self):
        if self.space_counter > 1:
            self.append_space()
        else:
            self.append_stack()
        self.space_counter = 0
        self.result.append(Tabulator())

    def add_spc(self):
        self.add_char(' ')
        self.space_counter += 1

    def add_char(self, char):
        if char != ' ':
            if self.space_counter > 1:
                self.append_space()
            else:
                self.space_counter = 0
        self.stack.append(char)

WhitespaceEncoder = _WhitespaceEncoder()

def encode_whitespaces(plaintext):
    return WhitespaceEncoder.encode(plaintext)

def decode_whitespaces(taglist):
    return WhitespaceEncoder.decode(taglist)
