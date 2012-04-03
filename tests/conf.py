# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       tests/conf
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.


"""
Unit tests for `galicaster.util.conf` module.
"""
from os import path
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError
from unittest import TestCase

from galicaster.utils.conf import Conf


class TestFunctions(TestCase):
    
    
    def setUp(self):
        conf_file = path.join(path.dirname(path.abspath(__file__)), 'resources', 'conf', 'conf.ini')
        self.conf = Conf(conf_file)

           
    def tearDown(self):
        del self.conf
        

    def test_get_bins(self):
        self.assertEqual(len(self.conf.getBins('/tmp')), 3)
        #FIXME add more
