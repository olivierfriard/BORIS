#!/usr/bin/env python
#coding:utf-8
# Purpose: const.py
# Created: 28.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

import sys

VERSION = "0.1.0"
GENERATOR = "http://pypi.python.org/pypi/ezodf/%s$Python%s" % (VERSION, sys.version)

MIMETYPES = {
    'odt': "application/vnd.oasis.opendocument.text",
    'ott': "application/vnd.oasis.opendocument.text-template",
    'odg': "application/vnd.oasis.opendocument.graphics",
    'otg': "application/vnd.oasis.opendocument.graphics-template",
    'odp': "application/vnd.oasis.opendocument.presentation",
    'otp': "application/vnd.oasis.opendocument.presentation-template",
    'ods': "application/vnd.oasis.opendocument.spreadsheet",
    'ots': "application/vnd.oasis.opendocument.spreadsheet-template",
    'odc': "application/vnd.oasis.opendocument.chart",
    'otc': "application/vnd.oasis.opendocument.chart-template",
    'odi': "application/vnd.oasis.opendocument.image",
    'oti': "application/vnd.oasis.opendocument.image-template",
    'odf': "application/vnd.oasis.opendocument.formula",
    'otf': "application/vnd.oasis.opendocument.formula-template",
    'odm': "application/vnd.oasis.opendocument.text-master",
    'oth': "application/vnd.oasis.opendocument.text-web",
}

FILE_EXT_FOR_MIMETYPE = dict([(mimetype, ext) for ext, mimetype in MIMETYPES.items()])

ANIM_NS = "urn:oasis:names:tc:opendocument:xmlns:animation:1.0"
DB_NS = "urn:oasis:names:tc:opendocument:xmlns:database:1.0"
CHART_NS = "urn:oasis:names:tc:opendocument:xmlns:chart:1.0"
CONFIG_NS = "urn:oasis:names:tc:opendocument:xmlns:config:1.0"
CSS3T_NS = "http://www.w3.org/TR/css3-text/"
DC_NS = "http://purl.org/dc/elements/1.1/"
DOM_NS = "http://www.w3.org/2001/xml-events"
DR3D_NS = "urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0"
DRAW_NS = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
DRAWOOO_NS = "http://openoffice.org/2010/draw"
FIELD_NS = "urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0"
FO_NS = "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
FORM_NS = "urn:oasis:names:tc:opendocument:xmlns:form:1.0"
FORMX_NS = "urn:openoffice:names:experimental:ooxml-odf-interop:xmlns:form:1.0"
GRDDL_NS = "http://www.w3.org/2003/g/data-view#"
KOFFICE_NS = "http://www.koffice.org/2005/"
MANIFEST_NS = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
MATH_NS = "http://www.w3.org/1998/Math/MathML"
META_NS = "urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
NUMBERS_NS = "urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
OFFICEOOO_NS = "http://openoffice.org/2009/office"
OF_NS = "urn:oasis:names:tc:opendocument:xmlns:of:1.2"
OOO_NS = "http://openoffice.org/2004/office"
OOOW_NS = "http://openoffice.org/2004/writer"
OOOC_NS = "http://openoffice.org/2004/calc"
PRESENTATION_NS = "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0"
RDFA_NS = "http://docs.oasis-open.org/opendocument/meta/rdfa#"
RPT_NS = "http://openoffice.org/2005/report"
SCRIPT_NS = "urn:oasis:names:tc:opendocument:xmlns:script:1.0"
SMIL_NS = "urn:oasis:names:tc:opendocument:xmlns:smil-compatible:1.0"
STYLE_NS = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
SVG_NS = "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
TABLEOOO_NS = "http://openoffice.org/2009/table"
TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
XFORMS_NS = "http://www.w3.org/2002/xforms"
XHTML_NS = "http://www.w3.org/1999/xhtml"
XLINKS_NS = "http://www.w3.org/1999/xlink"
XML_NS = "http://www.w3.org/XML/1998/namespace"
XSD_NS = "http://www.w3.org/2001/XMLSchema"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

META_NSMAP = {
    'office': OFFICE_NS,
    'xlink': XLINKS_NS,
    'dc': DC_NS,
    'meta': META_NS,
    'ooo': OOO_NS,
    'grddl': GRDDL_NS,
}

MANIFEST_NSMAP = {
    'manifest': MANIFEST_NS,
}

STYLES_NSMAP = {
    'style': STYLE_NS,
    'text': TEXT_NS,
    'table': TABLE_NS,
    'draw': DRAW_NS,
    'fo': FO_NS,
    'xlink': XLINKS_NS,
    'dc': DC_NS,
    'meta': META_NS,
    'number': NUMBERS_NS,
    'svg': SVG_NS,
    'chart': CHART_NS,
    'dr3d': DR3D_NS,
    'math': MATH_NS,
    'form': FORM_NS,
    'script': SCRIPT_NS,
    'ooo': OOO_NS,
    'ooow': OOOW_NS,
    'oooc': OOOC_NS,
    'office': OFFICE_NS,
    'dom': DOM_NS,
    'rpt': RPT_NS,
    'of': OF_NS,
    'xhtml': XHTML_NS,
    'grddl': GRDDL_NS,
    'tableooo': TABLEOOO_NS,
    'css3t': CSS3T_NS,
}

