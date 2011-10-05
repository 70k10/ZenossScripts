#!/usr/bin/env python

#####################################################################
# SET ME
#####################################################################

bulkFile = 'PSList.txt'
devPth = "/Server/Windows/WMI"
SNMPComm = ""
#SNMPPort = 
collector = "localhost"
#discoveryProtocol = "snmp"
#snmpcommunity = ""
#discoveryProtocol="snmp"
deviceSuffix=".something.com"

#####################################################################
# TODO
#####################################################################


#####################################################################
# Imports
#####################################################################

from os import path
import sys
#import os.path
#from stat import *
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from transaction import commit
from Products import ZenModel
from re import split,sub

#####################################################################
# Zenoss Setup
#####################################################################

dmd = ZenScriptBase(connect=True).dmd

#####################################################################
# Variables
#####################################################################

file = open(bulkFile)
server = []
devList = []

#####################################################################
# Functions
#####################################################################


#####################################################################
# Main
#####################################################################


server = [box.split(';') for box in file]
file.close()
del file

devList = [ZenModel.Device.manage_createDevice(dmd, ''.join([dev[0],deviceSuffix]), devicePath=devPth, manageIp=dev[1].rstrip('\n'), performanceMonitor=collector, title=''.join([dev[0],deviceSuffix])) for dev in server]

del server

holder = [mdldev.collectDevice(background=True) for mdldev in devList]
del devList
del holder

commit()
#EOF
