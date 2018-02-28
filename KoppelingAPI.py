# -*- coding: utf-8 -*-
"""
@author: Robin Kuijs
"""
 
#!/usr/bin/python3
import requests
import json
import datetime
import configparser
import logging
import datetime
import os
from io import BytesIO
 
# Config parameters, config file is in same directory
configParser = configparser.RawConfigParser()   
configFilePath = r'koppelingAPI.conf'
configParser.read(configFilePath)
urlSource = configParser.get('topdeskservers', 'urlSource')
userSource = configParser.get('topdeskservers', 'userSource')
pwSource = configParser.get('topdeskservers', 'pwSource')
uploadedFilesLocation = configParser.get('topdeskservers', 'uploadedFilesLocation')
urlTarget = configParser.get('topdeskservers', 'urlTarget')
userTarget = configParser.get('topdeskservers', 'userTarget')
pwTarget = configParser.get('topdeskservers', 'pwTarget')
operatorGroupTarget = configParser.get('topdeskservers', 'operatorGroupTarget')
operatorGroupTarget1 = configParser.get('topdeskservers', 'operatorGroupTarget1')
operatorGroupTarget2 = configParser.get('topdeskservers', 'operatorGroupTarget2')
 
# Filters
operatorGroup = configParser.get('filters', 'operatorGroup')
status = configParser.get('filters', 'status')
pageSize = configParser.get('filters', 'page_size')
 
# Logging parameters
logFile = configParser.get('logging', 'logFile')
logger = logging.getLogger('topdeskAPI')
hdlr = logging.FileHandler(logFile)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.DEBUG)
 
# request token
def getToken(url,username,pw):
    requestToken = requests.get(url+'login/operator', auth=(username,pw))
 
    if requestToken.status_code != 200:
        logger.error('Problem retrieving token at ' + url)
    else:    
        token = requestToken.text
        auth = 'TOKEN id="'+token+'"'
        return auth
 
# get the operatorgroupid in order to filter incidentlist       
def getOperatorGroup(url,auth,filteroperator):    
    getOperatorGroupId = requests.get(url+'operatorgroups', headers={"Authorization" : auth, 'Accept': 'application/json'}, params = {"name":filteroperator})
    if getOperatorGroupId.status_code != 200:
        logger.error('Operatorgroup could not be found ' + url)
    else:
        oGId = getOperatorGroupId.json()
        operatorGroupId = oGId[0]['id']
        return operatorGroupId
 
# retrieve JSON array containing incidents that meet the given parameters
# only tickets created today are retrieved      
def getIncidentList(url,auth,status,pagesize,operatorgroup):
    creationdatestart = (datetime.datetime.now().strftime('%Y-%m-%d'))
    param1 = {"status":status,"page_size":pagesize,"completed":"false","operator_group":operatorgroup,"creation_date_start":creationdatestart}
    getList = requests.get(url+'incidents', headers={"Authorization" : auth, 'Accept': 'application/json'}, params = param1)
    jsonresponse = getList.text
 
    if getList.status_code == 204: # if there are no incidents, do nothing
        pass
    else:
        incidentList = json.loads(jsonresponse)
        return incidentList
 
# Get calltype in order to filter 
def getIncidentType(incident):
    incidentType = incident['callType']['name']
    externalNumber = incident['externalNumber']
    optionalField = incident['optionalFields2']['text4']
 
    if incidentType == "Incident" and externalNumber == "" and optionalField == "Standaard Platform Incident":  
        createIncident(incident) # Use function createIncident if callType = incident AND field Escalatie vanuit = Standaard Platform Incident
    elif incidentType == "RFI" and externalNumber == "" and optionalField == "Standaard Platform RFI":
        createRfi(incident)
    else:
        pass
     
