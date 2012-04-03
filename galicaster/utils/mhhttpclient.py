# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/utils/mhhttpclient
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.


import re
import json
import logging
import urllib
#FIXME Se puede usar cStringIO para mas rapido
from StringIO import StringIO
import pycurl

INIT_ENDPOINT = '/welcome.html'
ME_ENDPOINT = '/info/me.json'
SETRECORDINGSTATE_ENDPOINT = '/capture-admin/recordings/{id}'
SETSTATE_ENDPOINT = '/capture-admin/agents/{name}'
SETCONF_ENDPOINT = '/capture-admin/agents/{name}/configuration'
INGEST_ENDPOINT = '/ingest/addZippedMediaPackage'
ICAL_ENDPOINT = '/recordings/calendars?agentid={name}'
SERIES_ENDPOINT = '/series/series.json'

log = logging.getLogger()


#FIXME No me gusta este nombre
class MHHTTPClient():

    def __init__(self, server, user, password):
        self.server = server
        self.user = user
        self.password = password
        self.cookie = ''
        self.__login()

    def __login(self):
        c = pycurl.Curl()
        b = StringIO()
        c.setopt(pycurl.URL, self.server + INIT_ENDPOINT)
        c.setopt(pycurl.HEADER, True)  
        c.setopt(pycurl.FOLLOWLOCATION, False)
        c.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_DIGEST)
        c.setopt(pycurl.USERPWD, self.user + ':' + self.password)
        c.setopt(pycurl.HTTPHEADER, ['X-Requested-Auth: Digest'])
        
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.perform()
        status_code = c.getinfo(pycurl.HTTP_CODE)
        c.close() 
        if status_code != 200:
            #FIXME exception
            return None
        g = re.findall('Set-Cookie: (.*);Path=', b.getvalue())
        self.cookie = g[-1]
        #g = re.search('Set-Cookie: (.*);Path=', b.getvalue())
        #self.cookie = g.group(1)        
        log.info('login in {%r} OK', self.server)
        return self.cookie


    def whoami(self):
        c = pycurl.Curl()
        b = StringIO()
        c.setopt(pycurl.URL, self.server + ME_ENDPOINT)
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.COOKIE, self.cookie)
        c.perform()
        c.close() 
        #FIXME JSON to ARRAY??
        return json.loads(b.getvalue())

    def ical(self, name):
        c = pycurl.Curl()
        b = StringIO()
        c.setopt(pycurl.URL, self.server + ICAL_ENDPOINT.format(name = "GC-" + name))
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.COOKIE, self.cookie)
        c.perform()
        c.close() 
        return b.getvalue()


    #FIXME create self.name, self.conf, self.address y self.state
    def setstate(self, agent, address, state):
        c = pycurl.Curl()
        b = StringIO()
        c.setopt(pycurl.URL, self.server + SETSTATE_ENDPOINT.format(name = "GC-" + agent))
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.COOKIE, self.cookie)
        c.setopt(pycurl.POST, 1) 
        #c.setopt(pycurl.POSTFIELDS, "address=" + address + "&state=" + state) 
        c.setopt(pycurl.POSTFIELDS, urllib.urlencode({'address': address, 'state': state}))

        #c.setopt(pycurl.HEADER, True)  
        #c.setopt(pycurl.VERBOSE, True) 
        c.perform()
        c.close() 
        
        return b.getvalue()

    #FIXME create self.name, self.conf, self.address y self.state
    def setrecordingstate(self, recording_id, state):
        """
        Los posibles estados son: unknown, capturing, capture_finished, capture_error, manifest, 
        manifest_error, manifest_finished, compressing, compressing_error, uploading, upload_finished, upload_error
        """
        c = pycurl.Curl()
        b = StringIO()
        c.setopt(pycurl.URL, self.server + SETRECORDINGSTATE_ENDPOINT.format(id = recording_id))
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.COOKIE, self.cookie)
        c.setopt(pycurl.POST, 1) 
        c.setopt(pycurl.POSTFIELDS, urllib.urlencode({'state': state}))

        #c.setopt(pycurl.HEADER, True)  
        #c.setopt(pycurl.VERBOSE, True) 
        c.perform()
        c.close() 

        return b.getvalue()


    def setconfiguration(self, agent, address):
        #FIXME poner esto en otro sitio
        client_conf = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd"><properties version="1.0"><entry key="service.pid">galicaster</entry><entry key="capture.device.names">camera,screen,audio</entry><entry key="capture.device.camera.flavor">presenter/source</entry><entry key="capture.device.camera.outputfile">camera.mpg</entry><entry key="capture.device.camera.src">/dev/camera</entry><entry key="capture.device.screen.outputfile">screen.mpg</entry><entry key="capture.device.screen.flavor">presentation/source</entry><entry key="capture.device.screen.src">/dev/screen</entry><entry key="capture.device.audio.flavor">presenter/source</entry><entry key="capture.device.audio.src">hw:0</entry><entry key="capture.device.audio.outputfile">audio.mp3</entry><entry key="capture.confidence.debug">false</entry><entry key="capture.confidence.enable">false</entry><entry key="capture.confidence.video.location">/opt/matterhorn/storage/volatile/</entry><entry key="capture.config.remote.polling.interval">600</entry><entry key="capture.config.cache.url">/opt/matterhorn/storage/cache/capture.properties</entry><entry key="capture.agent.name">{name}</entry><entry key="capture.agent.state.remote.polling.interval">10</entry><entry key="capture.agent.capabilities.remote.polling.interval">10</entry><entry key="capture.agent.state.remote.endpoint.url">{server}/capture-admin/agents</entry><entry key="capture.recording.shutdown.timeout">60</entry><entry key="capture.recording.state.remote.endpoint.url">{server}/capture-admin/recordings</entry><entry key="capture.schedule.event.drop">false</entry><entry key="capture.schedule.remote.polling.interval">1</entry><entry key="capture.schedule.event.buffertime">1</entry><entry key="capture.schedule.remote.endpoint.url">{server}/recordings/calendars</entry><entry key="capture.schedule.cache.url">/opt/matterhorn/storage/cache/schedule.ics</entry><entry key="capture.ingest.retry.interval">300</entry><entry key="capture.ingest.retry.limit">5</entry><entry key="capture.ingest.pause.time">3600</entry><entry key="capture.cleaner.interval">3600</entry><entry key="capture.cleaner.maxarchivaldays">30</entry><entry key="capture.cleaner.mindiskspace">536870912</entry><entry key="capture.error.messagebody">&quot;Capture agent was not running, and was just started.&quot;</entry><entry key="capture.error.subject">&quot;%hostname capture agent started at %date&quot;</entry><entry key="org.opencastproject.server.url">http://172.20.209.88:8080</entry><entry key="org.opencastproject.capture.core.url">{server}</entry><entry key="capture.max.length">28800</entry></properties>"""

        c = pycurl.Curl()
        b = StringIO()
        c.setopt(pycurl.URL, self.server + SETCONF_ENDPOINT.format(name = "GC-" + agent))
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.COOKIE, self.cookie)
        c.setopt(pycurl.POST, 1) 
        #c.setopt(pycurl.POSTFIELDS, "configuration=" + conf) 
        c.setopt(pycurl.POSTFIELDS, urllib.urlencode(
                {'configuration': client_conf.format(name = "GC-" + agent, server = self.server)}))

        #c.setopt(pycurl.HEADER, True)  
        #c.setopt(pycurl.VERBOSE, True) 

        c.perform()
        c.close() 

        return b.getvalue()


    def ingest(self, mp_file, workflow = 'full', workflow_instance = None):
        c = pycurl.Curl()
        b = StringIO()
        c.setopt(pycurl.URL, self.server + INGEST_ENDPOINT)
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.COOKIE, self.cookie)
        #FIXME comprobar que el archivo existe.
        if workflow_instance != None:
            postdict = [ 
                ('workflowDefinitionId', workflow),
                ('workflowInstanceId', str(workflow_instance)),
                ('trimHold', 'true'),
                ('track',(pycurl.FORM_FILE, mp_file)),
                ] 
        else:
            postdict = [ 
                ('workflowDefinitionId', workflow),
                ('trimHold', 'true'),
                ('track',(pycurl.FORM_FILE, mp_file)),
                ] 

        c.setopt(pycurl.HTTPPOST, postdict) 
        #c.setopt(pycurl.VERBOSE, True) 
        c.perform()
        #Fixme chech status_code
        status_code = c.getinfo(pycurl.HTTP_CODE)
        c.close() 
        #FIXME Que devuelve??
        return status_code



    def getSeries(self):
        c = pycurl.Curl()
        b = StringIO()
        c.setopt(pycurl.URL, self.server + SERIES_ENDPOINT)
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.COOKIE, self.cookie)
        c.perform()
        c.close() 
        series_json = json.loads(b.getvalue())
        # convert JSON in ARRAY
        out = list()
        for series in series_json["catalogs"]:
            s = dict()
            for key, value in series["http://purl.org/dc/terms/"].iteritems():
                s[key] = value[0]["value"]
            out.append(s)
        return out
