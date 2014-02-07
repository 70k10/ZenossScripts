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

#####################################################################
# Imports
#####################################################################

from os import path
import sys
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from transaction import commit
from re import split,sub
from Products import ZenModel
import itertools

#####################################################################
# Zenoss Setup
#####################################################################

dmd = ZenScriptBase(connect=True).dmd

#####################################################################
# Variables
#####################################################################

#template_name = ''
dpNames = []
GraphPoints = []
agencies = []
agencycount = {}
urls = {}
domains = {}

#####################################################################
# Functions
#####################################################################

# Hacks up URLs and determines SSL
# Accepts URL
# returns: [bool ssl, domain, url, space delim url]
def parseLine(line):
    secure = 0
    if line[0].startswith('http'):
        port = line[(len(line)-1)].split(';')[1]
        text = line[(len(line)-1)].split(';')[2]
        if line[0].startswith('https'):
            secure = 1
        line.pop(0)
        line.pop(0)
        return (secure, line.pop(0), ''.join(["/%s" % (path.split(';')[0]) for path in line]), ''.join(["%s " % (path.split(';')[0]) for path in line]).rstrip(' '), port, text)

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
def createDataSources(template, secure, url, urlSpaces, port, text):
#    DS = template.manage_addRRDDataSource(urlSpaces, 'HttpMonitorDataSource.HttpMonitor')
    proto = "http://"
    DS = template.manage_addRRDDataSource(urlSpaces, 'WebTxDataSource.WebTx')
    DS.enabled = 'true'
    DS.eventClass = '/Status/Web'
    #DS.url = url
    #DS.commandTemplate = "go https://secure.intranetappstest.nd.gov/itd/onlineservices/scheddowntime/admin/login.htm\n find 'Login'"
    findquery = ""
    if text:
        findquery = ''.join(["\nfind ", "'", text, "'"])
    if secure:
        DS.useSsl = 1
        DS.port = 443
        proto = "https://"
    if port:
        DS.port = port
    DS.commandTemplate = ''.join(["go ", proto, "${dev/id}", url, findquery])
    DP =  DS.manage_addRRDDataPoint('available')
    #DP = DS.manage_addRRDDataPoint('size')
    DP.rrdtype = 'GAUGE'
    DP =  DS.manage_addRRDDataPoint('totalTime')
    #DP = DS.manage_addRRDDataPoint('time')
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

# Line Parser
def lineParser(inputfile):
    templates = []
    urls = []
    domains = []
    for line in inputfile:
        if (line[:1].isalpha() and not line.startswith('http')):
            templates.append(line)
            tempidx = (len(templates)-1)
            urls.append('')
            urls[tempidx] = []
            domains.append('')
            domains[tempidx] = []
        elif (line[:1].isalpha() and line.startswith('http')):
            parsedLine = parseLine(line.split('/'))
            domains[tempidx].append(parsedLine[1])
            urls[tempidx].append(parsedLine)
    urls.sort
    domains = [ uniq(domain) for domain in domains ]
    print domains
# Create the template dictionary for urls
    return dict(itertools.izip(templates, urls[:])), dict(itertools.izip(templates, domains[:]))


#####################################################################
# FILE Handling
#####################################################################

urlfile = open('testURLs.txt')
fileobjects = [ objects.rstrip('\n') for objects in urlfile ]
urlfile.close()
del urlfile

#####################################################################
# Parser
#####################################################################

urls,domains = lineParser(fileobjects)

#####################################################################
# URL Parsing
#####################################################################

# Acquires unique domain names
#domains = uniq([ domain[1] for domain in parsedURL ])

#if graphbyagency == 1:
# Grab a unique list of agencies
#    agencies = uniq([url[3].split(' ')[0] for url in parsedURL ])
#    print agencies

#####################################################################
# Main
#####################################################################

#for url in parsedURL:
print urls
for template_name in urls.iterkeys():
    if graphbyagency == 1:
         print "graphing"
         #Grab a unique list of agencies
         agencies = uniq([ url[3].split(' ')[0] for url in urls[template_name] ])
    for url in urls[template_name]:
        device = acquireDevice(dmd, url[1])
        template = findTemplate(device, template_name)
        # Stores index of unique domain, datapoint, and agency for graph creation...Appends tuple
        dpNames.append((domains[template_name].index(url[1]), createDataSources(template, url[0], url[2], url[3], url[4], url[5]), url[3].split(' ')[0]))
        del device
        del template
    # Sort our DataPoint list
    dpNames.sort()
    # Cycle through our domains and create the devices, templates, graphs, and graphpoints as necessary
    for domainNumber in xrange(len(domains[template_name])):
        print domains[template_name][domainNumber]
        device = acquireDevice(dmd, domains[template_name][domainNumber])
        template = findTemplate(device, template_name)
        if graphbyagency == 1:
            # All agencies in this domain
            tempAgencies = [ dpName[2] for dpName in dpNames if dpName[0] == domainNumber ]
            # Count the agencies for this domain
            agencycount = dict([ (ag, tempAgencies.count(ag)) for ag in agencies])
            #print tempAgencies
            del tempAgencies
            for agency in agencies:
                GraphPoints = []
                # Grab datapoints filtered by agency and domain
                dataPoints = [ dpName[1] for dpName in dpNames if dpName[0] == domainNumber and dpName[2] == agency]
                if agencycount[agency] >= minagencygraph:
                    print agency
                    print dataPoints
                    graph = findGraph(template, template_name, graphbyagency, agency)
                    GraphPoints.append(graph.manage_addDataPointGraphPoints(dataPoints))
                    [ renameGraphLegend(graphPoint) for graphPoint in GraphPoints[0] ]
                    print GraphPoints
                    del GraphPoints
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

commit()
