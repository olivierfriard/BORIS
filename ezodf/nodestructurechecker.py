#!/usr/bin/env python
#coding:utf-8
# Purpose: node structure checker
# Created: 02.02.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .nodestructuretags import TEXT_PRELUDE, TEXT_CONTENT_STREAM, TEXT_CONTENT_PAGED, TEXT_EPILOGUE

from .nodeorganizer import PreludeTagBlock, EpilogueTagBlock

class NodeStructureChecker(object):
    """ Provides a method to check if an XMLNode has only children with tags
    defined in prelude_tags, midrange_tags, epilogue_tags.

    The Prelude/Epilogue range ends with the first occurrence of another tag
    as defined in prelude/epilogue_tags (order is significant), the rest is
    the midrange and should only contain tags from midrange_tags.
    """
    def __init__(self, prelude_tags, midrange_tags, epilogue_tags):
        self.prelude_tags = tuple(prelude_tags)
        self.midrange_tags = tuple(midrange_tags)
        self.epilogue_tags = tuple(epilogue_tags)

    def is_valid(self, xmlnode):
        def midrange(children):
            if epilogue_count:
                return children[prelude_count: -epilogue_count]
            else:
                return children[prelude_count:]

        prelude_count = len(PreludeTagBlock(xmlnode, self.prelude_tags))
        epilogue_count = len(EpilogueTagBlock(xmlnode, self.epilogue_tags))

        for element in midrange(xmlnode.getchildren()):
            if element.tag not in self.midrange_tags:
                return False
        return True

StreamTextBodyChecker = NodeStructureChecker(TEXT_PRELUDE, TEXT_CONTENT_STREAM, TEXT_EPILOGUE)
PagedTextBodyChecker = NodeStructureChecker(TEXT_PRELUDE, TEXT_CONTENT_PAGED, TEXT_EPILOGUE)
