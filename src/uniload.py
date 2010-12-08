#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009-2010, Samuel Spiza
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
"""Uniload

A bulk downloader for moodle and static web sites

[Uniload](http://github.com/samuelspiza/uniload) is hosted on Github.

The [template](http://gist.github.com/704990) contains examples for the
configuration of Uniload.
"""

__author__ = "Samuel Spiza <sam.spiza@gmail.com>"
__copyright__ = "Copyright (c) 2009-2010, Samuel Spiza"
__license__ = "Simplified BSD License"
__version__ = "0.3.2"

import re
import os
import optparse
import logging
import logging.handlers
import ConfigParser
import sys
from moodlefiles import Module, moodleLogin
from fileupdater import File, absFindall, safe_getResponse
import getpass
try:
    import keyring
except ImportError:
    keyring = None

# NullHandler is part of the logging package in Python 3.1
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

logging.getLogger('').addHandler(NullHandler())

CONFIG_FILES = [os.path.expanduser("~/uniload-cred.ini"),
                os.path.expanduser("~/.uniload-cred.conf"),
                "uniload-cred.ini","uniload-cred.conf"]

CONFIG_FILES2 = [os.path.expanduser("~/.uniload.conf"),"uniload.conf",
                 os.path.expanduser("~/uniload.ini"),"uniload.ini"]

def getOptions(argv):
    """A method for parsing the argument list."""
    installDirectory = os.path.dirname(sys.argv[0])
    config = ConfigParser.SafeConfigParser({
                 'username': "",
                 'log': False,
                 'log.path': installDirectory + "/uniload.log",
                 'moodle.defaultdir': "stuff"
                 })
    config.read(CONFIG_FILES)
    section = "uniload"
    parser = optparse.OptionParser()
    parser.add_option("-t", "--test",
                      dest="test", action="store_true", default=False)
    default = config.getboolean(section, "log")
    parser.add_option("-l", "--log",
                      dest="log", action="store_true", default=default,
                      help="Write a log.")
    default = config.get(section, "log.path")
    parser.add_option("-m", "--logPath",
                      dest="logpath", metavar="PATH", default=default,
                      help="Change the path of the log file.")
    default = config.get(section, "moodle.defaultdir")
    parser.add_option("-d", "--moodleDefaultDir",
                      dest="moodleDefaultDir", metavar="PATH",
                      default=default,
                      help="Change the default directory for unmatched files.")
    return parser.parse_args(argv)[0], config

def uniload(config2, test=False):
    for section in config2.sections():
        if section.startswith("uniload-site "):
            moduleName = section[14:-1]
            print "# Modul: %s #" % moduleName
            page = config2.get(section, "page")
            items = getCascadedOptions(config2.items(section))
            Static(moduleName, page, items, test).start()

def writeWithComments(config, path):
    ci = ["#", ";"] # Comment indicators
    last = "start"
    comments = {last: dict([(i, []) for i in ci])}

    # Retrieve all comment lines from the old config file. Sorts all comment
    # lines in a dict to the nearest section above them.
    with open(path, 'r') as file:
        for line in file.readlines():
            if 0 < len(line.strip()) and line.strip()[0] == "[":
                last = line.strip()
                comments[last] = dict([(i, []) for i in ci])
            elif 0 < len(line) and line[0] in ci:
                comments[last][line[0]].append(line.strip())

    # Writes the current config.
    config.write(open(path, 'w'))

    # Read the new config file and inserts the comment lines under their
    # section.
    content = []
    for i in ci:
        content.extend(comments["start"][i])
    with open(path, 'r') as file:
        for line in file.readlines():
            content.append(line.strip())
            if 0 < len(line) and line[0] == "[" and line.strip() in comments:
                for i in ci:
                    content.extend(comments[line.strip()][i])

    with open(path, 'w') as file:
        file.write("\n".join(content) + "\n")

def moodleAuth(config):
    # Benutzerdaten
    if not config.has_section("moodle-credentials"):
        config.add_section("moodle-credentials")

    username = config.get("moodle-credentials", "username")
    if keyring is None:
        password = None
        if config.has_option("moodle-credentials", "password"):
            password = config.get("moodle-credentials", "password")
    else:
        password = keyring.get_password('uniload', username)

    if password == None or not moodleLogin(username, password):

        for i in range(3):
            username = raw_input("ZIM Kennung:\n")
            password = getpass.getpass("Password:\n")

            if moodleLogin(username, password):
                break
            else:
                print "Authorization failed."
                if i == 2:
                    sys.exit(1)

        # Store the password.
        if keyring is None:
            config.set("moodle-credentials", "password", password)
        else:
            keyring.set_password("uniload", username, password)

        # Store the username.
        config.set("moodle-credentials", "username", username)

        for path in reversed(CONFIG_FILES):
            if os.path.exists(path):
                writeWithComments(config, path)
                break

def moodle(config, config2, defaultDir, test=False):
    moodleAuth(config)

    for section in config2.sections():
        if section.startswith("moodle-module "):
            moduleName = section[15:-1]
            print "# Modul: %s #" % moduleName
            url = config2.get(section, "page")
            overrides = getCascadedOptions(config2.items(section))
            whitelist = config2.has_option(section, "whitelist") and \
                        config2.getboolean(section, "whitelist")
            Module(moduleName, url, overrides, whitelist, defaultDir,
                   test=test).start()

def removeComments(content):
    return "".join([a.split("-->")[-1] for a in content.split("<!--")])

def getCascadedOptions(items, regexp="[0-9]{2}"):
    options = {}
    for item in items:
        m = re.match(regexp, item[0])
        if m is not None:
            if m.group(0) not in options:
                options[m.group(0)] = {}
            options[m.group(0)][item[0][len(m.group(0)):]] = item[1]
    return options

class Static:
    def __init__(self, module, page, items, test):
        self.module = module
        self.page   = page
        self.items  = items
        self.test   = test

    def start(self):
        content = safe_getResponse(self.page).read()
        content = removeComments(content)
        for item in self.items.values():
            localdir = os.path.join(self.module, item['folder'])
            self.loaditem(item['regexp'], content, localdir)

    def loaditem(self, regexp, content, localdir):
        for remote in absFindall(self.page, regexp, content=content):
            local = "/".join([localdir, os.path.basename(remote)])
            File(remote, local, test=self.test).update()

def main(argv):
    # An OptionParser and a ConfigParser object
    options, config = getOptions(argv)

    # A ConfigParser object for the sites and modules.
    config2 = ConfigParser.ConfigParser()
    config2.read(CONFIG_FILES2)

    if options.log:
        if options.test:
            logging.getLogger('').setLevel(logging.DEBUG)
        else:
            logging.getLogger('').setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
                      options.logpath, maxBytes=65000, backupCount=1)
        format = "%(asctime)s %(name)-25s %(levelname)-8s %(message)s"
        handler.setFormatter(logging.Formatter(format))
        logging.getLogger('').addHandler(handler)

    os.chdir(os.path.expanduser(config.get("uniload", "path")))

    if options.test:
        print "*** TESTMODUS (Keine Filesystemoperationen) ***"

    # Start update for static websites.
    uniload(config2, options.test)

    # Start moodle update.
    moodle(config, config2, options.moodleDefaultDir, options.test)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
