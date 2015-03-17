#!/usr/bin/env python
#coding:utf-8
# Purpose: byte stream manager
# Created: 25.02.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

import io

from .filemanager import FileManager

class ByteStreamManager(FileManager):
    def __init__(self, buffer=None):
        self._zipfile_as_bytes = buffer
        super(ByteStreamManager, self).__init__()

    def save(self, filename, backup=False):
        with open(filename, 'wb') as fp:
            fp.write(self.tobytes())

    def has_zip(self):
        return self._zipfile_as_bytes is not None

    def _open_bytestream(self):
        return io.BytesIO(self._zipfile_as_bytes)
