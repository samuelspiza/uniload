#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib, urllib2, re, cookielib, os, sys, ConfigParser
from BeautifulSoup import BeautifulSoup
from threading import Thread
import uniload


def getResponse(url, postData = None):
    header = { 'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0',
                'Accept-Language': 'de',
                'Accept-Encoding': 'utf-8'                                   
            } 
    if(postData is not None):
        postData = urllib.urlencode(postData)
    req = urllib2.Request(url, postData, header)
    try:
        return urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        print 'Error Code:', e.code
        return None

class Course(Thread):
    def __init__ (self, url, CourseName):
        Thread.__init__(self)
        self.url = url
        self.CourseName = CourseName

    def run(self):
        self.newFiles = []
        if not os.path.exists(self.CourseName):
            os.mkdir(self.CourseName)
        soup = BeautifulSoup(getResponse(self.url).read())
        links = soup.findAll(attrs={'href' : re.compile("resource/view.php")})
        for link in links:
            if not(link.span is None):
                new = self.download(link['href'], link.span.next, self.CourseName)
                for n in new:
                    self.newFiles.append(n)
    
    def download(self, url, folder, CourseName):
        print url
        newFiles, savedFile = [], []
        response = getResponse(url)
        if(response is not None):
            # Direkter Download
            if(response.info().get("Content-Type").find('audio/x-pn-realaudio') == 0):
                d="" #print "Real Player Moodle Page"
            elif(response.info().get("Content-Type").find('text/html') != 0):
                fileUrl = response.geturl()
                savedFile = self.saveFile(fileUrl)
                if(len(savedFile) > 0):
                    newFiles.append(savedFile)
            # Moodle indirekter Download
            else:
                data = response.read()
                soup = BeautifulSoup(data)
                # entweder frames oder files und dirs
                frames = soup.findAll(attrs={'src' : re.compile("http://moodle.uni-duisburg-essen.de/file.php")})
                files = soup.findAll(attrs={'href' : re.compile("http://moodle.uni-duisburg-essen.de/file.php")})
                dirs = soup.findAll(attrs={'href' : re.compile("subdir")})
    
                folder = re.sub(u"[^a-zA-Z0-9_()äÄöÖüÜ ]", "", folder).strip()
                for f in files:
                    savedFile = self.saveFile(f['href'], folder)
                    if(len(savedFile) > 0):
                        newFiles.append(savedFile)
                # Folders
                for d in dirs:
                    folder = os.path.basename(d['href'])                
                    href = "http://moodle.uni-duisburg-essen.de/mod/resource/" + d['href']
                    self.download(href, folder, CourseName)
                # Frame
                for f in frames:
                    savedFile = self.saveFile(f['src'])
                    if(len(savedFile) > 0):
                        newFiles.append(savedFile)
        return newFiles
    
    def saveFile(self, url, folder = ""):
        if(folder != ""):
            folder = "/" + folder
        isFileNew = False
        fileChanged = False
        newPath = "/".join(url.split("/")[5:])
        #Overrides
        #config = getConfig()
        ov = []
        for section in [s for s in config.sections() if s.startswith("moodle-module ")]:
            ov.append((section[15:-1],dict(config.items(section))))
        override = dict(ov)
        print newPath
        if os.path.dirname(newPath).lower() not in override[self.CourseName]:
            fullFileName = os.path.join(self.CourseName, "stuff", newPath)
        else:
            fullFileName = os.path.join(self.CourseName, override[self.CourseName][os.path.dirname(newPath).lower()], os.path.basename(newPath))
        fullFileName = re.sub(r"\?forcedownload=1", "", fullFileName)
        if not os.path.exists(os.path.dirname(fullFileName)):
            os.makedirs(os.path.dirname(fullFileName))
        response = getResponse(url)
        if(os.path.isfile(fullFileName)):
            with open(fullFileName, 'r') as f:
                read_data = f.read()
                f.closed
            check_md5 = False
            # if no Content-Length in header
            if(response.info().get("Content-Length") is None or check_md5 == True):
                data = response.read()
                m1 = hashlib.md5()
                m2 = hashlib.md5()
                m1.update(data)
                m2.update(read_data)
                #print "Lokal:", m1.hexdigest(), "Online:", m2.hexdigest()
                if (m1.hexdigest() == m2.hexdigest()):
                    return []
                else:
                    isFileNew = True
                    fileChanged = True
            else:
                #print filename, "check:", "Length"
                length = response.info().get("Content-Length")
                if (int(length) == len(read_data)):
                    return []
                else:
                    isFileNew = True
                    fileChanged = True
        else:
            isFileNew = True
        if(isFileNew == True):
            data = response.read()
            with open(fullFileName, "w") as f:
                f.write(data)
                f.close()
            return [fullFileName, url, fileChanged]
        else:
            return []
        
