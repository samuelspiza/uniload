#!/usr/bin/env python

import urllib2, os, re, ConfigParser, sys
from moodle import openCourse
from configutil import getIndexedOptions
from fileupdater import getResponse, File

CONFFILES = [os.path.expanduser(p) for p in ["~/.uniload.conf", "~/.uniloadcred.conf"]]

def uniload(config):
    os.chdir(os.path.expanduser(config.get("uniload", "path")))
    for section in [s for s in config.sections() if s.startswith("uniload-site ")]:
        print "Kurs:", section[14:-1]
        load(config, section)

def moodle(config):
    os.chdir(os.path.expanduser(config.get("uniload", "path")))
    
    # Benutzerdaten
    password = config.get("moodle-credentials", "password") # PASSWORD
    user = config.get("moodle-credentials", "user")
    # CAS Daten
    casUrl = 'https://cas.uni-duisburg-essen.de/cas/login'
    casService = "http://moodle.uni-duisburg-essen.de/login/index.php?authCAS=CAS"
        
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
        
    for section in [s for s in config.sections() if s.startswith("moodle-module ")]:
        module = section[15:-1]
        page = config.get(section, "page")
        overrides = getIndexedOptions(config, section, ['regexp', 'remote', 'folder'])
        openCourse(config, page, module, overrides)
                
def getConfig():
    config = ConfigParser.ConfigParser()
    succed = config.read(CONFFILES)
    return config

def load(config, section):
    module = section[14:-1]
    page = config.get(section, "page")
    content = urllib2.urlopen(page).read()
    for item in getIndexedOptions(config, section, ["regexp", "folder"]):
        localdir = os.path.join(module, item['folder'])
        loaditem(config, localdir, os.path.dirname(page), item['regexp'], content)

def loaditem(config, localdir, webdir, regexp, content):
    files = [File("/".join([webdir, f]),
                  "/".join([localdir, os.path.basename(f)]),
                  test=config.getboolean("uniload", "test"))
             for f in re.findall(regexp, content)]

if __name__ == "__main__":
    opt = "".join([o[1:] for o in sys.argv if o.startswith("-")])
    config = getConfig()
    test = True
    # test = (-1 < opt.find('t'))
    config.set("uniload", "test", str(test))
    if test:
        print "*** TESTMODUS (Keine Filesystemoperationen) ***"
    uniload(config)
    moodle(config)
