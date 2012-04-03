# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/mediapackage/repository
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.

import os
import thread
import tempfile
from shutil import rmtree
from xml.dom import minidom
from datetime import datetime

from galicaster.utils.mhhttpclient import MHHTTPClient
from galicaster.mediapackage import mediapackage
from galicaster.mediapackage import serializer
from galicaster.mediapackage import deserializer


class Repository(object):
    attach_dir = 'attach'

    def __init__(self, root=None, dispatcher=None):
        """
        FIXME doc

        param: root...
        """ 

        self.root = root 
        if not os.path.isdir(os.path.join(self.root, self.attach_dir)):
            os.mkdir(os.path.join(self.root, self.attach_dir))
            
        self.dispatcher = dispatcher
        # TODO create a folder structure via cof, not only one folder
        self.__list = dict()
        self.refresh()


    def refresh(self):
        self.__list.clear()
        if self.root != None:
            for folder in os.listdir(self.root):
                if folder == self.attach_dir:
                    continue
                manifest = os.path.join(self.root, folder, "manifest.xml")
                if os.path.exists(manifest):
                    novo = deserializer.fromXML(manifest)
                    self.__list[novo.getIdentifier()] = novo


    def list(self):
        return self.__list


    def list_by_status(self, status):
        def is_valid(mp):
            return mp.status == status

        next = filter(is_valid, self.__list.values())
        return next

    def size(self):
        return len(self.__list)

    def values(self):
        return self.__list.values()

    def items(self):
        return self.__list.items()

    def __iter__(self):
        return self.__list.__iter__()

    def __len__(self):
        return len(self.__list)

    def __contains__(self, v):
        return v in self.__list

    def __getitem__(self, k):
        return self.__list[k]

    def filter(self):
        # TODO filter by certain parameters
        return self.__list

    def get_next_mediapackages(self):
        """
        Return de next mediapackages to be record.
        """
        def is_future(mp):
            return mp.getDate() > datetime.utcnow()

        next = filter(is_future, self.__list.values())
        next = sorted(next, key=lambda mp: mp.startTime) 
        return next


    def get_next_mediapackage(self):
        """
        Retrive de next mediapackage to be record.
        """
        next = None
        for mp in self.__list.values():
            if mp.getDate() > datetime.utcnow():
                if next == None:
                    next = mp
                else:
                    if mp.getDate() < next.getDate():
                        next = mp

        return next


    def get(self, key):
        """Returns the Mediapackage identified by key"""
        return self.__list.get(key)


    def has(self, mp):
        return self.__list.has_key(mp.getIdentifier())


    def has_by_key(self, key):
        return self.__list.has_key(key)
    

    def add(self, mp):
        if self.has(mp):
            raise KeyError('Key Repeated')
        if mp.getURI() == None:
            mp.setURI(self.__get_folder_name())
        else:
            assert mp.getURI().startswith(self.root + os.sep)            
        os.mkdir(mp.getURI())

        return self.__add(mp)


    def add_after_rec(self, mp, bins, duration):
        if not self.has(mp):
            mp.setURI(self.__get_folder_name())
            os.mkdir(mp.getURI())

        for bin in bins:
            filename = bin['file']
            dest = os.path.join(mp.getURI(), os.path.basename(filename))
            os.rename(filename, dest)
            etype = 'audio/mp3' if bin['klass'] in ['pulse.GCpulse'] else 'video/' + dest.split('.')[1].lower()
            mp.add(dest, mediapackage.TYPE_TRACK, 
                   # FIXME move to restart preview
                   bin['options']['flavor'] + '/source', etype, duration) # FIXME MIMETYPE
        mp.forceDuration(duration)
        # ADD MP to repo
        self.__add(mp) 
        


    def delete(self, mp):
        if not self.has(mp):
            raise KeyError('Key not Exists')

        del self.__list[mp.getIdentifier()]
        rmtree(mp.getURI())
        return mp

        
    def update(self, mp):
        if not self.has(mp):
            raise KeyError('Key not Exists')
        #Si cambio URI error.
        return self.__add(mp)


    def import_from_zip(self, location):
        #TODO import from zip
        #TODO unzip file and put it on the repository
        return None

    def export_to_zip(self, mp, location):
        thread.start_new_thread(self._export_to_zip, (mp, location))
        return None

    def _export_to_zip(self, mp, location):
        serializer.save_in_zip(mp, location)
        return None
       
    def ingest(self, mp, server, user, password, workflow = 'full'):
        thread.start_new_thread(self._ingest, (mp, server, user, password, workflow))

    def _ingest(self, mp, server, user, password, workflow = 'full'):
        #FIXME New client in each ingest
        mp.status = mediapackage.INGESTING
        self.__add(mp) 
        client = MHHTTPClient(server, user, password)
        ifile = tempfile.NamedTemporaryFile()
        self._export_to_zip(mp, ifile)
        try:
            response = client.ingest(ifile.name, workflow)
            if response == 200:
                mp.status = mediapackage.INGESTED
            else:
                mp.status = mediapackage.INGEST_FAILED
        except:
            mp.status = mediapackage.INGEST_FAILED

        self.__add(mp) 
        if self.dispatcher:
            self.dispatcher.emit('refresh-row', mp.identifier)
        ifile.close()

    def ingest_pending(self, server, user, password, workflow = 'full'):
        thread.start_new_thread(self._ingest_pending, (server, user, password, workflow))

    def _ingest_pending(self, server, user, password, workflow = 'full'):
        mps = self.list_by_status(mediapackage.PENDING)
        for mp in mps:
            self._ingest(mp, server, user, password, workflow)
            

    def get_new_mediapackage(self, name=None, add_episode=True):
        folder = self.__get_folder_name(name)
        timestamp = None
        mp = mediapackage.Mediapackage(uri=folder, date=timestamp)
        if add_episode:
            mp.add(os.path.join(folder, 'episode.xml'), mediapackage.TYPE_CATALOG, 'dublincore/episode', 'text/xml')
        return mp


    def save_attach(self, name, data):
        m = open(os.path.join(self.root, self.attach_dir, name), 'w')  
        m.write(data)  
        m.close()
        
    def get_attach(self, name):
        return open(os.path.join(self.root, self.attach_dir, name))  

    def get_attach_path(self):
        return os.path.join(self.root, self.attach_dir)

    def __get_folder_name(self, name=None):
        if name == None:
            timestamp = datetime.now().replace(microsecond=0).isoformat()
            folder = os.path.join(self.root, "gc_" + timestamp)
        else:
            folder = os.path.join(self.root, "gc_" + name)
        
        return folder

    def __add(self, mp):
        self.__list[mp.getIdentifier()] = mp
        serializer.save_in_dir(mp)
        #FIXME escribir de nuevo los XML de metadata.xml y episode.xml y series.xml
        return mp
        
    



    
    
