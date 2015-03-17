#!/usr/bin/env python
#coding:utf-8
# Purpose: protection routines
# Created: 20.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

import random

FNCHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

def random_protection_key(count=12):
    return random.sample(FNCHARS, count)
