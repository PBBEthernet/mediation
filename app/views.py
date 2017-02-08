import os
import sys
import io
import requests
import logging
from datetime import datetime
import xmltodict
import xml.etree.ElementTree as ET
from flask import jsonify, abort, make_response, render_template, request, Response, url_for
from flask.ext.httpauth import HTTPBasicAuth
from app import app

#app.logger = logging.getLogger('NSOREST')
#hdlr = logging.FileHandler('/poc/app/server.log')
#formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
#hdlr.setFormatter(formatter)
#app.logger.addHandler(hdlr)
#app.logger.setLevel(logging.INFO)

auth = HTTPBasicAuth()

@auth.get_password
def get_password(username):
 if username == 'dcidemo':
    return 'DCIPoC'
 elif username == 'admin':
    return 'admin'
 return None

@auth.error_handler
def unauthorized():
 return make_response(jsonify({'message': 'Unauthorized access'}), 403)

@app.errorhandler(500)
def internal_error(exception):
 app.logger.error(exception)


@app.route('/')
@app.route('/index')
def index():
	user = {'nickname': 'MEF PoC'}
	features = [  # array of features
                {
                        'service': {'function': 'Get Devices'},
                        'uri': url_for('getDevices')
                },
                {
                        'service': {'function': 'Get Interfaces'},
                        'uri': url_for('getInterfaces', devID='dev1')
                },
        	{ 
            		'service': {'function': 'Create'}, 
            		'uri': url_for('createServices') 
        	},
        	{ 
            		'service': {'function': 'Delete'}, 
            		'uri': url_for('deleteService', serviceName='OVC1')
        	}
    	]
	return render_template('index.html',title='Home',user=user,features=features)

@app.route('/TATAapi/running/devices', methods=['GET'])
@auth.login_required
def getDevices():
 dev = requests.get("http://172.20.170.110:8080/api/running/devices/", auth=('admin','admin'))
 #return (dev.text, dev.status_code, dev.headers.items())
 d = xmltodict.parse(dev.text)
 devXML = ET.Element('devices')
 for device in d['devices']['device']:
  if device['name'] == 'elab9075.elab.tata':
   device1XML = ET.SubElement(devXML, 'device')
   ET.SubElement(device1XML, 'id').text = 'dev1'
   ET.SubElement(device1XML, 'name').text = 'TATA-DCI-A'
  if device['name'] == 'elab9085.elab.tata':
   device2XML = ET.SubElement(devXML, 'device')
   ET.SubElement(device2XML, 'id').text = 'dev2'
   ET.SubElement(device2XML, 'name').text = 'TATA-DCI-Z'
 devicesXML = ET.tostring(devXML)
 return devicesXML, dev.status_code, dev.headers.items()

@app.route('/TATAapi/running/devices/<string:devID>/interfaces', methods=['GET'])
@auth.login_required
def getInterfaces(devID):
 dev = ''
 port = ''
 if devID == 'dev1':
  dev = 'elab9075.elab.tata'
 if devID == 'dev2':
  dev = 'elab9085.elab.tata'

 ifs = requests.get("http://172.20.170.110:8080/api/running/devices/device/"+dev+"/config/interface/", auth=('admin','admin'))
 ifsDict = xmltodict.parse(ifs.text)
 ifsXML = ET.Element('interfaces')
 if ifs.status_code == 200:
  for ifsD in ifsDict['interface']['GigabitEthernet']:
   if (devID=='dev1') and (ifsD['id']=='0/0/0/16'):
    if1XML = ET.SubElement(ifsXML, 'inerface')
    ET.SubElement(if1XML, 'id').text = 'dev1p1'
    ET.SubElement(if1XML, 'name').text = 'TATA-DCI-A-GE'
   if (devID == 'dev2') and (ifsD['id'] == '0/0/0/16'):
    if1XML = ET.SubElement(ifsXML, 'inerface')
    ET.SubElement(if1XML, 'id').text = 'dev2p1'
    ET.SubElement(if1XML, 'name').text = 'TATA-DCI-Z-GE'
  ifssXML = ET.tostring(ifsXML)
  return ifssXML, ifs.status_code, ifs.headers.items()
 else:
  return 'No device found!'

@app.route('/TATAapi/running/services', methods=['GET'])
@auth.login_required
def getServices():
 app.logger.info('Get Service request received from: ' + request.headers['host'])
 app.logger.info(request.data)
 services = requests.get("http://172.20.170.110:8080/api/running/services/", auth=('admin','admin'))
 return (services.text, services.status_code, services.headers.items())

@app.route('/TATAapi/running/services/<string:serviceName>', methods=['GET'])
@auth.login_required
def getService(serviceName):
 service = requests.get("http://172.20.170.110:8080/api/running/services/pbb-evpl/"+serviceName+"/uni-endpoints", auth=('admin','admin'))
 return (service.text, service.status_code, service.headers.items())

