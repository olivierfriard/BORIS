#!/usr/bin/env python
#coding:utf-8
# Purpose: variables and user_fields objects
# Created: 10.10.2014
# Copyright (C) 2014, Shvein Anton
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "T0ha <t0hashvein@gmail.com>"

from .xmlns import register_class, CN, wrap
from .base import GenericWrapper
from .compatibility import itermap, tostr


class Variables(GenericWrapper):  # {{{1

    def __init__(self, xmlnode=None):  # {{{2
        """docstring for __init__"""
        super(Variables, self).__init__(xmlnode)
        self.variables = {}
        for v in self:
            self.variables[v.name] = v

    def __getitem__(self, index):  # {{{2
        if index in self.variables:
            return self.variables[index]
        else:
            return self.get_child(index)

    def __setitem__(self, index, value):  # {{{2
        if index in self.variables:
            self.variables[index].value = value
        else:
            return self.set_child(index, value)


@register_class
class SimpleVariables(Variables):  # {{{1
    """Simple variables dict-like container"""
    TAG = CN('text:variable-decls')


@register_class
class UserFields(Variables):  # {{{1
    TAG = CN('text:user-field-decls')


class Variable(GenericWrapper):  # {{{1

    def __init__(self, xmlnode=None):  # {{{2
        """docstring for __init__"""
        super(Variable, self).__init__(xmlnode)
        self.name = self.xmlnode.get(CN('text:name'))

    @property
    def instances(self):  # {{{2
        vs = self.get_xmlroot().findall(".//%s[@%s='%s']" %
                                                      (CN('text:variable-set'),
                                                       CN('text:name'),
                                                       self.name))
        vg = self.get_xmlroot().findall(".//%s[@%s='%s']" %
                                                      (CN('text:variable-get'),
                                                       CN('text:name'),
                                                       self.name))
        vi = self.get_xmlroot().findall(".//%s[@%s='%s']" %
                                                      (CN('text:variable-input'),
                                                       CN('text:name'),
                                                       self.name))
        return itermap(wrap, vs + vg + vi)

    @property
    def type(self):  # {{{2
        """Gets type of variable"""
        return self.get_attr(CN('office:value-type'), 'string')

    @type.setter
    def type(self, t):  # {{{2
        """Sets type of variable"""
        self.set_attr(CN('office:value-type'), tostr(t))
        for instance in self.instances:
            instance.type = t



@register_class
class SimpleVariable(Variable):  # {{{1
    TAG = CN('text:variable-decl')

    @property
    def value(self):  # {{{2
        """
        Get variable value
        FIXME: (it's assumed that all instances have the same value)
        """
        return list(self.instances)[0].value

    @value.setter
    def value(self, v):  # {{{2
        """
        Set variable value
        """
        vtype = type(v)

        for instance in self.instances:
            instance.value = v

        if vtype == bool:
            self.type = 'boolean'
        elif vtype == int or vtype == float:
            self.type = 'float'
        else:
            self.type = 'string'


@register_class
class UserField(Variable):  # {{{1
    TAG = CN('text:user-field-decl')

    @property
    def value(self):  # {{{2
        """
        Get user-field value
        FIXME: (it's assumed that all instances have the same value)
        """

        if self.type == 'boolean':
            return self.get_bool_attr(CN('office:boolean-value'))
        elif self.type == 'string':
            return self.get_attr(CN('office:string-value'))
        return float(self.get_attr(CN('office:value')))

    @value.setter
    def value(self, v):  # {{{2
        """
        Set user-field value
        """
        vtype = type(v)

        for instance in self.instances:
            instance.value = v

        if vtype == bool:
            self.type = 'boolean'
            self.set_bool_attr(CN('office:boolean-value'), v)
        elif vtype == int or vtype == float:
            self.set_attr(CN('office:value'), v)
            self.type = 'float'
        else:
            self.set_attr(CN('office:string-value'), v)
            self.type = 'string'


class SimpleVariableInstance(GenericWrapper):  # {{{1

    def __init__(self, xmlnode=None):  # {{{2
        super(SimpleVariableInstance, self).__init__(xmlnode)
        self.name = self.xmlnode.get(CN('text:name'))

    @property
    def value(self):  # {{{2
        """Gets instavce value"""
        if self.type == 'string':
            return self.text
        elif self.type == 'boolean':
            return self.text == 'true'
        elif self.type == 'float':
            return float(self.text)
        else:
            return self.text

    @value.setter
    def value(self, v):  # {{{2
        """Sets instavce value"""

        vtype = type(v)
        self.text = tostr(v)
        if vtype == bool:
            self.type = 'boolean'
        elif vtype == int or vtype == float:
            self.type = 'float'
        else:
            self.type = 'string'

    @property
    def type(self):  # {{{2
        """Gets type of variable"""
        return self.get_attr(CN('office:value-type'), 'string')

    @type.setter
    def type(self, t):  # {{{2
        """Sets type of variable"""
        self.set_attr(CN('office:value-type'), tostr(t))


@register_class
class SimpleVariableSet(SimpleVariableInstance):  # {{{1
    TAG = CN('text:variable-set')


@register_class
class SimpleVariableGet(SimpleVariableInstance):  # {{{1
    TAG = CN('text:variable-get')


@register_class
class SimpleVariableInput(SimpleVariableInstance):  # {{{1
    TAG = CN('text:variable-input')


class UserFieldInstance(GenericWrapper):  # {{{1

    def __init__(self, xmlnode=None):  # {{{2
        super(UserFieldInstance, self).__init__(xmlnode)
        self.name = self.xmlnode.get(CN('text:name'))

    @property
    def value(self):  # {{{2
        """Gets instavce value"""
        if self.type == 'string':
            return self.text
        elif self.type == 'boolean':
            return self.text == 'true'
        elif self.type == 'float':
            return float(self.text)
        else:
            return self.text

    @value.setter
    def value(self, v):  # {{{2
        """Sets instavce value"""

        vtype = type(v)
        self.text = tostr(v)
        if vtype == bool:
            self.type = 'boolean'
        elif vtype == int or vtype == float:
            self.type = 'float'
        else:
            self.type = 'string'

    @property
    def type(self):  # {{{2
        """Gets type of user-field"""
        return self.get_attr(CN('office:value-type'), 'string')

    @type.setter
    def type(self, t):  # {{{2
        """Sets type of user-field"""
        self.set_attr(CN('office:value-type'), tostr(t))


@register_class
class UserFieldSet(SimpleVariableInstance):  # {{{1
    TAG = CN('text:user-field-set')


@register_class
class UserFieldGet(SimpleVariableInstance):  # {{{1
    TAG = CN('text:user-field-get')


@register_class
class UserFieldInput(SimpleVariableInstance):  # {{{1
    TAG = CN('text:user-field-input')