def createIncident(incident):
    incidentNumber = (incident['number'])
    incidentId = (incident['id'])
    incidentId2 = incidentId.replace("-","")
    impact = incident['optionalFields1']['text4']
    urgency = incident['optionalFields1']['text5']
    subcategory = incident['subcategory']['name']
     
    briefDescription = incident['briefDescription']
    request = (incident['request'])
 
    personid = (incident['caller']['id'])
    logger.info('Incident '+incidentNumber+' gevonden')
    auth = getToken(urlSource,userSource,pwSource)
    personSourceUrl = urlSource+'persons/id/'+personid
    getPersonSource = requests.get(personSourceUrl, headers={"Authorization" : auth})
 
    personsource = (getPersonSource.json())
    personemail = (personsource['email'])
    personlastname = (personsource['surName'])
    personfirstname = (personsource['firstName'])
    auth2 = getToken(urlTarget,userTarget,pwTarget)
    personTargetUrl = urlTarget+'persons/'
    # get person ID from target database in order to link the person
    # this is based on the last name and first name, so they should be the same in source and target databases
    # I wanted to link persons based on email address, but it is not possible to filter personlist on email address in the current version of the API
    getPersonTarget = requests.get(personTargetUrl, headers={"Authorization" : auth2, 'Accept': 'application/json'}, params = {"firstname":personfirstname,"lastname":personlastname,"page_size":"1"})
    if getPersonTarget.status_code == 204:
        logger.error('Person not found: '+ personlastname +' '+ personTargetUrl)
    else:
        getPerson = getPersonTarget.text
        persons = json.loads(getPerson)
        for person in persons:
            personId = person['id']
    # Insert carriage returns in request field 
        reQuest = request.replace("\n","<br>")
        impactTarget = getId("impacts",impact,urlTarget,auth2)
        urgencyTarget = getId("urgencies",urgency,urlTarget,auth2)    
        categoryTarget = getId("categories",subcategory,urlTarget,auth2)
        entryTypeTarget = getId("entry_types","Koppeling",urlTarget,auth2)
        callTypeTarget = getId("call_types","Incident",urlTarget,auth2)
        if subcategory == "Centraal Aansluitpunt":
            operatorGroupId = getOperatorGroup(urlTarget,auth2,operatorGroupTarget1)
        elif subcategory == "Standaard Platform":
            operatorGroupId = getOperatorGroup(urlTarget,auth2,operatorGroupTarget2)
        else:
            operatorGroupId = getOperatorGroup(urlTarget,auth2,operatorGroupTarget)
                       
    # compose JSON to post the incident 
        incidentJson = {"operatorGroup" : {"id": operatorGroupId}, "briefDescription" : briefDescription, "entryType" : {"id" : entryTypeTarget},"callType" : {"id" : callTypeTarget}, "category" : {"id" : categoryTarget}, "request" : reQuest, "caller" : {"id" : personId}, "externalNumber" : incidentNumber, "impact" : {"id": impactTarget}, "urgency" : {"id": urgencyTarget} }
        incidentTargetUrl = urlTarget +'incidents'
        postIncident = requests.post(incidentTargetUrl, headers={"Authorization": auth2, 'Accept': 'application/json'}, data = json.dumps(incidentJson))
        jsonPostIncident = (postIncident.json())
        externalNumberSource = (jsonPostIncident['number'])
        incidentIdSource = (jsonPostIncident['id'])  
        logger.info('Incident aangemaakt: '+ externalNumberSource +' '+ urlTarget)
    # update external number using HTTP-request, API did not work because of bug  
        urlUpdateExternalNumber = 'http://localhost/tas/secure/incident?action=edit&unid='+ incidentId2 +'&field0=externnummer&value0='+ externalNumberSource +'&j_username='+ userSource +'&j_password='+ pwSource +'&save=true&validate=false'
        updateExternalNumber = requests.post(urlUpdateExternalNumber)
        cUploadPath = uploadedFilesLocation+'\\incident\\'+incidentNumber+'\\'
         
    # upload attached files
        contentsUploadPath = os.listdir(cUploadPath)
        for file in contentsUploadPath:
            filename = cUploadPath + file
        
            fileName = {'file': open(filename, 'rb')}
            uploadFileUrl = urlTarget +'incidents/id/'+ incidentIdSource +'/attachments'
            uploadFile = requests.post(uploadFileUrl, headers={"Authorization": auth2, 'Accept': 'application/json'}, files = fileName)
 
             
# temporary solution:
def createRfi(incident):
    pass
 
# createRFI is not yet in use  
# switch function above to the function below           
           
