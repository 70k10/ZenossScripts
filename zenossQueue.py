#!/usr/bin/env python

#####################################################################
# SET ME
#####################################################################

device_name = 'server'
template_name = 'AMQ'

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
#from Products import ZenModel
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from transaction import commit
#from re import split,sub

#####################################################################
# Zenoss Setup
#####################################################################

dmd = ZenScriptBase(connect=True).dmd

#####################################################################
# Variables
#####################################################################

queues = []
dpNames = []
GraphPoints = []
attributeMap = dict((('MemoryPercentUsage', 'Memory'), \
                ('ConsumerCount', 'Consumers'), \
                ('QueueSize', 'Messages'), \
                ('MinEnqueueTime', 'Queue_Performance'), \
                ('AverageEnqueueTime', 'Queue_Performance'), \
                ('MaxEnqueueTime', 'Queue_Performance')))
graphSuffixes = ['Memory', 'Consumers', 'Messages', 'Queue_Performance']
queueDatapoints = []

#####################################################################
# Functions
#####################################################################

# Creates or Finds Device
# Accepts: dmd object, device name
# Returns: device object
def acquireDevice(dmd, dev):
    device = dmd.Devices.findDevice(dev)
    return device

# Creates or Finds Template
# Accepts: device, template_name
# Returns: template object
def findTemplate(device, template_name):
    template = [temp for temp in device.getRRDTemplates() if temp.id == template_name]
    if template == []:
        device.addLocalTemplate(template_name)
        template = [temp for temp in device.getRRDTemplates() if temp.id == template_name]
    return template[0]

# Creates Datasources on templates for Graphs
# Accepts: queue
# Returns: datapoint name
# MemoryPercentUsage, ConsumerCount, QueueSize, MinEnqueueTime, AverageEnqueueTime, MaxEnqueueTime
def createDataSources(template, queue):
    attributeList = ['MemoryPercentUsage', 'ConsumerCount', 'QueueSize', 'MinEnqueueTime', 'AverageEnqueueTime', 'MaxEnqueueTime']
    datapointList = []
    for attribute in attributeList:
        DS = template.manage_addRRDDataSource(''.join([queue, attribute]), 'JMXDataSource.JMX')
        DS.enabled = 'true'
        DS.jmxPort = 1099
        DS.attributeName = attribute
#    DS.eventClass = '/Status/Web'
        DS.objectName = ''.join(["org.apache.activemq:BrokerName=localhost,Type=Queue,Destination=",queue])
        DP = DS.manage_addRRDDataPoint(attribute)
        DP.rrdtype = 'GAUGE'
        datapointList.append(DP.name())
    return datapointList

# Finds or creates a Graph
# Accepts: template, graphname
# Returns: graph object
def findGraph(template, graphname):
#If there are no graphs on the template then generate a new graph
    if template.getGraphDefs() == []:
        print "generating graph"
        graph = template.manage_addGraphDefinition(graphname)
    else:
        print "generating graph"
        graph = [ tempgraph for tempgraph in template.getGraphDefs() if tempgraph.id ==  graphname ]
        if graph == []:
            graph = template.manage_addGraphDefinition(graphname)
        else:
            return graph[0]
    return graph

# Renames the graphpoint in the graph legend
# Accepts: graphpoint
# Returns: None
def renameGraphLegend(graphPoint):
    print graphPoint
    graphPoint.legend = ''.join(["_%s"  % (sub('\.do$|\.htm$|\.html$', '', path)) for path in graphPoint.dpName.split(' ')]).lstrip('_')
#    print graphPoint.legend

#####################################################################
# Queue Name Import
#####################################################################

# Pulls out the template name by checking for any line not starting with a symbol or URL
queues = [ queue.rstrip('\n') for queue in open('Queues.txt') ]

#####################################################################
# Main
#####################################################################

device = acquireDevice(dmd, device_name)
template = findTemplate(device, template_name)
for queue in queues:
    # Stores index of unique domain, datapoint, and agency for graph creation...Appends tuple
    queueDatapoints = createDataSources(template, queue)
    graphs = [ findGraph(template, ''.join([queue,'_',graph])) for graph in graphSuffixes ]
    [[graph.manage_addDataPointGraphPoints([queueDatapoint]) for graph in graphs \
    if graph.id == ''.join([queue,'_',attributeMap[queueDatapoint.rpartition("_")[2]]])] \
    for queueDatapoint in queueDatapoints]
#Check the attribute map and add the datapoints
#Rename the Legend

#    graph.addRRD...
#    GraphPoints.append(graph.manage_addDataPointGraphPoints(dataPoints))
#    [ renameGraphLegend(graphPoint) for graphPoint in GraphPoints[0] ]
#    print GraphPoints
#    del GraphPoints

commit()
#EOF
