# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/mediapackage/serializer
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.


# TODO:
# * metadata dict in mediapackage *33

import zipfile
from os import path
from xml.dom import minidom
from galicaster.mediapackage import mediapackage

SERIES_FILE="series.xml"


def save_in_dir(mp):
    assert path.isdir(mp.getURI())
    # FIXME use catalog to decide what files to modify or create


    # check if series should be added to the catalog

    # Episode **3
    m2 = open(path.join(mp.getURI(), 'episode.xml'), 'w')
    m2.write(set_episode(mp)) #FIXME
    m2.close()

    # Galicaster properties
    m = open(path.join(mp.getURI(), 'galicaster.xml'), 'w')
    m.write(set_properties(mp))
    m.close()

    # Series
    if mp.series not in [None, "", "[]"]:

        # Create or modify file
        m3 = open(path.join(mp.getURI(), SERIES_FILE), 'w')
        m3.write(set_series(mp)) #FIXME
        m3.close()        

    # Manifest
    m = open(path.join(mp.getURI(), 'manifest.xml'), 'w')  
    m.write(set_manifest(mp))  ##FIXME
    m.close()



def save_in_zip(mp, file):
    """
    Save in ZIP file

    @param mp Mediapackage to save in ZIP.
    @param file can be either a path to a file (a string) or a file-like object.
    """
    z = zipfile.ZipFile(file, 'w', zipfile.ZIP_STORED, True) # store only (DEFAULT)

    # manifest
    z.writestr('manifest.xml', set_manifest(mp))

    # episode (fist persist episode)
    m2 = open(path.join(mp.getURI(), 'episode.xml'), 'w')
    m2.write(set_episode(mp))
    m2.close()

    for catalog in mp.getCatalogs():
        if path.isfile(catalog.getURI()):
            z.write(catalog.getURI(), path.basename(catalog.getURI()))

    # tracks
    for track in mp.getTracks():
        if path.isfile(track.getURI()):
            z.write(track.getURI(), path.basename(track.getURI()))

    for attach in mp.getAttachments():
        if path.isfile(attach.getURI()):
            z.write(attach.getURI(), path.basename(attach.getURI()))

    # FIXME other elements
    z.close()


def set_properties(mp):
    """
    Crear la string para galicaster.properties
    """
    doc = minidom.Document()
    galicaster = doc.createElement("galicaster") 
    doc.appendChild(galicaster)
    status = doc.createElement("status")
    stext = doc.createTextNode(str(mp.status))
    status.appendChild(stext)
    galicaster.appendChild(status)
    notes = doc.createElement("notes")
    ntext = doc.createTextNode(mp.notes)
    notes.appendChild(ntext)
    galicaster.appendChild(notes)
    return doc.toxml(encoding="utf-8")


def set_manifest(mp):
    """
    Crear un manifest XML 
    """
    doc = minidom.Document()
    xml = doc.createElement("mediapackage") 
    #xml.setAttribute("xmlns:oc","http://mediapackage.opencastporject.org") FIXME is necesary?
    xml.setAttribute("id", mp.getIdentifier()) 
    xml.setAttribute("start", mp.getDate().isoformat())
    if mp.getDuration() != None:
        xml.setAttribute("duration", str(mp.getDuration())) 
    
    doc.appendChild(xml)
    media = doc.createElement("media")          
    xml.appendChild(media)
    metadata = doc.createElement("metadata")
    xml.appendChild(metadata)
    attachments = doc.createElement("attachments")          
    xml.appendChild(attachments)
    # FIXME attachement and others
    
    for t in mp.getTracks(): 
        track = doc.createElement("track")
        track.setAttribute("id", t.getIdentifier())
        track.setAttribute("type", t.getFlavor())
        mime = doc.createElement("mimetype")
        mtext = doc.createTextNode(t.getMimeType()) 
        mime.appendChild(mtext)
        url = doc.createElement("url")
        utext = doc.createTextNode(path.basename(t.getURI()))
        url.appendChild(utext)
        duration = doc.createElement("duration")               
        dtext = doc.createTextNode(str(t.getDuration()))
        duration.appendChild(dtext)
        track.appendChild(mime)
        track.appendChild(url)
        track.appendChild(duration)
        media.appendChild(track)

    for c in mp.getCatalogs():
        cat = doc.createElement("catalog")
        cat.setAttribute("id", c.getIdentifier())
        cat.setAttribute("type", c.getFlavor())
        loc = doc.createElement("url")
        uutext = doc.createTextNode(path.basename(c.getURI()))
        loc.appendChild(uutext)
        mim = doc.createElement("mimetype")
        mmtext = doc.createTextNode(c.getMimeType())
        mim.appendChild(mmtext)
        cat.appendChild(mim)
        cat.appendChild(loc)
        metadata.appendChild(cat)   

    for a in mp.getAttachments():
        attachment = doc.createElement("attachment")
        cat.setAttribute("id", c.getIdentifier())
        loc = doc.createElement("url")
        uutext = doc.createTextNode(path.basename(a.getURI()))
        loc.appendChild(uutext)
        attachment.appendChild(loc)
        attachments.appendChild(attachment)   
        
    # FIXME ADD checksum
    # return doc.toprettyxml(indent="   ", newl="\n",encoding="utf-8")    
    return doc.toxml(encoding="utf-8")          
         

def set_episode(mp):
    """
    Crear un episode XML
    """
    doc = minidom.Document()
    xml = doc.createElement("dublincore")
    xml.setAttribute("xmlns","http://www.opencastproject.org/xsd/1.0/dublincore/")
    xml.setAttribute("xmlns:xsi","http://www.w3.org/2001/XMLSchema-instance/")
    xml.setAttribute("xmlns:dcterms","http://purl.org/dc/terms/")
    doc.appendChild(xml)
    for name in mediapackage.DCTERMS: #FIXME *33
        try:
            if not mp.metadata_episode[name]:
                continue
            if type(mp.metadata_episode[name]) is not list:
                created = doc.createElement("dcterms:" + name)
                text = doc.createTextNode(str(mp.metadata_episode[name]))
                created.appendChild(text)
                xml.appendChild(created)
            else:
                if  len(mp.metadata_episode[name]):
                    for element in mp.metadata_episode[name]:
                        created = doc.createElement("dcterms:" + name)
                        text = doc.createTextNode(element)
                        created.appendChild(text)
                        xml.appendChild(created)
                    
        except KeyError:
            continue

    return doc.toxml(encoding="utf-8") #without encoding



def set_series(mp):
    """
    Crear un episode XML
    """
    doc = minidom.Document()
    xml = doc.createElement("dublincore")
    xml.setAttribute("xmlns","http://www.opencastproject.org/xsd/1.0/dublincore/")
    xml.setAttribute("xmlns:dcterms","http://purl.org/dc/terms/")
    doc.appendChild(xml)
    for name in ["title", "identifier"]: # FIXME Set mediapackage.SeriesDCTERMS
        try:
            created = doc.createElement("dcterms:" + name)
            text = doc.createTextNode(str(mp.metadata_series[name]))
            created.appendChild(text)
            xml.appendChild(created)
        except KeyError:
            print "KeyError in serializer.set_series"
            continue
    return doc.toxml(encoding="utf-8") #without encoding
