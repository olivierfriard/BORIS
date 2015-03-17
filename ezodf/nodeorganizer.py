#!/usr/bin/env python
#coding:utf-8
# Purpose: node organizer
# Created: 31.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

class PreludeEpilogueOrganizer(object):
    """ Reorganizes children order of an XMLNode.

    Moves prelude-tags in front of the node and epilogue-tags to the end of the
    node. Prelude-tags and epilogue-tags are grouped together in the order of
    the constructor parameter 'prelude_tags' and 'epilogue-tags' but document
    order is preserved as possible.
    """
    def __init__(self, prelude_tags=[], epilogue_tags=[]):
        self.prelude_tags = prelude_tags
        self.epilogue_tags = epilogue_tags

    def reorder(self, xmlnode):
        def insert_prelude_nodes(nodes):
            for node in reversed(nodes):
                xmlnode.insert(0, node)

        def append_epilogue_nodes(nodes):
            xmlnode.extend(epilogue_nodes)

        if len(xmlnode) < 2:
            return
        prelude_nodes = self._extract_nodes(xmlnode, self.prelude_tags)
        epilogue_nodes = self._extract_nodes(xmlnode, self.epilogue_tags)
        insert_prelude_nodes(prelude_nodes)
        append_epilogue_nodes(epilogue_nodes)

    @staticmethod
    def _extract_nodes(xmlnode, tags):
        extracted_nodes = []
        for tag in tags:
            extracted_nodes.extend(xmlnode.findall(tag))
        PreludeEpilogueOrganizer._remove_children_from_node(xmlnode, extracted_nodes)
        return extracted_nodes

    @staticmethod
    def _remove_children_from_node(xmlnode, children):
        for child in children:
            xmlnode.remove(child)


class PreludeTagBlock(object):
    def __init__(self, xmlnode, tags):
        if xmlnode is None:
            raise ValueError('xmlnode is None')
        self.xmlnode = xmlnode
        self.tags = tuple(tags)
        if len(self.tags) == 0:
            raise ValueError('no block-tags specified.')
        if len(self.tags) != len(set(self.tags)):
            raise ValueError('duplicate tags are not allowed.')

    def __len__(self):
        return self._count_tags_in_block()

    def  _get_children(self):
        return self.xmlnode.getchildren()

    def _iter_children(self):
        return self.xmlnode.iterchildren()

    def _count_tags_in_block(self):
        if len(self.xmlnode) == 0 or len(self.tags) == 0:
            return 0

        counter = 0
        tags = self.tags
        for child in self._iter_children():
            if child.tag == tags[0]:
                counter += 1
            else:
                try:
                    tags = tags[tags.index(child.tag):]
                    counter += 1
                except ValueError: # not in list
                    break
        return counter

    def tag_info(self, tag):
        self._check_for_valid_tag(tag)

        def get_pos_and_count(tag, elements):
            last_pos = -1
            count = 0
            for pos, element in enumerate(elements):
                if element.tag == tag:
                    count += 1
                    last_pos = pos
            if count > 0:
                return (last_pos - count + 1, count)
            else:
                return (-1, 0)

        children = self._get_children()
        prelude_count = self._count_tags_in_block()
        return get_pos_and_count(tag, children[:prelude_count])

    def _check_for_valid_tag(self, tag):
        if tag not in self.tags:
            raise ValueError("invalid tag '%s'." % tag)

    def _get_tag_and_successors(self, tag):
        pos = self.tags.index(tag)
        return self.tags[pos:]

    def insert_position_before(self, tag):
        self._check_for_valid_tag(tag)

        for tag in self._get_tag_and_successors(tag):
            pos, count = self.tag_info(tag)
            if count > 0:
                return pos
        return 0

    def _successor_tag(self, tag):
        tagpos = self.tags.index(tag)
        return self.tags[tagpos + 1]

    def insert_position_after(self, tag=None):
        # if tag is None -> insert after all prelude-tags
        if tag is None:
            tag = self.tags[-1]
        self._check_for_valid_tag(tag)

        if tag == self.tags[-1]:
            return self._count_tags_in_block()
        else:
            return self.insert_position_before(self._successor_tag(tag))

class EpilogueTagBlock(PreludeTagBlock):
    def __init__(self, xmlnode, tags):
        super(EpilogueTagBlock, self).__init__(xmlnode, reversed(tags))

    def _get_children(self):
        return list(self._iter_children())

    def _iter_children(self):
        return self.xmlnode.iterchildren(reversed=True)

    def tag_info(self, tag):
        pos, count = super(EpilogueTagBlock, self).tag_info(tag)
        if count > 0:
            pos = len(self.xmlnode) - pos - count
        return (pos, count)

    def insert_position_before(self, tag=None):
        # if tag is None -> insert before all epiloge-tags
        if tag is None:
            tag = self.tags[-1]
        self._check_for_valid_tag(tag)

        if tag == self.tags[-1]:
            return len(self.xmlnode) - self._count_tags_in_block()
        else:
            return self.insert_position_after(self._successor_tag(tag))

    def insert_position_after(self, tag):
        self._check_for_valid_tag(tag)

        def tag_info(tag):
            return super(EpilogueTagBlock, self).tag_info(tag)

        for tag in self._get_tag_and_successors(tag):
            pos, count = tag_info(tag)
            if count > 0:
                return len(self.xmlnode) - pos
        return len(self.xmlnode)