def finish(newFiles):
    """
    Moved from Monitor class. Sends an email containing all new files.
    """
    pass

def getConfig():
    conffile = os.path.expanduser("~/.uniload.conf")
    config = ConfigParser.ConfigParser()
    succed = config.read([conffile])
    ok = getConfigModules(config, succed)
    ok = getConfigCredentials(config, succed) and ok
    ok = getConfigPath(config, succed) and ok
    if not ok:
        with open(conffile, "w") as configfile:
            config.write(configfile)
        print "Please modify '" + conffile + "' according to your setup."
        sys.exit()
    return config

def getConfigModules(config, succed):
    if 0 < len(succed):
        for section in config.sections():
            if section.startswith("moodle-module ") and section != 'moodle-module "Example"':
                return True
    config.add_section('moodle-module "Example"')
    config.set('moodle-module "Example"', "exercise", "uebung")
    return False

def getConfigCredentials(config, succed):
    if 0 < len(succed) and config.has_section("moodle-credentials"):
        return True
    config.add_section("moodle-credentials")
    config.set("moodle-credentials", "password", "abcd1234")
    config.set("moodle-credentials", "user", "name")
    return False

def getConfigPath(config, succed):
    if 0 < len(succed) and config.has_section("uniload"):
        return True
    config.add_section("uniload")
    config.set("uniload", "path", "~/dropbox/uni/")
    return False

uniload.uniload()

config = getConfig()
os.chdir(os.path.expanduser(config.get("uniload", "path")))
#os.chdir(os.path.expanduser("~/workspace/python/uniload"))
print os.getcwd()
#
#
# Benutzerdaten
password = config.get("moodle-credentials", "password") # PASSWORD
user = config.get("moodle-credentials", "user")
# CAS Daten
casUrl = 'https://cas.uni-duisburg-essen.de/cas/login'
casService = "http://moodle.uni-duisburg-essen.de/login/index.php?authCAS=CAS"

# Setup
jar = cookielib.CookieJar()
handler = urllib2.HTTPCookieProcessor(jar)
opener = urllib2.build_opener(handler)
urllib2.install_opener(opener)
    
# Get token
data = getResponse(casUrl).read()
rawstr = '<input type="hidden" name="lt" value="([A-Za-z0-9_\-]*)" />'
token = re.search(rawstr, data, re.MULTILINE).group(1)

# Login
postData = {'username': user, 'password': password, 'lt': token, '_eventId': 'submit'}
dummy = getResponse(casUrl + '?service=' + casService, postData)
dummy = None

# Use the Service
url = 'http://moodle.uni-duisburg-essen.de/index.php'
# verueckt, erst muss ich einen kurs aufrufen um in der hauptseite eingeloggt zu sein
dummy = getResponse("http://moodle.uni-duisburg-essen.de/course/view.php?id=2064")

html = getResponse(url).read()
#soup = BeautifulSoup(html)
# Nicht allzu sauber mit den regexp
#links = soup.findAll(attrs={'href' : re.compile("course/view.php"), 'title' : re.compile("Hier klicken"), })

courses = []

newFiles = {}

#for link in links:
#    CourseName = link.string.replace("&amp;", "&")
#    CourseName = re.sub(u"[^a-zA-Z0-9_() ]", "", CourseName).strip()
    #print u"Kurs: " + CourseName
current = Course("http://moodle.uni-duisburg-essen.de/course/view.php?id=219", "rem1")
courses.append(current)
current.start()
current = Course("http://moodle.uni-duisburg-essen.de/course/view.php?id=1965", "dsd")
courses.append(current)
current.start()
current = Course("http://moodle.uni-duisburg-essen.de/course/view.php?id=1120", "bwl")
courses.append(current)
current.start()
    
for course in courses:
    course.join()
    new_files_of_course = course.newFiles
    if new_files_of_course:
        newFiles[course.CourseName] = course.newFiles
    
