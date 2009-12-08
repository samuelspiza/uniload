#!/usr/bin/env python

import urllib2, os, re, ConfigParser, sys

def uniload():
    config = getConfig()
    os.chdir(os.path.expanduser(config.get("uniload", "path")))
    for section in [s for s in config.sections() if s.startswith("uniload-site ")]:
        load(config, section)

def getConfig():
    conffile = os.path.expanduser("~/.uniload.conf")
    config = ConfigParser.ConfigParser()
    succed = config.read([conffile])
    ok = getConfigSites(config, succed)
    ok = getConfigPath(config, succed) and ok
    if not ok:
        with open(conffile, "w") as configfile:
            config.write(configfile)
        print "Please modify '" + conffile + "' according to your setup."
        sys.exit()
    return config

def getConfigSites(config, succed):
    if 0 < len(succed):
        for section in config.sections():
            if section.startswith("uniload-site ") and section != 'uniload-site "Example"':
                return True
    config.add_section('uniload-site "Example"')
    config.set('uniload-site "Example"', "path", "http://www.example.com/")
    config.set('uniload-site "Example"', "page", "http://www.example.com/site.htm")
    config.set('uniload-site "Example"', "example/exercise", r"exercise/exercise_[0-9]{2}\.pdf")
    return False

def getConfigPath(config, succed):
    if 0 < len(succed) and config.has_section("uniload"):
        return True
    config.add_section("uniload")
    config.set("uniload", "path", "~/dropbox/uni/")
    return False

def load(config, section):
    content = urllib2.urlopen(config.get(section, "page")).read()
    for item in [i for i in config.items(section) if i[0] != "page" and i[0] != "path"]:
        loaditem(item, config.get(section, "path"), content)

def loaditem(item, path, content):
    folder = item[0]
    if not os.path.exists(folder):
        os.makedirs(folder)
    files = [File(f, path, folder) for f in re.findall(item[1], content)]
    print [f.__str__() for f in files]
    for f in files:
        if f.isNew() or f.hasChanged():
            f.download()

class File:
    def __init__(self, name, webdir, localdir):
        self.name = os.path.basename(name)
        self.web = webdir + name
        self.local = os.path.join(localdir,self.name)
        self.oldlen = None
        self.newlen = None
        self.newcontent = None
        self.response = None

    def isNew(self):
        return not os.path.exists(self.local)

    def hasChanged(self):
        newlen = self.getNewLen()
        if newlen is not None:
            return self.getOldLen() != newlen
        else:
            return False

    def getOldLen(self):
        if self.oldlen is None:
            file = open(self.local, "r")
            self.oldlen = len(file.read())
            file.close()
        return self.oldlen

    def getNewLen(self):
        if self.newlen is None:
            response = self.getResponse()
            if response is None:
                return None
            elif response.info().get("Content-Length") is None:
                self.newlen = len(self.getNewContent())
            else:
                self.newlen = int(response.info().get("Content-Length"))
        return self.newlen

    def getNewContent(self):
        if self.newcontent is None and self.getResponse() is not None:
            self.newcontent = self.response.read()
        return self.newcontent

    def getResponse(self):
        if self.response is None:
            self.response = getResponse(self.web, None)
        return self.response
      
    def download(self):
        newcontent = self.getNewContent()
        if newcontent is not None:
            file = open(self.local, "w")
            file.write(newcontent)
            file.close()

    def __str__(self):
        return self.name

def getResponse(url, postData = None):
    header = { 'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)',
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

if __name__ == "__main__":
    uniload()