@app.route('/TATAapi/running/services/construct', methods=['POST'])
@auth.login_required
def createServices():
 app.logger.info('Create request received from: ' + request.headers['host'])
# eciXMLReq = request.environ['wsgi.input'].read()
 eciXMLReq = getChunkData(request)
 app.logger.info('WSGI input read.......' + eciXMLReq)
 if not eciXMLReq:
  eciXMLReq = request.stream.read()
  app.logger.info('Stream read.......' + eciXMLReq)
 if not eciXMLReq:
  eciXMLReq = request.get_data()
  app.logger.info('Got data in another approach ' + eciXMLReq)
 if not eciXMLReq:
  eciXMLReq = request.data
  app.logger.info('Request.data shows ...........' + eciXMLReq)
 len = request.headers["Content-Length"]
 app.logger.info('Request content type ' + request.headers['Content-Type'])
 app.logger.info('Request content length ' + len)
 
 try:
  app.logger.info('Start synching devices..')
  nodesync('admin','admin','/poc/app/service.xml')
  app.logger.info('Successfully completed device synchronization..')
  with open('/poc/app/service.xml') as f:
   xmlTATA = xmltodict.parse(f) 
  if(request.headers['Content-Type'] == 'application/xml'):
   xmlECI = xmltodict.parse(eciXMLReq)
  else:
   return Response('Data format mismatch!Request should have application/xml content type!', status=412, mimetype='text/xml')
  ECIServName = xmlECI['forwarding_construct']['id']

#  if(os.path.isfile('/poc/app/newservice.xml')):
#   with open('/poc/app/newservice.xml') as sf:
#    existServDict = xmltodict.parse(sf)
#   if(existServDict['service']['ReqName'] == ECIServName):
#    TATAServName = existServDict['service']['TATAName']
#    existingServices = requests.get("http://172.20.170.110:8080/api/running/services/", auth=('admin','admin'))
#    if(existingServices.status_code == 200):
#     existServicesDict = xmltodict.parse(existingServices.text)
#     for service in existServicesDict['services']['pbb-evpl']:
#      if(service['name'] == TATAServName):
#       return Response('Service already exists!', status=412, mimetype='text/xml')
#    else:
#     return Response('Server Error!', status=500, mimetype='text/xml')
#   else:
#    return Response('One service exists with name '+existServDict['service']['ReqName']+'!', status=412, mimetype='text/xml')

  xmlTATA['services']['pbb-evpl']['name'] = xmlECI['forwarding_construct']['id']
  bandwidth = int(xmlECI['forwarding_construct']['ovc_end_point'][0]['ingress_bw_cfg_cir'])

  if(bandwidth > 100):
   return Response('Bandwidth request must be less than 100Mb!', status=412, mimetype='text/xml')

  xmlTATA['services']['pbb-evpl']['bandwidth'] = str(bandwidth)
  for endpoint in xmlECI['forwarding_construct']['ovc_end_point']:
#   ECIPhysPort = endpoint['end_point_interface']['physical_port_reference_port']
#   TATAPhysPort = ''
#   if ECIPhysPort == '2':
#    app.logger.info('Configuring port 15 ....')
#    TATAPhysPort = 'GigabitEthernet0/0/0/15'
#   else:
#    TATAPhysPort = 'GigabitEthernet0/0/0/16'
   if endpoint['end_point_id'] == 'TATA.DCI.P1':
    xmlTATA['services']['pbb-evpl']['uni-endpoints'][0]['device'] = 'elab9075.elab.tata'
    xmlTATA['services']['pbb-evpl']['uni-endpoints'][0]['interface'] = 'GigabitEthernet0/0/0/19'
    xmlTATA['services']['pbb-evpl']['uni-endpoints'][0]['port-type'] = 'customer-vlan'
    xmlTATA['services']['pbb-evpl']['uni-endpoints'][0]['cvlan'] = endpoint['end_point_vlan_map_ce_vlan']
    xmlTATA['services']['pbb-evpl']['uni-endpoints'][0]['ingress-vlan'] = endpoint['end_point_vlan_map_ce_vlan']     #for NNI, ingress-vlan will not be used. this value will be used as a string to create sub-interface name  
   if endpoint['end_point_id'] == 'TATA.DCI.P2':
    xmlTATA['services']['pbb-evpl']['uni-endpoints'][1]['device'] = 'elab9085.elab.tata'
    xmlTATA['services']['pbb-evpl']['uni-endpoints'][1]['interface'] = 'GigabitEthernet0/0/0/19'
    xmlTATA['services']['pbb-evpl']['uni-endpoints'][1]['port-type'] = 'customer-vlan'
    xmlTATA['services']['pbb-evpl']['uni-endpoints'][1]['cvlan'] = endpoint['end_point_vlan_map_ce_vlan']
    xmlTATA['services']['pbb-evpl']['uni-endpoints'][1]['ingress-vlan'] = endpoint['end_point_vlan_map_ce_vlan']     #for NNI, ingress-vlan will not be used. this value will be used as a string to create sub-interface name
