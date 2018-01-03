#!/usr/bin/python
#
# Simple Flickr image/folder uploader
# Author: Gustavo Iniguez Goia - https://github.com/gustavo-iniguez-goya/flickr-uploader
# Inspired in https://github.com/alfem/synology-flickr-folder-uploader ->
# https://github.com/sybrenstuvel/flickrapi and https://github.com/jamesmstone/flickr-uploadr

# Documentation: https://stuvel.eu/flickrapi-doc/index.html
# Flickr API: https://www.flickr.com/services/api/

import flickrapi
import os
import sys
import argparse
import json
import re

# Get an api key and an api secret: https://www.flickr.com/services/apps/create/apply

class FlickrUploader():
    USER_ID     = ""
    API_KEY     = ""
    API_SECRET  = ""
    flickr      = None

    ALBUMS_NAME         = []
    TAGS                = ""
    ALBUM_DESCRIPTION   = ""
    PHOTO_TITLE         = None
    PHOTO_DESCRIPTION   = ""
    ALLOWED_EXTENSIONS  = ['png', 'jpeg', 'jpg', 'avi', 'mp4', 'gif', 'tiff',
            'mov', 'wmv', 'ogv', 'mpg', 'mp2', 'mpeg', 'mpe', 'mpv']
    PHOTOS_LAT          = None
    PHOTOS_LON          = None
    PHOTOS_CONTEXT      = "2" # 0 outdoors, 1 indoors
    PHOTOS_PRIVACY      = "1" # 0 private, 1 public
    # 0 - all rights reserved
    # 1 - non comm, share alike
    # 2 - attr-non comm
    # 3 - no comm, no derivs, alike
    # 4 - attr
    # 5 - attr-alike
    # 6 - attr-no derivs
    # 7 -
    # 8 -
    # 9 - pub domain ded CC0
    # 10 - pub domain
    PHOTOS_LICENSE      = "10"
    DELETE_AFTER_UPLOAD = False
    IGNORE_PATTERN      = None


    def __init__(self):
        self.flickr = flickrapi.FlickrAPI(self.API_KEY, self.API_SECRET)
        if self.USER_ID == "" or self.API_KEY == "" or self.API_SECRET == "":
            raise Exception,"\n[!!] You must get an API KEY before upload images to Flickr with this script.\nGo to https://www.flickr.com/services/apps/create/apply and get one.\n"


    def authenticate(self):
        try:
            if self.flickr == None or not self.flickr.token_valid(perms='write'):
                print "[!!] Authentication required. Copy and paste this url in your browser:"

                # Get request token
                self.flickr.get_request_token(oauth_callback='oob')

                # Show url. Copy and paste it in your browser
                authorize_url = self.flickr.auth_url(perms=u'write')
                print(authorize_url)

                # Prompt for verifier code from the user
                verifier = unicode(raw_input('Verifier code: '))

                print "[+] Verifier:", verifier

                # Trade the request token for an access token
                print("OK:",self.flickr.get_access_token(verifier))
        except flickrapi.FlickrError,e:
            raise Exception, str(e)

    def create_album(self, _name=ALBUMS_NAME, _description=ALBUM_DESCRIPTION, _cover_photo_id=None):
        try:
            if _cover_photo_id == None:
                print "We need the cover photo id"
                return

            print "[i] Creating new PHOTOSET: %s" % _name
            resp = self.flickr.photosets.create(title=_name, primary_photo_id=_cover_photo_id, description=_description)
            album_id = resp.findall('photoset')[0].attrib['id']
            print "[+] OK. album id = " + album_id
            return album_id
        except Exception,e:
            print "[-] ERROR creating album: %s" % str(e)
            return None

    def get_album_id(self, _name):
        """
        https://www.flickr.com/services/api/flickr.photosets.getList.html
        """
        try:
            raw_sets = self.flickr.photosets.getList(user_id=self.USER_ID)
            for photosets in raw_sets:
                for pset in photosets:
                    if pset.find('title').text == _name:
                        print "Reusing SET ID %s" % str(pset.attrib['id'])
                        return pset.attrib['id']

        except flickrapi.FlickrError,e:
            print "[-] get_album_id() exception:", str(e)

        return None

    def add_photos_to_album(self, _photos_ids, _albums_name=None):
        """
        Add photos to an album. If the album does not exist, it'll be created.

        :param _photos_ids - List of photos IDs already uploaded to Flickr.
        :param _album_name - The album name. If it's None, the name of the folder where the photo resides will be used.
        :returns: True|False
        """
        try:
            if _albums_name != None:
                self.ALBUMS_NAME = _albums_name

            for _album_name in self.ALBUMS_NAME:
                album_id = self.get_album_id(_album_name)
                if album_id == None:
                    album_id = self.create_album(_album_name, self.ALBUM_DESCRIPTION, _photos_ids[0])
                    if album_id == None:
                        print "[!] add_photos_to_album() error: Album not created"
                        return False

                print "[i] Adding photos to the album %s" % _album_name
                for photo_id in _photos_ids:
                    try:
                        print "[*] Adding photo to album %s with ID %s" % (album_id, photo_id)
                        resp = self.flickr.photosets.addPhoto(photoset_id=album_id, photo_id=photo_id)
                    except Exception,e:
                        print "\n[W] Warning adding file to album", photo_id
                        print "    Exception: %s" % str(e)

            return True
        except flickrapi.FlickrError,e:
            print "[-] add_photos_to_album() exception:", str(e)
            return False

    def upload_folder(self, _path):
        try:
            f = os.path.abspath(_path)+"/"
            if self.ALBUMS_NAME == "":
                self.ALBUMS_NAME = os.path.basename(os.path.normpath(_path))

            print "[+] Uploading folder: %s with name: %s" % (params.folder, self.ALBUMS_NAME)

            photo_ids = self.upload_files(os.listdir(f), _path)
            if photo_ids != None and len(photo_ids) > 0:
                self.add_photos_to_album(photo_ids)
        except Exception,e:
            print "[!] Exception uploading folder %s: %s" % (_path, str(e))

    def upload_files(self, _photos_list, _base_dir=""):
        """
        Upload files
        https://www.flickr.com/services/api/upload.api.html

        :param _photos_list: Array of path files to images.
        :param _base_dir: Base directory when uploading a folder (optional)
        :returns: Array of the IDs of the photos uploaded
        """
        photo_ids = []
        if len(_photos_list) == 0:
            print "0 photos to upload"
            return photo_ids

        print "[+] upload_files()", _photos_list
        for filename in _photos_list:
            filename = _base_dir + filename
            _title = os.path.basename(filename)
            if self.PHOTO_TITLE != None:
                _title = self.PHOTO_TITLE
            filename_split = filename.split('.')

            EXCLUDE_FILE=False
            if self.IGNORE_PATTERN != None:
                print "[i] Checking %s for IGNORE patterns" % filename
                for pattern in self.IGNORE_PATTERN:
                    if re.search(pattern, filename):
                        print "[i] Match found, excluding file %s with pattern %s" % (filename, pattern)
                        EXCLUDE_FILE=True
                        break

                if EXCLUDE_FILE != False:
                    continue

            print "[+] Uploading %s" % (filename)
            if len(filename_split) == 2:
                ext = filename_split[1].lower()
            else:
                ext = ''
            if ext in self.ALLOWED_EXTENSIONS:

                try:
                    uploadResp = self.flickr.upload(
                            filename=filename,
                            title=_title,
                            is_public=self.PHOTOS_PRIVACY,
                            is_friend=0,
                            is_family=1,
                            tags=self.TAGS,
                            description=self.PHOTO_DESCRIPTION)
                    photo_id = uploadResp.findall('photoid')[0].text
                    print "[+] %s OK. Flickr id = %s" % (filename, photo_id)
                    if self.PHOTOS_LAT != None and self.PHOTOS_LON != None:
                        ret = self.set_location(photo_id, self.PHOTOS_LAT, self.PHOTOS_LON, "11", self.PHOTOS_CONTEXT)
                        print "[i] GEO ret: " + str(ret)
                    ret = self.set_license(photo_id, self.PHOTOS_LICENSE)
                    print "[i] License ret: " + str(ret)
                    photo_ids.append(photo_id)

                    if self.DELETE_AFTER_UPLOAD == True:
                        self.delete_file(filename)
                except Exception, e:
                    print "\n[!] ERROR uploading file %s: %s" % (filename, str(e))
                    #if e.code == 4:
                    #    os.remove(full_filename)

        print "[+] Finish uploading %d photos" % len(photo_ids)
        return photo_ids

    def set_tags(self, _tags):
        self.TAGS = _tags

    def set_albums_name(self, _name):
        self.ALBUMS_NAME = _name.split(',')

    def set_album_description(self, _description):
        self.ALBUM_DESCRIPTION = _description

    def set_photo_title(self, _title):
        self.PHOTO_TITLE = _title

    def set_photo_description(self, _description):
        self.PHOTO_DESCRIPTION = _description

    def set_license(self, _photo_id, _license=PHOTOS_LICENSE):
        return self.flickr.photos.licenses.setLicense(photo_id=_photo_id, license_id=_license)

    def set_location(self, _photo_id, _lat, _lon, _accuracy, _context):
        return self.flickr.photos.geo.setLocation(photo_id=_photo_id, lat=_lat, lon=_lon, accuracy=_accuracy, context=_context)

    def set_delete_after_upload(self, _delete=False):
        """
        If set to True, the file will be deleted after being uploaded to Flickr
        """
        self.DELETE_AFTER_UPLOAD = _delete

    def set_photos_privacy(self, _privacy=PHOTOS_PRIVACY):
        self.PHOTOS_PRIVACY = _privacy

    def set_ignore_pattern(self, _pattern=[]):
        self.IGNORE_PATTERN = _pattern

    def delete_file(self, _path):
        print "[i] Deleting file %s" % _path
        os.remove(_path)




