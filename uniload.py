#!/usr/bin/env python

import urllib2, os, re, ConfigParser, sys
from moodle import openCourse
from configutil import getIndexedOptions
from fileupdater import safe_getResponse, File

CONFFILES = [os.path.expanduser(p) for p in ["~/.uniload.conf",
                                             "~/.uniloadcred.conf"]]

def main(argv):
    opt = "".join([o[1:] for o in argv if o.startswith("-")])
    config = getConfig()
    options = getOptions()
    config.set("uniload", "test", str(options.test))
    if options.test:
        print "*** TESTMODUS (Keine Filesystemoperationen) ***"
    uniload(config)
    moodle(config)

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
    dummy = safe_getResponse(casUrl + '?service=' + casService, postData)
    dummy = None
    
    # Use the Service
    url = 'http://moodle.uni-duisburg-essen.de/index.php'
    # verueckt, erst muss ich einen kurs aufrufen um in der hauptseite eingeloggt zu sein
    dummy = safe_getResponse("http://moodle.uni-duisburg-essen.de/course/view.php?id=2064")
    
    html = safe_getResponse(url).read()
        
    for section in [s for s in config.sections() if s.startswith("moodle-module ")]:
        module = section[15:-1]
        page = config.get(section, "page")
        overrides = getIndexedOptions(config, section, ['regexp', 'remote', 'folder'])
        openCourse(config, page, module, overrides)
                
def getConfig():
    config = ConfigParser.ConfigParser()
    succed = config.read(CONFFILES)
    return config

def getOptions(argv):
    parser = optparse.OptionParser()
    parser.add_option("-t", "--test", action="store_true", dest="test",
                      default=False)
    return parser.parse_args(argv)[0]

def load(config, section):
    module = section[14:-1]
    page = config.get(section, "page")
    content = safe_getResponse(page).read()
    for item in getIndexedOptions(config, section, ["regexp", "folder"]):
        localdir = os.path.join(module, item['folder'])
        loaditem(config, localdir, os.path.dirname(page), item['regexp'], content)

def loaditem(config, localdir, webdir, regexp, content):
    for f in re.findall(regexp, content)]
        remote = "/".join([webdir, f])
        local = "/".join([localdir, os.path.basename(f)])
        test = config.getboolean("uniload", "test")
        File(remote, local, test=test).update()

if __name__ == "__main__":
    main(sys.argv[1:])
