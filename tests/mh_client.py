# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       tests/mh_client
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.


"""
Unit tests for `galicaster.utils` module.
"""

from unittest import TestCase
from galicaster.utils.mhhttpclient import MHHTTPClient
from galicaster.player.player import Player

class TestFunctions(TestCase):
    def test_mhhttpclient_whoami(self):
        server = "http://admindev.matterhorn.uvigo.es:8080"
        user = "matterhorn_system_account";
        password = "CHANGE_ME";

        client = MHHTTPClient(server, user, password)
        mh_user = client.whoami()

        self.assertEqual(mh_user['username'], 'matterhorn_system_account')


    def test_mhhttpclient_series(self):
        server = "http://admindev.matterhorn.uvigo.es:8080"
        user = "matterhorn_system_account";
        password = "CHANGE_ME";

        client = MHHTTPClient(server, user, password)
        series = client.getSeries()    

        self.assertEqual(type(series), list)


    def test_setstate(self):
        server = "http://admindev.matterhorn.uvigo.es:8080"
        user = "matterhorn_system_account";
        password = "CHANGE_ME";
        client_name = "rubenrua_pr"
        client_address = "172.20.209.225"
        client_states = [ 'shutting_down', 'capturing', 'uploading', 'unknown', 'idle' ]        

        client = MHHTTPClient(server, user, password)
        
        for state in client_states:
            a = client.setstate(client_name, client_address, state)
            self.assertEqual(a, '{0} set to {1}'.format(client_name, state))


    def test_setcapabilities(self):
        server = "http://admindev.matterhorn.uvigo.es:8080"
        user = "matterhorn_system_account";
        password = "CHANGE_ME";
        client_name = "rubenrua_pr"
        client_address = "172.20.209.225"

        client = MHHTTPClient(server, user, password)
        
        a = client.setconfiguration(client_name, client_address) 
        #print a
        #FIXME add ssert
        #self.assertEqual(a, '{0} set to {1}'.format(client_name, state))


    def no_test_player(self):
        # files = {'presenter': '/tmp/CAMERA.mpeg', 'presentation': '/tmp/SCREEN.avi'}
        files = {'video': '/home/rubenrua/Videos/Prueba EHU.mp4'}
        inst = Player(files)
        inst.play()


    def no_test_bad_player(self):
        #files = {'presenter': '/tmp/CAMERA.mpeg', 'presentation': '/tmp/SCREEN.avi'}
        files = {'video': '/home/rubenrua/Videos/Prueba EHU.mp4'}
        players = {'video': '----'}
        inst = Player(files, players)
        inst.play()


