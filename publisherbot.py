#!/usr/bin/python

# PublisherBot
# by Daniel Montalvo

from time import asctime, time, ctime
import time
import json
import urllib
import string
import sys
import psycopg2
import traceback
import os
sys.path.append('/home/dmontalvo/openlibrary')
from openlibrary.api import OpenLibrary

def change(before, after):
    global logstring
    madechange = False
    url = 'http://openlibrary.org/search.json?publisher="%s"' % urllib.quote(before.encode('utf-8'))
    search = urllib.urlopen(url)
    results = json.JSONDecoder().decode(search.read())
    if results.has_key('docs') and len(results['docs']) > 0:
        for work in results['docs']:
            for edition_key in work['edition_key']:
                edition = ol.get("/books/%s" % edition_key)
                if edition.has_key('publishers'):
                    for pub in edition['publishers']:
                        if string.lower(before) == string.lower(pub):
                            edition['publishers'].remove(pub)
                            edition['publishers'].append(after)
                            new_authors = []
                            for akey in edition['authors']:
                                a = ol.get(akey)
                                if a['type'] == '/type/redirect':
                                    akey = a['location']
                                new_authors.append(akey)
                            edition['authors'] = new_authors
                            ol.save("/books/%s" % edition_key, edition, 'corrected publisher')
                            logstring += "\tModified publisher for %s.\n" % edition_key
                            madechange = True
    if not madechange:
        logstring += "\tPublisher %s not found.\n" % before

if os.path.exists("pubbot_lock.txt"):
    print "Bot already running. Exiting."
    exit()
i = open("pubbot_lock.txt", 'w')

t = asctime()
s = time.time()

try:
    global conn
    global c
    conn = psycopg2.connect('dbname=vandalism user=dmontalvo password=iawatchbot')
    c = conn.cursor()
    ol = OpenLibrary("http://openlibrary.org")
    ol.autologin()
    global logstring
    logstring = 'Started at: %s\n' % t
    c.execute('select * from pubqueue')
    queue = c.fetchall()

    for item in queue:
        master = item[0].decode('utf-8')
        x = 0
        titlecased = ''
        for letter in master:
            val = ord(letter)
            if (x == 0 or master[x-1] == ' ') and val >= 97 and val <= 122:
                titlecased += string.upper(letter)
            else:
                titlecased += letter
            x += 1
        mergelist = json.JSONDecoder().decode(item[1])
        for publisher in mergelist:
            logstring += "Changing %s to %s.\n" % (publisher, titlecased)
            change(publisher, titlecased)
        c.execute('delete from pubqueue where master=%s and merges=%s', (item[0], item[1]))
        conn.commit()

    logstring += "Ended at: %s\n" % asctime()
    logstring += "Total run time: %s seconds\n" % (time.time() - s)
    c.execute("insert into logs (time, bot, logtype, data) values (%s, 'publisherbot', 'logs', %s)", (t, logstring))
    os.remove("pubbot_lock.txt")
    c.close()

except:
    error = traceback.format_exc()
    print error
    c.execute("insert into logs (time, bot, logtype, data) values (%s, 'publisherbot', 'errors', %s)", (t, error))
    conn.commit()
    c.close()
    os.remove("pubbot_lock.txt")
