#!/usr/bin/env python

#####################################################################
# SET ME!
#####################################################################
#Whether to graph by agency
graphbyagency = 1
#Minimum URLs per agency for a separate graph
minagencygraph = 3

#####################################################################
# TODO
#####################################################################

#Save list of unique domains - DONE
#Save list of dpNames w/ reference to domain - DONE
#Create Graph - DONE
#get device/template/graph for the domain in question - DONE
#Build graph - DONE
#Setup separate graphs for agencies - DONE
#Set ports for JVMs
#Set Regular Expression for testing

#####################################################################
# Imports
#####################################################################

from os import path
import sys
#import os.path
#from stat import *
#import ZenModel
#from ZenModel import Device
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from transaction import commit
from re import split,sub
from Products import ZenModel

#####################################################################
# Zenoss Setup
#####################################################################

dmd = ZenScriptBase(connect=True).dmd

#####################################################################
# Variables
#####################################################################

template_name = ''
dpNames = []
GraphPoints = []
agencies = []
agencycount = {}

#####################################################################
# Functions
#####################################################################

# Since Python 2.4 doesn't have nice list sorting, we have our own compare
def cmp1(a,b): return cmp(a[1],b[1])

# Hacks up URLs and determines SSL
# Accepts URL
# returns: [bool ssl, domain, url, space delim url]
def parseURL(url):
    secure = 0
    if url[0].startswith('http'):
        if url[0].startswith('https'):
            secure = 1
        url.pop(0)
        url.pop(0)
        return [secure, url.pop(0), ''.join(["/%s" % (path.rstrip('\n')) for path in url]), ''.join(["%s " % (path.rstrip('\n')) for path in url])]

# Creates or Finds Device
# Accepts: dmd object, device name
# Returns: device object
def acquireDevice(dmd, dev):
    if dmd.Devices.findDevice(dev) == None:
        device = ZenModel.Device.manage_createDevice(dmd, dev, devicePath="/HTTP", discoverProto="")
    else:
        device = dmd.Devices.findDevice(dev)
    return device

# Creates or Finds Template
# Accepts: device, template_name
# Returns: template object
def findTemplate(device, template_name):
    template = [temp for temp in device.getRRDTemplates() if temp.id == template_name]
    if template == []:
        template = device.addLocalTemplate(template_name)
        template = [temp for temp in device.getRRDTemplates() if temp.id == template_name]
    return template[0]

# Creates Datasources on templates for Graphs
# Accepts: template object, bool ssl, context root, context root space delimited
# Returns: datapoint name
def createDataSources(template, secure, url, urlSpaces):
    DS = template.manage_addRRDDataSource(urlSpaces, 'HttpMonitorDataSource.HttpMonitor')
    DS.enabled = 'true'
    DS.eventClass = '/Status/Web'
    DS.url = url
    if secure:
        DS.useSsl = 1
        DS.port = 443
    DP = DS.manage_addRRDDataPoint('size')
    DP.rrdtype = 'GAUGE'
    DP = DS.manage_addRRDDataPoint('time')
    DP.rrdtype = 'GAUGE'
    return DP.name()

# Finds or creates a Graph
# Accepts: template, template_name
# Returns: graph object
def findGraph(template, template_name, graphbyagency, agency):
    if graphbyagency == 1 and agency != '':
        newgraphname = ''.join([template_name, ' - ', agency])
    else:
        newgraphname = template_name
    if template.getGraphDefs() == []:
        print "generating graph"
        graph = template.manage_addGraphDefinition(newgraphname)
    else:
        graph = [ tempgraph for tempgraph in template.getGraphDefs() if tempgraph.id ==  newgraphname ]
        if graph == []:
            graph = template.manage_addGraphDefinition(newgraphname)
        else:
            return graph[0]
    return graph

# Renames the graphpoint in the graph legend
# Accepts: graphpoint
# Returns: None
def renameGraphLegend(graphPoint):
#    print graphPoint
    graphPoint.legend = ''.join(["_%s"  % (sub('\.do$|\.htm$|\.html$', '', path)) for path in graphPoint.dpName.split(' ')]).lstrip('_')
#    print graphPoint.legend

# Fast unique
def uniq(seq):
    return {}.fromkeys(seq).keys()

#####################################################################
# URL Parsing
#####################################################################

