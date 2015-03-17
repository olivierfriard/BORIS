#!/usr/bin/env python
#coding:utf-8
# Purpose: ODF Document class
# Created: 27.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

import zipfile
import os

from io import BytesIO

from .compatibility import tostr, is_bytes, is_zipfile
from .const import MIMETYPES, MIMETYPE_BODYTAG_MAP, FILE_EXT_FOR_MIMETYPE
from .xmlns import subelement, CN, etree, wrap, ALL_NSMAP, fake_element
from .filemanager import FileManager
from .bytestreammanager import ByteStreamManager
from .meta import OfficeDocumentMeta
from .styles import OfficeDocumentStyles
from .content import OfficeDocumentContent
from . import observer

from . import body # not used, but important to register body classes

class InvalidFiletypeError(TypeError):
    pass

def is_valid_stream(buffer):
    if is_bytes(buffer):
        try:
            return is_zipfile(BytesIO(buffer))
        except TypeError:
            raise NotImplementedError("File like objects are not compatiable with zipfile in"
                                      "Python before 2.7 version")
    else:
        return False

def opendoc(filename):
    if is_zipfile(filename):
        fm = FileManager(filename)
    elif is_valid_stream(filename):
        fm = ByteStreamManager(filename)
    else:
        try:
            xmlnode = etree.parse(filename).getroot()
            return FlatXMLDocument(filename=filename, xmlnode=xmlnode)
        except etree.ParseError:
            raise IOError("File '%s' is neither a zip-package nor a flat "
                          "XML OpenDocumentFormat file." % filename)

    mime_type = __detect_mime_type(fm)
    return PackagedDocument(filemanager=fm, mimetype=mime_type)


def __detect_mime_type(file_manager):
    mime_type = file_manager.get_text('mimetype')
    if mime_type is not None:
        return mime_type
    # Fall-through to next mechanism
    entry = file_manager.manifest.find('/')
    if entry is not None:
        mime_type = entry.get(CN('manifest:media-type'))
    else:
        # use file ext name
        ext = os.path.splitext(file_manager.zipname)[1]
        mime_type = MIMETYPES[ext]
    return mime_type


def newdoc(doctype="odt", filename="", template=None):
    if template is None:
        mimetype = MIMETYPES[doctype]
        document = PackagedDocument(None, mimetype)
        document.docname = filename
    else:
        document = _new_doc_from_template(filename, template)
    return document


def _new_doc_from_template(filename, templatename):
    #TODO: only works with zip packaged documents
    def get_filemanager(buffer):
        if is_zipfile(buffer):
            return FileManager(buffer)
        elif is_valid_stream(buffer):
            return ByteStreamManager(buffer)
        else:
            raise IOError('File does not exist or it is not a zipfile: %s' % tostr(buffer))

    fm = get_filemanager(templatename)
    mimetype = fm.get_text('mimetype')
    if mimetype.endswith('-template'):
        mimetype = mimetype[:-9]
    try:
        document = PackagedDocument(filemanager=fm, mimetype=mimetype)
        document.docname = filename
        return document
    except KeyError:
        raise InvalidFiletypeError("Unsupported mimetype: %s".format(mimetype))


class _BaseDocument(object):
    """
    Broadcasting Events:
        broadcast(event='prepare_saving'): send before saving the document
        broadcast(event='post_saving'): send after saving the document
    """
    def __init__(self):
        self.backup = True

    def saveas(self, filename):
        self.docname = filename
        self.save()

    def save(self):
        if self.docname is None:
            raise IOError('No filename specified!')
        observer.broadcast('prepare_saving', root=self.body.get_xmlroot())
        self.meta.touch()
        self.meta.inc_editing_cycles()
        self._saving_routine()
        observer.broadcast('post_saving', root=self.body.get_xmlroot())

    @property
    def application_body_tag(self):
        return CN(MIMETYPE_BODYTAG_MAP[self.mimetype])

    def _create_shortcuts(self, body):
        if hasattr(body, 'sheets'):
            self.sheets = body.sheets
        if hasattr(body, 'pages'):
            self.pages = body.pages

    def inject_style(self, stylexmlstr, where="styles.xml"):
        style = fake_element(stylexmlstr)
        self.styles.styles.xmlnode.append(style.xmlnode)

