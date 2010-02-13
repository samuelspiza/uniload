#!/usr/bin/env python

import urllib2, os, re, ConfigParser, sys

CONFFILE = os.path.expanduser("~/.uniload.conf")

def uniload():
    config = getConfig()
    os.chdir(os.path.expanduser(config.get("uniload", "path")))
    for section in [s for s in config.sections() if s.startswith("uniload-site ")]:
        load(config, section)

def getConfig():
    config = ConfigParser.ConfigParser()
    succed = config.read([CONFFILE])
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
    config.set('uniload-site "Example"', "00folder", "uebung")
    config.set('uniload-site "Example"', "00regexp", r"exercise/exercise_[0-9]{2}\.pdf")
    config.set('uniload-site "Example"', "page", "http://www.example.com/site.htm")
    return False

def getConfigPath(config, succed):
    if 0 < len(succed) and config.has_section("uniload"):
        return True
    config.add_section("uniload")
    config.set("uniload", "path", "~/dropbox/uni/")
    return False

def load(config, section):
    module = section[14:-1]
    page = config.get(section, "page")
    content = urllib2.urlopen(page).read()
    for item in getIndexedOptions(config, section, ["regexp", "folder"]):
        localdir = os.path.join(module, item['folder'])
        loaditem(localdir, os.path.dirname(page), item['regexp'], content)

def loaditem(localdir, webdir, regexp, content):
    # files = [File(f, webdir, localdir).update(test=False) for f in re.findall(regexp, content)]
    files = [File(f, webdir, localdir).update(test=True) for f in re.findall(regexp, content)]

def getIndexedOptions(config, section, values):
    arr = []
    i = 0
    temp = getOptionsById(config, section, values, i)
    while 0 < len(temp):
        arr.append(temp)
        i = i + 1
        temp = getOptionsById(config, section, values, i)
    return arr

def getOptionsById(config, section, values, i):
    values = [v.format(i) for v in ["{0:02}" + v for v in values]]
    return dict([(v[2:], config.get(section, v))
                 for v in values if config.has_option(section, v)])

class File:
    def __init__(self, name, webdir, localdir):
        self.name = os.path.basename(name)
        self.web = os.path.join(webdir, name)
        self.local = os.path.join(localdir,self.name)
        self.oldlen = None
        self.newlen = None
        self.newcontent = None
        self.response = None
        self.isnew = None
        self.haschanged = None

    def update(self, test=False):
        if self.check():
            self.download(test)
    
    def check(self):
        return self.isNew() or self.hasChanged()

    def isNew(self):
        if self.isnew is None:
            self.isnew = not os.path.exists(self.local)
        return self.isnew

    def hasChanged(self):
        if self.haschanged is None:
            if self.isNew():
                self.haschanged = False
            else:
                newlen = self.getNewLen()
                if newlen is not None:
                    self.haschanged = (self.getOldLen() != newlen)
                else:
                    self.haschanged = False
        return self.haschanged

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
      
    def download(self, test=False):
        newcontent = self.getNewContent()
        if newcontent is not None:
            localdir = os.path.dirname(self.local)
            if not os.path.exists(localdir):
                if not test:
                    os.makedirs(localdir)
                print "makedirs: " + localdir
            if not test:
                file = open(self.local, "w")
                file.write(newcontent)
                file.close()
            print "write: " + self.local
            
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
