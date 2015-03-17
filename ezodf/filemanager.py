#!/usr/bin/env python
#coding:utf-8
# Purpose: filemanager module
# Created: 31.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

import os
import zipfile
import io
import random
from datetime import datetime

from .xmlns import etree, CN
from .manifest import Manifest
from .compatibility import tobytes, bytes2unicode, is_bytes, is_zipfile

FNCHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

class FileObject(object):
    __slots__ = ['element', 'media_type', 'zipinfo']

    def __init__(self, name, element, media_type=""):
        self.element = element
        self.media_type = media_type
        now = datetime.now().timetuple()
        self.zipinfo = zipfile.ZipInfo(name, now[:6])
        self.zipinfo.compress_type = zipfile.ZIP_DEFLATED

    def tobytes(self):
        if hasattr(self.element, 'tobytes'):
            if self.media_type == 'text/xml':
                return self.element.tobytes(xml_declaration=True)
            else:
                return self.element.tobytes()
        else:
            return tobytes(self.element)

    @property
    def filename(self):
        return self.zipinfo.filename

class FileManager(object):
    def __init__(self, zipname=None):
        self.directory = dict()
        self.zipname = zipname
        self.manifest = Manifest(self.get_bytes('META-INF/manifest.xml'))
        self.register('META-INF/manifest.xml', self.manifest, 'text/xml')

    def has_zip(self):
        if self.zipname is not None:
            return is_zipfile(self.zipname)
        return False

    def _open_bytestream(self):
        return open(self.zipname, 'rb')

    def tmpfilename(self, basefile=None):
        def randomname(count):
            return ''.join(random.sample(FNCHARS, count))

        folder = "" if basefile is None else os.path.dirname(basefile)
        while True:
            filename = os.path.abspath(os.path.join(folder, randomname(8)+'.tmp'))
            if not os.path.exists(filename):
                return filename

    def register(self, name, element, media_type=""):
        self.directory[name] = FileObject(name, element, media_type)
        # 'mimetype' need not to be in the manifest.xml file, but it seems
        # not to break the vadility of the manifest file:
        # if name != 'mimetype:
        #     self.manifest.add(name, media_type)
        self.manifest.add(name, media_type)

    def save(self, filename, backup=True):
        # always create a new zipfile
        tmpfilename = self.tmpfilename(filename)
        zippo = zipfile.ZipFile(tmpfilename, 'w', zipfile.ZIP_DEFLATED)
        self._tozip(zippo)
        zippo.close()

        if os.path.exists(filename):
            if backup:
                # existing document becomes the backup file
                bakfilename = filename+'.bak'
                # remove existing backupfile
                if os.path.exists(bakfilename):
                    os.remove(bakfilename)
                os.rename(filename, bakfilename)
            else:
                # just remove the existing document
                os.remove(filename)

        # rename the new created document
        os.rename(tmpfilename, filename)
        self.zipname = filename

    def get_bytes(self, filename):
        """ Returns a byte stream or None. """
        filecontent = None
        if self.has_zip():
            bytestream = self._open_bytestream()
            zipfile_ = zipfile.ZipFile(bytestream, 'r')
            try:
                filecontent = zipfile_.read(filename)
            except KeyError:
                pass
            zipfile_.close()
            bytestream.close()
        return filecontent

    def get_text(self, filename, default=None):
        """ Retuns a str or 'default'. """
        filecontent = self.get_bytes(filename)
        if filecontent is not None:
            return bytes2unicode(filecontent)
        else:
            return default

    def get_xml_element(self, filename):
        filecontent = self.get_bytes(filename)
        if filecontent:
            return etree.XML(filecontent)
        else:
            return None

    def _tozip(self, zippo):
        # mimetype file should be the first & uncompressed file in zipfile
        mimetype = self.directory.pop('mimetype')
        mimetype.zipinfo.compress_type = zipfile.ZIP_STORED
        zippo.writestr(mimetype.zipinfo, mimetype.tobytes())
        processed = [mimetype.filename]

        for file in self.directory.values():
            zippo.writestr(file.zipinfo, file.tobytes())
            processed.append(file.filename)

        # push mimetype back to directory
        self.directory['mimetype'] = mimetype
        self._copy_zip_to(zippo, processed)

    def _copy_zip_to(self, newzip, ignore=[]):
        """ Copy all files like pictures and settings except the files in 'ignore'.
        """
        if not self.has_zip():
            return # nothing to copy
        try:
            bytestream = self._open_bytestream()
        except IOError:
            return # nothing to copy

        origzip = zipfile.ZipFile(bytestream)
        try:
            self._copy_from_zip_to_zip(origzip, newzip, ignore)
        finally:
            origzip.close()
            bytestream.close()

    @staticmethod
    def _copy_from_zip_to_zip(fromzip, tozip, ignore):
        for zipinfo in fromzip.filelist:
            if zipinfo.filename not in ignore:
                tozip.writestr(zipinfo, fromzip.read(zipinfo.filename))

    def tobytes(self):
        iobuffer = io.BytesIO()
        zippo = zipfile.ZipFile(iobuffer, 'w', zipfile.ZIP_DEFLATED)
        self._tozip(zippo)
        zippo.close()
        buffer = iobuffer.getvalue()
        del iobuffer
        return buffer

def check_zipfile_for_oasis_validity(filename, mimetype):
    """ Checks the zipfile structure and least necessary content, but not the
    XML validity of the document.
    """
    def check_manifest(stream):
        xmltree = etree.XML(stream)
        directory = dict([ (e.get(CN('manifest:full-path')), e) for e in xmltree.findall(CN('manifest:file-entry')) ])
        for name in ('content.xml', 'meta.xml', 'styles.xml', '/'):
            if name not in directory:
                return False
        if bytes2unicode(mimetype) != directory['/'].get(CN('manifest:media-type')):
            return False
        return True

    assert is_bytes(mimetype)
    if not is_zipfile(filename):
        return False
    # The first file in an OpenDocumentFormat zipfile should be the uncompressed
    # mimetype file, in a regular zipfile this file starts at byte position 30.
    # see also OASIS OpenDocument Specs. Chapter 17.4
    # LibreOffice ignore this requirement and opens all documents with
    # valid content (META-INF/manifest.xml, content.xml).
    with open(filename, 'rb') as f:
        buffer = f.read(38 + len(mimetype))
    if buffer[30:] != b'mimetype'+mimetype:
        return False
    zf = zipfile.ZipFile(filename)
    names = zf.namelist()
    if 'META-INF/manifest.xml' in names:
        manifest = zf.read('META-INF/manifest.xml')
    else:
        manifest = None
    zf.close()

    if manifest is None:
        return False
    # meta.xml and styles.xml are not required, but I think they should
    for filename in ['content.xml', 'meta.xml', 'styles.xml', 'mimetype']:
        if filename not in names:
            return False
    result = check_manifest(manifest)
    return result
