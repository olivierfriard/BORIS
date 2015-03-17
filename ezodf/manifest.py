#!/usr/bin/env python
#coding:utf-8
# Purpose: ODF META-INF/manifest.xml management
# Created: 27.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .xmlns import XMLMixin, etree, CN
from .const import MANIFEST_NSMAP

IGNORE_LIST = frozenset(['META-INF/manifest.xml'])

class Manifest(XMLMixin):
    def __init__(self, content=None):
        if content is None:
            self.xmlnode = etree.Element(CN('manifest:manifest'), nsmap=MANIFEST_NSMAP)
        else:
            self.xmlnode = etree.XML(content)

    def add(self, full_path, media_type="", version=None):
        def create_new_file_entry():
            file_entry = etree.SubElement(self.xmlnode, CN('manifest:file-entry'))
            file_entry.set(CN('manifest:full-path'), full_path)
            return file_entry

        def get_file_entry_or_create_new():
            file_entry = self.find(full_path)
            return create_new_file_entry() if file_entry is None else file_entry

        def set_media_type_and_version(file_entry):
            file_entry.set(CN('manifest:media-type'), media_type)
            if version is not None:
                file_entry.set(CN('manifest:version'), version)

        if full_path in IGNORE_LIST:
            return
        file_entry = get_file_entry_or_create_new()
        set_media_type_and_version(file_entry)

    def remove(self, full_path):
        file_entry = self.find(full_path)
        if file_entry is not None:
            self.xmlnode.remove(file_entry)

    def find(self, full_path):
        for node in self.xmlnode:
            if node.get(CN('manifest:full-path')) == full_path:
                return node
        return None
