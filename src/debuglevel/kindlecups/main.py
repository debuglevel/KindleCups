#!/usr/bin/python
# -*- coding: utf-8 -*-

# Imports
import base64
import sys
import os
import subprocess
import datetime
import magic
import smtplib
from email.mime.multipart import MIMEMultipart
from email import Encoders
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
import ConfigParser
import pprint

# Configuration

class Config:
    class SMTP:
        def __init__(self, config):
            self.user = config.get("SMTP", "user")
            self.password = base64.b64decode(config.get("SMTP", "password"))
            self.server = config.get("SMTP", "server")
    
    class Mail:
        def __init__(self, config):
            self.fromaddress = config.get("Mail", "from")
            self.to = config.get("Mail", "to")
            self.cc = config.get("Mail", "cc")
    
    class Tools:
        def __init__(self, config):
            self.ps2pdf = config.get("Tools", "ps2pdf")
    
    def __init__(self, user):
        userDirectory = "~"+user;
        self._config = ConfigParser.RawConfigParser()
        self._config.read(os.path.expanduser(userDirectory+"/etc/KindleCups.conf"))
        self.SMTP = Config.SMTP(self._config)
        self.Mail = Config.Mail(self._config)
        self.Tools = Config.Tools(self._config)



# Program

# print cups-readable information about this backend
def printCupsInformation():
    print 'network kindlecups:/noFurtherArguments "Unknown" "KindleCups"'
    sys.exit()

# print how to use this script
def printUsage():
    print >> sys.stderr, "USAGE: "+sys.argv[0]+" job-id user title copies options [file]"
    sys.exit()

# get arguments passed by
def getArguments():
    job = sys.argv[1]
    user = sys.argv[2]
    title = sys.argv[3]
    #title = title.decode('UTF-8').encode('ISO-8859-1')  # title is in utf-8; encode it in iso-8859-1 for simplicity    # TODO: doesnt seem to work that good
    copies = sys.argv[4]
    options = sys.argv[5]
    filename = sys.argv[6]
    return user, filename, job, title, copies, options

# get some environment variables
def getEnvironmentVariables():
    # try to fetch the Environment Variable "DEVICE_URI"
    # TODO: fetching environment variable does not seem to work 
    # CAVEAT: even if DeviceURI is configured as kindlecups://john.doe@free.kindle.com, CUPS sets DEVICE_URI=kindlecups://free.kindle.com
    #try:
    #    deviceURI = os.environ["DEVICE_URI"]
    #except KeyError:
    #    deviceURI = ""
    return None

# get input data from file or stdin
def getInputData(filename):
    if filename:
        inputType = "file"
    else:
        filename = sys.stdin
        inputType = "stdin"
        
    filedata = open(filename, "rb").read()
    return filename, inputType, filedata

# get MimeType of file
def getMimeType(filename):
    # get mimetype of the input
    # (outdated way of using magic)
    m = magic.open(magic.MAGIC_MIME)
    m.load()
    mimetype = m.file(filename) # might terribly crash if input via stdin 
    
    # this would be the appropriate way to use magic. Unfortunately, at least Ubuntu 11.04 doesn't ship a current version of python-magic
    # TODO: untested 
    #mime = magic.Magic(mime=True)
    #mime.from_buffer(filedata)
    
    return mimetype
 
# process input data (kind of dummy function for now)
def processInput(filedata, mimetype, config):
    if "pdf" in mimetype:
        fileextension = ".pdf"
    elif "postscript" in mimetype:
        # convert postscript to pdf
        p = subprocess.Popen([config.Tools.ps2pdf + " -sOutputFile=%stdout% -"], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(input=filedata)
        filedata = stdout
        fileextension = ".pdf"
        if p.returncode != 0:
            print >> sys.stderr, 'An error occured during conversion from ps to pdf:'
            print >> sys.stderr, stdout + '\n' + stderr
            sys.exit(1)
        
    return filedata, fileextension

# create mail container
def createMailContainer(config):
    msg = MIMEMultipart()
    msg['Subject'] = 'Convert'
    msg['From'] = config.Mail.fromaddress
    msg['To'] = config.Mail.to
    msg['Cc'] = config.Mail.cc
    msg['Date'] = formatdate(localtime=True)
    return msg

# add mail text
def addMailText(msg, user, filename, job, title, copies, options, inputType, mimetype):
    text = """
DateTime: %s
Job: %s
User: %s
Title: %s
Copies: %s
Options: %s
Filename: %s
inputType: %s
input-MimeType: %s
""" % (str(datetime.datetime.now()), job, user, title, copies, options, filename, inputType, mimetype)
    msg.attach(MIMEText(text, "plain", "utf-8"))

# add mail attachment
def addMailAttachment(msg, title, filedata, fileextension):
    part = MIMEBase('application', "octet-stream")
    part.set_payload(filedata)
    Encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="%s%s"' % (title, fileextension))
    msg.attach(part)

# send mail
def sendMail(msg, config):
    smtp = smtplib.SMTP(config.SMTP.server)
    smtp.login(config.SMTP.user, config.SMTP.password) #smtp.sendmail(config.Mail.fromaddress, COMMASPACE.join([config.Mail.to, config.Mail.cc]), msg.as_string())
    smtp.sendmail(config.Mail.fromaddress, [config.Mail.to, config.Mail.cc], msg.as_string())
    smtp.quit()

def main():
    # no arguments passed:
    # CUPS want to know some information about this printer
    if len(sys.argv) == 1:
        printCupsInformation()
        
    # not enough arguments passed:
    # print some information how to use this script
    if len(sys.argv) != 6 and len(sys.argv) != 7:
        printUsage()
    
    # get arguments passed by
    user, filename, job, title, copies, options = getArguments()
    
    # get environment variables
    unused = getEnvironmentVariables()
        
    # initialize configuration
    config = Config(user)
    
    # get input data
    filename, inputType, filedata = getInputData(filename)
    
    # get mimetype of input
    mimetype = getMimeType(filename)
    
    # process input data (kind of dummy function for now)
    filedata, fileextension = processInput(filedata, mimetype, config)
    
    # create mail container
    msg = createMailContainer(config)
    
    # add text to mail
    addMailText(msg, user, filename, job, title, copies, options, inputType, mimetype)
    
    # add attachment to mail
    addMailAttachment(msg, title, filedata, fileextension)
    
    # Send mail
    sendMail(msg, config)

if __name__ == "__main__":
    sys.exit(main())