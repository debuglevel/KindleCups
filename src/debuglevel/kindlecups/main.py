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
    
    def __init__(self):
        self._config = ConfigParser.RawConfigParser()
        self._config.read(os.path.expanduser("~marc/etc/KindleCups.conf"))
        self.SMTP = Config.SMTP(self._config)
        self.Mail = Config.Mail(self._config)
        self.Tools = Config.Tools(self._config)



# Program

# no arguments passed:
# CUPS want to know some information about this printer
if len(sys.argv) == 1:
    print 'network kindlecups "Unknown" "KindleCups"'
    sys.exit()
    
# not enough arguments passed:
# print some information how to use this script
if len(sys.argv) != 6 and len(sys.argv) != 7:
    print >> sys.stderr, "USAGE: kindlecups.py job-id user title copies options [file]"
    sys.exit()

# assign arguments
job = sys.argv[1]
user = sys.argv[2]
title = sys.argv[3]
#title = title.decode('UTF-8').encode('ISO-8859-1')  # title is in utf-8; encode it in iso-8859-1 for simplicity    # TODO: doesnt seem to work that good
copies = sys.argv[4]
options = sys.argv[5]
filename = sys.argv[6]


# try to fetch the Environment Variable "DEVICE_URI"
# TODO: does not seem to work 
try:
    deviceURI = os.environ["DEVICE_URI"]
except KeyError:
    deviceURI = ""
    
# initialize configuration
config = Config()

# read the input from file or stdin
if filename:
    inputType = "file"
else:
    filename = sys.stdin
    inputType = "stdin"

filedata = open(filename, "rb").read();

# get mimetype of the input
# outdated way of using magic
m = magic.open(magic.MAGIC_MIME)
m.load()
mimetype = m.file(filename) # might terribly crash if input via stdin 

# this would be the appropriate way to use magic. Unfortunately, at least Ubuntu 11.04 doesn't ship a current version of python-magic
# TODO: untested 
#mime = magic.Magic(mime=True)
#mime.from_buffer(filedata)


if "pdf" in mimetype:
    fileextension = ".pdf"
elif "postscript" in mimetype:
    # convert postscript to pdf
    # TODO: untested
    p = subprocess.Popen(["$ps2pdf $tmpfilename /tmp/kindle-printer-$job.tmp.pdf"], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tmpfilename = "/tmp/kindle-printer-$job.tmp.pdf"
    fileextension = ".pdf"
    print "I am in postscript convert mode. Untested ugly code"


# Create email container
msg = MIMEMultipart()
msg['Subject'] = 'Convert'
msg['From'] = config.Mail.fromaddress
msg['To'] = config.Mail.to
msg['Cc'] = config.Mail.cc
msg['Date'] = formatdate(localtime=True)

# Create email text
text = """
DateTime: %s
Job: %s
User: %s
Title: %s
Copies: %s
Options: %s
Filename: %s
inputType: %s
deviceURI: %s
""" % (str(datetime.datetime.now()), job, user, title, copies, options, filename, inputType, deviceURI)

msg.attach(MIMEText(text, "plain", "utf-8"))

# Create email attachment
part = MIMEBase('application', "octet-stream")
part.set_payload(filedata)
Encoders.encode_base64(part)
part.add_header('Content-Disposition', 'attachment; filename="%s%s"' % (title, fileextension))
msg.attach(part)

# Send email via SMTP server
smtp = smtplib.SMTP(config.SMTP.server)
smtp.login(config.SMTP.user, config.SMTP.password)
#smtp.sendmail(config.Mail.fromaddress, COMMASPACE.join([config.Mail.to, config.Mail.cc]), msg.as_string())
smtp.sendmail(config.Mail.fromaddress, [config.Mail.to, config.Mail.cc], msg.as_string())
smtp.quit()