class FlatXMLDocument(_BaseDocument):
    """ OpenDocument contained in a single XML file. """
    TAG = CN('office:document')

    def __init__(self, filetype='odt', filename=None, xmlnode=None):
        super(FlatXMLDocument, self).__init__()
        self.docname=filename
        self.mimetype = MIMETYPES[filetype]
        self.doctype = filetype

        if xmlnode is None: # new document
            self.xmlnode = etree.Element(self.TAG, nsmap=ALL_NSMAP)
        elif xmlnode.tag == self.TAG:
            self.xmlnode = xmlnode
            self.mimetype = xmlnode.get(CN('office:mimetype')) # required
        else:
            raise ValueError("Unexpected root tag: %s" % self.xmlnode.tag)

        if self.mimetype not in frozenset(MIMETYPES.values()):
            raise TypeError("Unsupported mimetype: %s" % self.mimetype)

        self._setup()
        self._create_shortcuts(self.body)


    def _setup(self):
        self.meta = OfficeDocumentMeta(subelement(self.xmlnode, CN('office:document-meta')))
        self.styles = wrap(subelement(self.xmlnode, CN('office:settings')))
        self.scripts = wrap(subelement(self.xmlnode, CN('office:scripts')))
        self.fonts = wrap(subelement(self.xmlnode, CN('office:font-face-decls')))
        self.styles = wrap(subelement(self.xmlnode, CN('office:styles')))
        self.automatic_styles = wrap(subelement(self.xmlnode, CN('office:automatic-styles')))
        self.master_styles = wrap(subelement(self.xmlnode, CN('office:master-styles')))
        self.body = self.get_application_body(self.application_body_tag)

    def get_application_body(self, bodytag):
        # The office:body element is just frame element for the real document content:
        # office:text, office:spreadsheet, office:presentation, office:drawing
        office_body = subelement(self.xmlnode, CN('office:body'))
        application_body = subelement(office_body, bodytag)
        return wrap(application_body)

    def _saving_routine(self):
        if os.path.exists(self.docname) and self.backup:
            self._backupfile(self.docname)
        self._writefile(self.docname)

    def _backupfile(self, filename):
        bakfilename = filename+'.bak'
        # remove existing backupfile
        if os.path.exists(bakfilename):
            os.remove(bakfilename)
        os.rename(filename, bakfilename)

    def _writefile(self, filename):
        with open(filename, 'wb') as fp:
            fp.write(self.tobytes())

    def tobytes(self):
        return etree.tostring(self.xmlnode,
                              xml_declaration=True,
                              encoding='UTF-8')

class PackagedDocument(_BaseDocument):
    """ OpenDocument as package in a zipfile.
    """
    def __init__(self, filemanager, mimetype):
        super(PackagedDocument, self).__init__()
        self.filemanager = fm = FileManager() if filemanager is None else filemanager
        self.docname = fm.zipname

        # add doctype to manifest
        self.filemanager.manifest.add('/', mimetype)

        self.mimetype = mimetype
        self.doctype = FILE_EXT_FOR_MIMETYPE[mimetype]
        fm.register('mimetype', self.mimetype)

        self.meta = OfficeDocumentMeta(fm.get_xml_element('meta.xml'))
        fm.register('meta.xml', self.meta, 'text/xml')

        self.styles = OfficeDocumentStyles(fm.get_xml_element('styles.xml'))
        fm.register('styles.xml', self.styles, 'text/xml')

        self.content = OfficeDocumentContent(mimetype, fm.get_xml_element('content.xml'))
        fm.register('content.xml', self.content, 'text/xml')

        self.body = self.content.get_application_body(self.application_body_tag)
        self._create_shortcuts(self.body)

    def _saving_routine(self):
        self.filemanager.save(self.docname, backup=self.backup)

    def tobytes(self):
        return self.filemanager.tobytes()