# Pulls out the template name by checking for any line not starting with a symbol or URL
template_name = [ url.rstrip('\n') for url in open('testURLs.txt') if (url[:1].isalpha() and not url.startswith('http')) ][0]
# Splits each URL and passes through parseURL function
parsedURL = [ parseURL(url.split('/')) for url in open('testURLs.txt') if (url[:1].isalpha() and url.startswith('http')) ]
# Acquires unique domain names
domains = uniq([ domain[1] for domain in parsedURL ])

if graphbyagency == 1:
# Grab a unique list of agencies
    agencies = uniq([url[3].split(' ')[0] for url in parsedURL ])
#    agencycount = dict([(agency,0) for agency in agencies ])
#    print agencies

#####################################################################
# Main
#####################################################################

#generators
#device = (acquireDevice(object[0]) for object in parsedURL)
#template = (findTemplate(dev,template_name) for dev in device)
#DP = (zip(domains.index(url[0]), createDataSources(template, url[0], url[2], url[3])) for url in parsedURL)
#if template.getRRDDataSources():
#    datasourcepaths = [datasource.url for datasource in template.getRRDDataSources()]
#graph = (findGraph(template, template_name) for j in xrange(len(parsedURL)))
    
#    if object[3] in datasourcepaths:
#        continue
for url in parsedURL:
    device = acquireDevice(dmd, url[1])
    template = findTemplate(device, template_name)
    # Stores index of unique domain, datapoint, and agency for graph creation...Appends tuple
    dpNames.append((domains.index(url[1]), createDataSources(template, url[0], url[2], url[3]), url[3].split(' ')[0]))
#    if graphbyagency == 1:
#        agencycount[url[3].split(' ')[0]] += 1
#        [ findGraph(template, template_name, graphbyagency, agency) for agency in agencies ]
#    else:
#        findGraph(template, template_name, graphbyagency, '')

# Sort our DataPoint list
dpNames.sort(cmp1)
#if graphbyagency == 1:
#    tempAgencies = [ dpName[2] for dpName in dpNames ]
#    agencyCounts = [ (ag, tempAgencies.count(ag) for ag in agencies ]
#    del tempAgencies

# Cycle through our domains and create the devices, templates, graphs, and graphpoints as necessary
for domainNumber in xrange(len(domains)):
    print domains[domainNumber]
    device = acquireDevice(dmd, domains[domainNumber])
    template = findTemplate(device, template_name)
    if graphbyagency == 1:
# All agencies in this domain
        tempAgencies = [ dpName[2] for dpName in dpNames if dpName[0] == domainNumber ]
# Count the agencies for this domain
        agencycount = dict([ (ag, tempAgencies.count(ag)) for ag in agencies])
#        print tempAgencies
#        agencyCounts = [ (ag, tempAgencies.count(ag)) for ag in agencies ]
        del tempAgencies
        for agency in agencies:
            GraphPoints = []
# Grab datapoints filtered by agency and domain
            dataPoints = [ dpName[1] for dpName in dpNames if dpName[0] == domainNumber and dpName[2] == agency]
            if agencycount[agency] >= minagencygraph:
#            if agencyCounts[agency] >= minagencygraph:
                print agency
                print dataPoints
                graph = findGraph(template, template_name, graphbyagency, agency)
                GraphPoints.append(graph.manage_addDataPointGraphPoints(dataPoints))
                [ renameGraphLegend(graphPoint) for graphPoint in GraphPoints[0] ]
                print GraphPoints
                del GraphPoints
#            elif agencyCounts[agency] > 0:
            elif agencycount[agency] > 0:
                print agency
                print dataPoints
# Assign to the default template
                graph = findGraph(template, template_name, graphbyagency, '')
                GraphPoints.append(graph.manage_addDataPointGraphPoints(dataPoints))
                [ renameGraphLegend(graphPoint) for graphPoint in GraphPoints[0] ]
                print GraphPoints
                del GraphPoints
# Need to add the counts in and finish
    else:
        dataPoints = [ dpName[1] for dpName in dpNames if dpName[0] == domainNumber ]
        graph = findGraph(template, template_name, graphbyagency, agency)
        GraphPoints.append(graph.manage_addDataPointGraphPoints(dataPoints))
        [ renameGraphLegend(graphPoint) for graphPoint in GraphPoints[0] ]
    


#print GraphPoints
# Rename the legend in the graph to something a little more human friendly
#[ renameGraphLegend(graphPoint) for graphPoint in GraphPoints[0] ]

commit()
