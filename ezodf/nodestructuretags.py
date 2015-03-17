#!/usr/bin/env python
#coding:utf-8
# Purpose: table const
# Created: 01.02.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

from .xmlns import CN

OFFICE_FORMS = [CN("office:forms")]

TABLE_TRACKED_CHANGES = [CN("table:tracked-changes")]

TEXT_DECL = [
    CN("text:variable-decls"),
    CN("text:sequence-decls"),
    CN("text:user-field-decls"),
    CN("text:dde-connection-decls"),
    CN("text:alphabetical-index-auto-mark-file"),
]

TABLE_DECL = [
    CN("table:calculation-settings"),
    CN("table:content-validations"),
    CN("table:label-ranges"),
]

SHAPE = [
    CN("draw:rect"),
    CN("draw:line"),
    CN("draw:polyline"),
    CN("draw:polygon"),
    CN("draw:regular-polygon"),
    CN("draw:path"),
    CN("draw:circle"),
    CN("draw:ellipse"),
    CN("draw:g"),
    CN("draw:page-thumbnail"),
    CN("draw:frame"),
    CN("draw:measure"),
    CN("draw:caption"),
    CN("draw:connector"),
    CN("draw:control"),
    CN("dr3d:scene"),
    CN("draw:custom-shape"),
]

CHANGE_MARKS = [
    CN("text:change"),
    CN("text:change-start"),
    CN("text:change-end"),
]

PAGE_SEQUENCE = [
    CN("text:page-sequence"),
    CN("draw:a"),
] + SHAPE

TABLE_FUNCTIONS = [
    CN("table:named-expressions"),
    CN("table:database-ranges"),
    CN("table:data-pilot-tables"),
    CN("table:consolidation"),
    CN("table:dde-links"),
]

TEXT_CONTENT_ELEMENTS = [
    CN("text:h"),
    CN("text:p"),
    CN("text:list"),
    CN("text:numbered-paragraph"),
    CN("table:table"),
    CN("draw:a"),
    CN("text:section"),
    CN("text:soft-page-break"),
    CN("text:table-of-content"),
    CN("text:illustration-index"),
    CN("text:table-index"),
    CN("text:object-index"),
    CN("text:user-index"),
    CN("text:alphabetical-index"),
    CN("text:bibliography"),
]

#<office:text>
TEXT_PRELUDE = OFFICE_FORMS + TABLE_TRACKED_CHANGES + TEXT_DECL + TABLE_DECL
TEXT_CONTENT_STREAM = TEXT_CONTENT_ELEMENTS + SHAPE + CHANGE_MARKS
TEXT_CONTENT_PAGED = PAGE_SEQUENCE
TEXT_EPILOGUE = TABLE_FUNCTIONS

TABLE_COLUMNS = [
    CN("table:table-column-group"),
    CN("table:table-columns"),
    CN("table:table-column"),
    CN("table:table-header-columns")
]

TABLE_ROWS = [
    CN("table:table-row-group"),
    CN("table:table-rows"),
    CN("table:table-row"),
    CN("table:table-header-rows"),
    CN("text:soft-page-break")
]

# <table:table>
TABLE_PRELUDE = [
    CN("table:table-source"),
    CN("office:dde-source"),
    CN("table:scenario"),
    CN("office:forms"),
    CN("table:shapes")]
TABLE_CONTENT = TABLE_COLUMNS + TABLE_ROWS


# <office:spreadsheet>
SPREADSHEET_PRELUDE = TABLE_TRACKED_CHANGES + TEXT_DECL + TABLE_DECL
SPREADSHEET_CONTENT = [CN("table:table"),]
SPREADSHEET_EPILOGUE = TABLE_FUNCTIONS