########################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-dir", "--folder", help="Path to the folder you want to upload")
    parser.add_argument("-f",   "--single-file", help="Upload a single file")
    parser.add_argument("-ft",  "--file-title", default="", help="sets file title")
    parser.add_argument("-fd",  "--file-description", default="", help="file description")
    parser.add_argument("-t",   "--tags", default="", help="One or more tags for all the files (use quotes if needed)")
    parser.add_argument("-n",   "--albums", help="Name of the albums to add photos to, separated by commas (,)")
    parser.add_argument("-ad",  "--album-description", default="", help="Album description")
    parser.add_argument("-df",  "--delete-after-upload", action="store_true", help="Delete each file after being uploaded")
    parser.add_argument("-ig",  "--ignore-pattern", help="Ignore files with these patterns, separated by commas (,). For example: \"hdr*,a*\"")
    parser.add_argument("-pf",  "--public-photos", default="0", help="public (1) or private (0) photos (default private)")
    params=parser.parse_args()

    if not params.folder and not params.single_file:
        print "  Usage: python flickr-uploader.py --single-file /path/to/img.jpg\n"
        sys.exit(1)

    fUploader = FlickrUploader()
    fUploader.authenticate()

    if params.ignore_pattern:
        print "Ignore pattern: %s" % params.ignore_pattern.split(',')
        fUploader.set_ignore_pattern(params.ignore_pattern.split(','))

    if params.public_photos:
        fUploader.set_photos_privacy(params.public_photos)

    if params.albums:
      fUploader.set_albums_name(params.albums)
    else:
      fUploader.set_albums_name(os.path.basename(os.path.normpath(os.path.dirname(params.single_file))))

    if params.album_description:
        fUploader.set_album_description(params.album_description)

    if params.file_title:
        fUploader.set_photo_title(params.file_title)

    if params.file_description:
        fUploader.set_photo_description(params.file_description)

    if params.delete_after_upload:
        fUploader.set_delete_after_upload(True)

    if params.tags:
      TAGS=params.tags
      fUploader.set_tags(params.tags)

    if params.folder:
        fUploader.upload_folder(params.folder)

    if params.single_file:
        print "[+] Uploading single file: %s" % params.single_file
        photo_ids = fUploader.upload_files([params.single_file])
        if photo_ids != None and len(photo_ids) > 0:
            fUploader.add_photos_to_album(photo_ids)
        else:
            print "[!] Failed uploading photos"
