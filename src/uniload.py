#!/usr/bin/env python
#
# This file is licensed under the Simplified BSD License.
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
"""uniload - a bulk downloader for moodle and static web sites"""

__author__ = "Samuel Spiza <sam.spiza@gmail.com>"
__copyright__ = "Copyright (c) 2009-2010, Samuel Spiza"
__license__ = "Simplified BSD License"
__version__ = "0.1"

import sys
import os
import re
import optparse
import ConfigParser
from moodlefiles import moodleLogin, openCourse
from fileupdater import File, absFindall, safe_getResponse

CONFIG_FILES = [os.path.expanduser("~/.uniload.conf"),"uniload.conf",
                os.path.expanduser("~/.uniload-cred.conf"),"uniload-cred.conf"]

def main(argv):
    config = ConfigParser.ConfigParser()
    config.read(CONFIG_FILES)
    os.chdir(os.path.expanduser(config.get("uniload", "path")))
    options = getOptions(argv)
    config.set("uniload", "test", str(options.test))
    if options.test:
        print "*** TESTMODUS (Keine Filesystemoperationen) ***"
    uniload(config, options.test)
    moodle(config)
    return 0

def getOptions(argv):
    parser = optparse.OptionParser()
    parser.add_option("-t", "--test",
                      dest="test", action="store_true", default=False)
    return parser.parse_args(argv)[0]

def uniload(config, test):
    for section in config.sections():
        if section.startswith("uniload-site "):
            module = section[14:-1]
            print "Kurs: %s" % module
            page = config.get(section, "page")
            items = getCascadedOptions(config.items(section))
            load(module, page, items, test)

def moodle(config):
    moodleLogin(config)
    for section in config.sections():
        if section.startswith("moodle-module "):
            module = section[15:-1]
            page = config.get(section, "page")
            overrides = getCascadedOptions(config.items(section))
            openCourse(config, page, module, overrides)
                
def load(module, page, items, test):
    content = safe_getResponse(page).read()
    for item in items:
        localdir = os.path.join(module, item['folder'])
        loaditem(page, item['regexp'], content, localdir, test)

def loaditem(page, regexp, content, localdir, test):
    for remote in absFindall(page, regexp, content=content):
        local = "/".join([localdir, os.path.basename(remote)])
        File(remote, local, test=test).update()

def getCascadedOptions(items, regexp="[0-9]{2}"):
    options = {}
    for item in items:
        m = re.match(regexp, item[0])
        if m is not None:
            if m.group(0) not in options:
                options[m.group(0)] = {}
            options[m.group(0)][item[0][len(m.group(0)):]] = item[1]
    return options

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))