#    xmlTATA['services']['pbb-evpl']['uni-endpoints'][1]['operation'] = 'translate'
#    xmlTATA['services']['pbb-evpl']['uni-endpoints'][1]['operation-vlan'] = 3000
  
  content = xmltodict.unparse(xmlTATA, pretty=True)
  r = requests.patch("http://172.20.170.110:8080/api/running/services/",auth=('admin','admin'),data=content)
  if(r.status_code == 204):
   if os.path.isfile('/poc/app/newservice.xml'):
    reqServExist = False
    with open('/poc/app/newservice.xml') as f:
     parseXML = ET.parse(f)
     existServices = parseXML.getroot()
     reqServExist = False
     for service in existServices.findall('service'):
      if(service.find('Name').text == xmlTATA['services']['pbb-evpl']['name']):
       reqServExist = True
       break
    if(not reqServExist):
     reqServiceAdd = ET.SubElement(existServices, 'service')
     ET.SubElement(reqServiceAdd, 'Name').text = xmlTATA['services']['pbb-evpl']['name']
     fw = open('/poc/app/newservice.xml', 'wb')
     fw.write(ET.tostring(existServices))
     fw.close()
     return Response('Service Created.', status=200, mimetype='text/xml')
    else:
     return Response('Service Updated.', status=200, mimetype='text/xml')
   else:
    rootXML = ET.Element('services')
    newServXML = ET.SubElement(rootXML,'service')
#    ET.SubElement(newServXML, 'ReqName').text = xmlECI['forwarding_construct']['id']
    ET.SubElement(newServXML, 'Name').text = xmlTATA['services']['pbb-evpl']['name']
    newServFile = open('/poc/app/newservice.xml', 'wb')
    newServFile.write(ET.tostring(rootXML))
    newServFile.close()
    return Response('Service Created', status=200, mimetype='text/xml')
  else:
   return Response(r.text, r.status_code, r.headers.items())
 except Exception, e:
  return Response(str(e), status=500, mimetype='text/xml')

def getChunkData(reqObj):
 input = reqObj.environ.get('wsgi.input')
 length = reqObj.environ.get('CONTENT_LENGTH', '0')
 length = 0 if length == '' else int(length)
 app.logger.info('Content length.....' + str(length))
 chunkData = ''
 if length == 0:
  if input is None:
   return
  if reqObj.environ.get('HTTP_TRANSFER_ENCODING','0') == 'chunked':
   size = int(input.readline(),16)
   total = size
   while size > 0:
    chunkData += input.read(size+2)
    size = int(input.readline(),16)
    total += size
  app.logger.info('Total chunk data read from input....' + str(total))
 else:
  chunkData = reqObj.environ['wsgi.input'].read(length)
 return chunkData

def nodesync(uid,passwd,filename):
#''' device sync'''
 content=open(filename, 'rb').read()
 root = ET.fromstring(content)
 for child in root:
  serviceEPlist = child.findall('{http://com/example/evp}uni-endpoints')
 for serviceEP in serviceEPlist:
  node=serviceEP[0].text
  app.logger.info('Synching '+node)
  link = "http://172.20.170.110:8080/api/running/devices/device/"+node+"/_operations/sync-from"   
  r = requests.post(link,auth=(uid,passwd))

@app.route('/TATAapi/running/services/construct/<string:serviceName>', methods=['DELETE'])
@auth.login_required
def deleteService(serviceName):
 app.logger.info('Delete request received from: ' + request.headers['host'])
 app.logger.info(request.data)
 app.logger.info('Start synching devices..')
 nodesync('admin','admin','/poc/app/service.xml')
 app.logger.info('Successfully completed device synchronization..')
# if os.path.isfile('/poc/app/newservice.xml'):
#  with open('/poc/app/newservice.xml') as f:
#   newServiceDict = xmltodict.parse(f)
#  tataServName = ''
#  if newServiceDict['service']['ReqName'] == serviceName:
#   tataServName = newServiceDict['service']['TATAName'] 
 existingServices = requests.get("http://172.20.170.110:8080/api/running/services/", auth=('admin','admin'))
 if(existingServices.status_code == 200):
  existServicesDict = xmltodict.parse(existingServices.text)
  for service in existServicesDict['services']['pbb-evpl']:
   if(service['name'] == serviceName):
    r = requests.delete("http://172.20.170.110:8080/api/running/services/pbb-evpl/"+serviceName,auth=('admin','admin'))
    if (r.status_code == 204):
#     os.remove('/poc/app/newservice.xml')
     return Response('Service deleted!', status=200, mimetype='text/xml')
    else:
     return r.text, r.status_code, r.headers.items()
 return Response('Service does not exist!', status=412, mimetype='text/xml')
#   return Response('Service does not exist!', status=412, mimetype='text/xml')
#  else:
#   return Response('Cannot find the service!', status=412, mimetype='text/xml')
# else:
#  return Response('Service does not exist!', status=412, mimetype='text/xml') 
