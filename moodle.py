#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib, urllib2, re, cookielib, os, sys, ConfigParser
from BeautifulSoup import BeautifulSoup
from fileupdater import safe_getResponse, File


def openCourse(config, url, name, overrides=[]):
    print "Kurs:", name
    new_files = []
    html = safe_getResponse(url).read()
    soup = BeautifulSoup(html)
    links = soup.findAll(attrs={'href' : re.compile("resource/view.php")})
    for link in links:
        if not(link.span is None):
            new = download(config, link['href'], link.span.next, name, overrides)
            new_files.extend(new)
    return new_files

def download(config, url, name, CourseName, overrides):
    #print url
    new_files = []
    response = safe_getResponse(url)
    if(response is not None):
        # Direkter Download
        if(response.info().get("Content-Type").find('audio/x-pn-realaudio') == 0):
            d="" #print "Real Player Moodle Page"
        elif(response.info().get("Content-Type").find('text/html') != 0):
            filename = os.path.basename(response.geturl())
            filename = CourseName + "/" + filename
            #value, params = cgi.parse_header(header)
            #filename = params.get('filename')
            if(saveFile(config, response.geturl(), CourseName, overrides)):
                new_files.append(filename)
                #print "Neue Datei:", filename
        # Moodle indirekter Download
        else:
            data = response.read()
            soup = BeautifulSoup(data)
            # entweder frames oder files und dirs
            frames = soup.findAll(attrs={'src' : re.compile("http://moodle.uni-duisburg-essen.de/file.php")})
            files = soup.findAll(attrs={'href' : re.compile("http://moodle.uni-duisburg-essen.de/file.php")})
            dirs = soup.findAll(attrs={'href' : re.compile("subdir")})

            # PopUp Links
            popup = soup.find(attrs={'href' : re.compile("inpopup=true")})
            if(popup is not None):
                print "NEW C"
                download(config, popup['href'], name, CourseName, overrides)
                #print response.info()
                #print "hu", popup['href']


            name = re.sub(u"[^a-zA-Z0-9_()äÄöÖüÜ ]", "", name).strip()
            for f in files:
                #print "Folder:", name
                if(saveFile(config, f['href'], CourseName, overrides)):
                    new_files.append(os.path.basename(f['href']))
                    #print "Neue Datei:", filename

            for d in dirs:
                # basename mal anders missbrauchen :-D
                folder = os.path.basename(d['href'])
                #print "Gehe in folder:", folder
                folder = name + "/" + folder
                href = "http://moodle.uni-duisburg-essen.de/mod/resource/" + d['href']
                download(config, href, folder, CourseName, overrides)

            # jojo eigentlich nur eine datei...
            for inli in frames:
                if(saveFile(config, inli['src'], CourseName, overrides)):
                    new_files.append(os.path.basename(inli['src']))
                    #print "Neue Datei:", filename
    return new_files

def saveFile(config, url, modul, overrides):
    # Find local filepath
    fullFileName = localfile(url, modul, overrides)

    # Update file and return if localfile was modified
    test = config.getboolean("uniload", "test")
    return File(url, fullFileName, test=test).update()

def localfile(url, modul, overrides):
    newpath = "/".join(url.split("/")[5:])
    newpath = newpath.replace("?forcedownload=1", "")
    for o in overrides:
        if (not 'regexp' in o or re.search(o['regexp'], newpath) is not None) and (not 'remote' in o or os.path.dirname(newpath).startswith(o['remote'])):
            if 'remote' in o:
                newpath = newpath.replace(o['remote'] + "/", "")
            return os.path.join(modul, o['folder'], newpath)
    return os.path.join(modul, "stuff", newpath)
