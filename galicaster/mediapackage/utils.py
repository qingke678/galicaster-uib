# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/mediapackage/utils
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.

from os import path

def _getElementAbsPath(name, base_path):
    if path.isabs(name):
        return name
    else:
        return path.join(base_path, name)
        

def _checknget(archive, name): 
    if archive.getElementsByTagName(name).length != 0:
        try:
            sout = archive.getElementsByTagName(name)[0].firstChild.wholeText.strip().strip("\n")
        except AttributeError:
            sout = ''
        return sout