def createRfi2(incident):
    incidentNumber = (incident['number'])
    incidentId = (incident['id'])
    incidentId2 = incidentId.replace("-","")
    subcategory = incident['subcategory']['name']
    briefDescription = incident['briefDescription']
    request = (incident['request'])
    personid = (incident['caller']['id'])
    logger.info('RFI '+incidentNumber+' gevonden')
    auth = getToken(urlSource,userSource,pwSource)
    personSourceUrl = urlSource+'persons/id/'+personid
    getPersonSource = requests.get(personSourceUrl, headers={"Authorization" : auth})
    personsource = (getPersonSource.json())
    personemail = (personsource['email'])
    personlastname = (personsource['surName'])
    personfirstname = (personsource['firstName'])
    auth2 = getToken(urlTarget,userTarget,pwTarget)
    personTargetUrl = urlTarget+'persons/'
    # get person ID from target database in order to link the person
    # this is based on the last name and first name, so they should be the same in source and target databases
    # I wanted to link persons based on email address, but it is impossible to filter personlist on email address in the current version of the API
    getPersonTarget = requests.get(personTargetUrl, headers={"Authorization" : auth2, 'Accept': 'application/json'}, params = {"firstname":personfirstname,"lastname":personlastname,"page_size":"1"})
    if getPersonTarget.status_code == 204:
        logger.error('Person not found: '+ personlastname +' '+ personTargetUrl)
    else:
        getPerson = getPersonTarget.text
        persons = json.loads(getPerson)
        for person in persons:
            personId = person['id']
    # Insert carriage returns in request field 
        reQuest = request.replace("\n","<br>")
          
        categoryTarget = getId("categories",subcategory,urlTarget,auth2)
        entryTypeTarget = getId("entry_types","Koppeling",urlTarget,auth2)
        callTypeTarget = getId("call_types","Request for Information (RFI)",urlTarget,auth2)
        operatorGroupId = getOperatorGroup(urlTarget,auth2,operatorGroupTarget)
    # compose JSON to post the incident 
        incidentJson = {"operatorGroup" : {"id": operatorGroupId}, "briefDescription" : briefDescription, "entryType" : {"id" : entryTypeTarget},"callType" : {"id" : callTypeTarget}, "category" : {"id" : categoryTarget}, "request" : reQuest, "caller" : {"id" : personId}, "externalNumber" : incidentNumber }
        incidentTargetUrl = urlTarget +'incidents'
        postIncident = requests.post(incidentTargetUrl, headers={"Authorization": auth2, 'Accept': 'application/json'}, data = json.dumps(incidentJson))
        jsonPostIncident = (postIncident.json())
        externalNumberSource = (jsonPostIncident['number'])
        incidentIdSource = (jsonPostIncident['id'])  
        logger.info('RFI aangemaakt: '+ externalNumberSource +' '+ urlTarget)
    # update external number using HTTP-request, API did not work because of error  
        urlUpdateExternalNumber = 'http://localhost/tas/secure/incident?action=edit&unid='+ incidentId2 +'&field0=externnummer&value0='+ externalNumberSource +'&j_username='+ userSource +'&j_password='+ pwSource +'&save=true&validate=false'
        updateExternalNumber = requests.post(urlUpdateExternalNumber)
        cUploadPath = uploadedFilesLocation+'\\incident\\'+incidentNumber+'\\'
         
    # upload attached files
        contentsUploadPath = os.listdir(cUploadPath)
        for file in contentsUploadPath:
            filename = cUploadPath + file
        
            fileName = {'file': open(filename, 'rb')}
            uploadFileUrl = urlTarget +'incidents/id/'+ incidentIdSource +'/attachments'
            uploadFile = requests.post(uploadFileUrl, headers={"Authorization": auth2, 'Accept': 'application/json'}, files = fileName)
 
   
 
# get UIDs of searchlist values (parameters are: name of searchlist, name of value in searchlist, url of TOPdesk instance, auth header) 
def getId(searchList,value,url,auth2):
    urlList = urlTarget+'incidents/'+searchList
    getListOfValues = requests.get(urlList, headers={"Authorization": auth2, 'Accept': 'application/json'})
    jsonGetListOfValues = (getListOfValues.json())
    for item in jsonGetListOfValues:
        if item['name'] == value:
            ValueId = item['id']
            return(ValueId)
     
 
# get incident types of tickets in list and subsequently submit tickets in target database depending on incident type
def submitIncidents(incidentlist):
    if not incidentlist:
        pass
    else:
        for incident in incidentlist:
            incidentType = getIncidentType(incident)
 
# use function getToken to request a token    
auth = getToken(urlSource,userSource,pwSource)
 
# use function getOperatorGroup in order to get the operatorgroupid
operator = getOperatorGroup(urlSource,auth,operatorGroup)
 
# use function getIncidentList, retrieve JSON array containing all incidents that meet the given parameters
incidentList = getIncidentList(urlSource,auth,status,pageSize,operator)
 
# use function submitIncidents to create incidents based on the incidentList  
submitIncidents(incidentList)
