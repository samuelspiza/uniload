#!/usr/bin/env python

import os, re, optparse, ConfigParser, sys
from moodle import openCourse
from configutil import getIndexedOptions
from fileupdater import File, absUrl, safe_getResponse

CONFFILES = []
CONFFILES.append(os.path.expanduser("~/.uniload.conf"))
CONFFILES.append(os.path.expanduser("~/.uniload-cred.conf"))
CONFFILES.append(os.path.expanduser("uniload.conf"))
CONFFILES.append(os.path.expanduser("uniload-cred.conf"))

def main(argv):
    config = ConfigParser.ConfigParser()
    config.read(CONFFILES)
    options = getOptions(argv)
    config.set("uniload", "test", str(options.test))
    if options.test:
        print "*** TESTMODUS (Keine Filesystemoperationen) ***"
    uniload(config)
    moodle(config)
    return 0

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
    data = safe_getResponse(casUrl).read()
    rawstr = '<input type="hidden" name="lt" value="([A-Za-z0-9_\-]*)" />'
    token = re.search(rawstr, data, re.MULTILINE).group(1)
    
    # Login
    postData = {'username': user, 'password': password, 'lt': token, '_eventId': 'submit'}
    safe_getResponse(casUrl + '?service=' + casService, postData)
    
    # Use the Service
    url = 'http://moodle.uni-duisburg-essen.de/index.php'
    # verueckt, erst muss ich einen kurs aufrufen um in der hauptseite eingeloggt zu sein
    safe_getResponse("http://moodle.uni-duisburg-essen.de/course/view.php?id=2064")
    
    safe_getResponse(url).read()
        
    for section in [s for s in config.sections() if s.startswith("moodle-module ")]:
        module = section[15:-1]
        page = config.get(section, "page")
        overrides = getIndexedOptions(config, section, ['regexp', 'remote', 'folder'])
        openCourse(config, page, module, overrides)
                
def getOptions(argv):
    parser = optparse.OptionParser()
    parser.add_option("-t", "--test",
                      action="store_true", dest="test", default=False)
    return parser.parse_args(argv)[0]

def load(config, section):
    module = section[14:-1]
    page = config.get(section, "page")
    content = safe_getResponse(page).read()
    for item in getIndexedOptions(config, section, ["regexp", "folder"]):
        localdir = os.path.join(module, item['folder'])
        loaditem(config, localdir, page, item['regexp'], content)

def loaditem(config, localdir, page, regexp, content):
    for f in re.findall(regexp, content):
        remote = absUrl(page, f)
        local = "/".join([localdir, os.path.basename(f)])
        test = config.getboolean("uniload", "test")
        File(remote, local, test=test).update()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