SETTINGS_NSMAP = {
    'office': OFFICE_NS,
    'xlink': XLINKS_NS,
    'config': CONFIG_NS,
    'ooo': OOO_NS,
}

TEXT_NSMAP = {
    'office': OFFICE_NS,
    'style': STYLE_NS,
    'text': TEXT_NS,
    'table': TABLE_NS,
    'draw': DRAW_NS,
    'fo': FO_NS,
    'xlink': XLINKS_NS,
    'dc': DC_NS,
    'meta': META_NS,
    'number': NUMBERS_NS,
    'presentation': PRESENTATION_NS,
    'svg': SVG_NS,
    'chart': CHART_NS,
    'dr3d': DR3D_NS,
    'math': MATH_NS,
    'form': FORM_NS,
    'script': SCRIPT_NS,
    'ooo': OOO_NS,
    'ooow': OOOW_NS,
    'oooc': OOOC_NS,
    'dom': DOM_NS,
    'xforms': XFORMS_NS,
    'xsd': XSD_NS,
    'xsi': XSI_NS,
    'rpt': RPT_NS,
    'of': OF_NS,
    'xhtml': XHTML_NS,
    'grddl': GRDDL_NS,
    'field': FIELD_NS,
    'formx': FORMX_NS,
    'tableooo': TABLEOOO_NS,
    'css3t': CSS3T_NS,
}

SPREADSHEET_NSMAP = {
    'presentation': PRESENTATION_NS,
}
SPREADSHEET_NSMAP.update(TEXT_NSMAP)

PRESENTATION_NSMAP = {
    'smil': SMIL_NS,
    'anim': ANIM_NS,
    'officeooo': OFFICEOOO_NS,
    'drawooo': DRAWOOO_NS,
}
PRESENTATION_NSMAP.update(SPREADSHEET_NSMAP)

GRAPHICS_NSMAP = PRESENTATION_NSMAP

ALL_NSMAP = {}
ALL_NSMAP.update(META_NSMAP)
ALL_NSMAP.update(MANIFEST_NSMAP)
ALL_NSMAP.update(STYLES_NSMAP)
ALL_NSMAP.update(SETTINGS_NSMAP)
ALL_NSMAP.update(TEXT_NSMAP)
ALL_NSMAP.update(SPREADSHEET_NSMAP)
ALL_NSMAP.update(PRESENTATION_NSMAP)
ALL_NSMAP.update(GRAPHICS_NSMAP)

MIMETYPE_NSMAP = {
    "application/vnd.oasis.opendocument.text" : TEXT_NSMAP,
    "application/vnd.oasis.opendocument.text-template" : TEXT_NSMAP,
    "application/vnd.oasis.opendocument.graphics" : GRAPHICS_NSMAP,
    "application/vnd.oasis.opendocument.graphics-template" : GRAPHICS_NSMAP,
    "application/vnd.oasis.opendocument.presentation" : PRESENTATION_NSMAP,
    "application/vnd.oasis.opendocument.presentation-template" : PRESENTATION_NSMAP,
    "application/vnd.oasis.opendocument.spreadsheet": SPREADSHEET_NSMAP,
    "application/vnd.oasis.opendocument.spreadsheet-template": SPREADSHEET_NSMAP,
    "application/vnd.oasis.opendocument.chart" : GRAPHICS_NSMAP,
    "application/vnd.oasis.opendocument.image" : GRAPHICS_NSMAP,
    "application/vnd.oasis.opendocument.formula" : GRAPHICS_NSMAP,
}

MIMETYPE_BODYTAG_MAP = {
    "application/vnd.oasis.opendocument.text" : "office:text",
    "application/vnd.oasis.opendocument.text-template" : "office:text",
    "application/vnd.oasis.opendocument.graphics" : "office:drawing",
    "application/vnd.oasis.opendocument.graphics-template" : "office:drawing",
    "application/vnd.oasis.opendocument.presentation" : "office:presentation",
    "application/vnd.oasis.opendocument.presentation-template" : "office:presentation",
    "application/vnd.oasis.opendocument.spreadsheet": "office:spreadsheet",
    "application/vnd.oasis.opendocument.spreadsheet-template": "office:spreadsheet",
    "application/vnd.oasis.opendocument.chart" : "office:chart",
    "application/vnd.oasis.opendocument.image" : "office:image",
}

DEFAULT_TABLE_EXPAND_STRATEGY = "all_less_maxcount"
DEFAULT_MAXCOUNT = (32, 32)
