# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/utils/series
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.

import os
from os import path
from galicaster import context

OPTIONS  = ['short', 'name', 'id']

def get_series():
    repo = context.get_repository() 
    series_path = path.join(repo.get_attach_path(), 'series.attach')
    series = []
    
    if path.isfile(series_path):
        with open(series_path, 'r') as f:
            while 1:
                series.append(dict(zip(OPTIONS,[transform(f.readline()),
                                                transform(f.readline()),
                                                transform(f.readline())])))
                line=f.readline() # read empty line
                if not line:
                    break
    return series

def get_series2():
    match = dict()
    origin = get_series()
    for group in origin:
        match[group["id"]]=group["name"]
    return match
        
        
def getSeriesbyId(seriesid):
    """
    Generate a list with the series value name, shortname and id
    """
    list_series = get_series()
    match = dict()
    
    for serie in list_series:
        if serie["id"] == seriesid:
            match = serie
    return match       
    
def transform(a):
    return a.strip()

def getSeriesbyId(seriesid):
    """
    Generate a list with the series value name, shortname and id
    """
    list_series = get_series()
    match = dict()
    
    for serie in list_series:
        if serie["id"] == seriesid:
            match = serie
    return match        
    
def getSeriesbyShort(seriesid):
    """
    Generate a list with the series value name, shortname and id
    """
    list_series = get_series()
    match = dict()
    for serie in list_series:
        if serie["short"] == seriesid:
            match = serie
    return match    

def getSeriesbyName(seriesid):
    """
    Generate a list with the series value name, shortname and id
    """
    list_series = get_series()
    match = dict()
    for serie in list_series:
        if serie["name"] == seriesid:
            match = serie
    return match      
    


