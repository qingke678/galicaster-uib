# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/recorder/pipeline/audiotest
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.

import logging

import gobject
import gst

from os import path
from galicaster.recorder import base
from galicaster.recorder import module_register

pipestr = (" audiotestsrc name=gc-audiotest-src is-live=true freq=440 volume=0.8 wave=5 ! " 
           " audioamplify name=gc-audiotest-amplify amplification=1 ! tee name=tee-aud  ! queue ! "
           " level name=gc-audiotest-level message=true interval=100000000 ! "
           " volume name=gc-audiotest-volume ! alsasink name=gc-audiotest-preview  sync=false "
           " tee-aud. ! queue ! valve drop=false name=gc-audiotest-valve ! "
           " audioconvert ! lamemp3enc target=1 bitrate=192 cbr=true !  queue ! filesink name=gc-audiotest-sink async=false ")

class GCaudiotest(gst.Bin, base.Base):

    order = ["name", "flavor", "location", "file", 
             "vumeter", "player","amplification",
             "volume", "pattern", "frequency",
             ]

    gc_parameters = {
        "name": {
            "type": "text",
            "default": "AudioTest",
            "description": "Name assigned to the device",
            },
        "flavor": {
            "type": "flavor",
            "default": "presenter",
            "description": "Matterhorn flavor associated to the track",
            },
        "location": {
            "type": "device",
            "default": "default",
            "description": "Device's mount point of the MPEG output",
            },
        "file": {
            "type": "text",
            "default": "sound.mp3",
            "description": "The file name where the track will be recorded.",
            },
        "vumeter": {
            "type": "boolean",
            "default": True,
            "description": "Activate Level message",
            },
        "player": {
            "type": "boolean",
            "default": True,
            "description": "Enable sound play",
            },
        "amplification": {
            "type": "float",
            "default": 1.0,
            "range": (0,10),
            "description": "Audio amplification",
            },
        "volume": {
            "type": "float",
            "default": 0.5,
            "range": (0,1),
            "description": "Audio volume",
            },
        "pattern": {
            "type": "select",
            "default": "pink-noise",
            "options": ["sine", "square", "saw", "triangle",
                        "white-noise", "pink-noise", "sine-table"
                        "ticks", "gaussian-noise", "red-noise"
                        "blue-noise", "violet-noise"
                        ],                                  
            "description" : "Premade samples to test audio",
            },                      
        "frequency":  {
            "type": "integer",
            "default" : 440,
            "range" : (0, 20000),
            "description": "Reference frequency of the sample, 0-20000 Hz"
            },
        }

    is_pausable = True
    has_audio   = True
    has_video   = False
    
    __gstdetails__ = (
        "Galicaster Audio BIN",
        "Generic/Audio",
        "Mock Audio Source for testing purpuses",
        "Teltek Video Research"
        )

    def __init__(self, options={}): 
        base.Base.__init__(self, options)
        gst.Bin.__init__(self, self.options["name"])

        bin = gst.parse_bin_from_description(pipestr.replace("gc-audiotest-preview", "sink-" + self.options["name"]), True)

        self.add(bin)

        sink = self.get_by_name("gc-audiotest-sink")
        sink.set_property('location', path.join(self.options['path'], self.options['file']))

        if "player" in self.options and self.options["player"] == False:
            self.mute = True
            element = self.get_by_name("gc-audiotest-volume")
            element.set_property("mute", True)
        else:
            self.mute = False

        if "vumeter" in self.options:
            level = self.get_by_name("gc-audiotest-level")
            if self.options["vumeter"] == False:
                level.set_property("message", False) 
        if "amplification" in self.options:
            ampli = self.get_by_name("gc-audiotest-amplify")
            ampli.set_property("amplification", float(self.options["amplification"]))

        sink = self.get_by_name("gc-audiotest-src")          
        sink.set_property("freq", int(self.options["frequency"]))
        sink.set_property("volume", float(self.options["volume"]))
        sink.set_property("wave", str(self.options["pattern"]))    
            
        if not self.options["vumeter"]:
            level = self.get_by_name("gc-audiotest-level")
            level.set_property("message", False) 

    def changeValve(self, value):
        valve1=self.get_by_name('gc-audiotest-valve')
        valve1.set_property('drop', value)

    def getVideoSink(self):
        return self.get_by_name("gc-audiotest-preview")

    def getSource(self):
        return self.get_by_name("gc-audiotest-src")

    def getAudioSink(self):
        return self.get_by_name("gc-audiotest-preview")

    def send_event_to_src(self, event):
        src1 = self.get_by_name("gc-audiotest-src")
        src1.send_event(event)        

    def mute_preview(self, value):
        if not self.mute:
            element = self.get_by_name("gc-audiotest-volume")
            element.set_property("mute", value)

    
gobject.type_register(GCaudiotest)
gst.element_register(GCaudiotest, "gc-audiotest-bin")
module_register(GCaudiotest, 'audiotest')
