#!/usr/bin/env python

import cgi
import string
import json
import psycopg2

ALPHA_PER_PAGE = 50
COUNT_PER_PAGE = 10

conn = psycopg2.connect('dbname=vandalism user=dmontalvo password=iawatchbot')
c = conn.cursor()

form = cgi.FieldStorage()
letter = None
pagenum = 1
showmerged = True
perpage = ALPHA_PER_PAGE
sorting = "alphabetical"
searchstr = None
count = 0
if form.getlist("letter"):
    letter = form.getlist("letter")[0]
if form.getlist("pagenum"):
    pagenum = int(form.getlist("pagenum")[0])
if form.getlist("showmerged"):
    if form.getlist("showmerged")[0] == "False":
        showmerged = False
if form.getlist("sorting"):
    if form.getlist("sorting")[0] == "count":
        sorting = "count"
        perpage = COUNT_PER_PAGE
if form.getlist("pubsearch"):
    searchstr = form.getlist("pubsearch")[0]
searchsuffix = ''
if searchstr is not None:
    searchsuffix = '&pubsearch=%s' % searchstr
if form.getlist("count"):
    count = int(form.getlist("count")[0])

if letter == 'other':
    c.execute("select * from publishers where publisher not similar to '[a-zA-Z]%'")
elif len(letter) == 1:
    exp = letter + '%'
    c.execute("select * from publishers where publisher ilike %s", (exp,))
elif searchstr is not None:
    exp = '%' + searchstr + '%'
    c.execute("select * from publishers where publisher ilike %s", (exp,))
pubs = c.fetchall()
pubs.sort()
lookuplist = []
templist = []
if sorting != "alphabetical":
    for pub in pubs:
        lookuplist.append(pub[0])
        templist.append((pub[1], pub[0], pub[2]))
    templist.sort()
    templist.reverse()
    pubs = []
    for pub in templist:
        pubs.append((pub[1], pub[0], pub[2]))
maxindex = perpage * pagenum
minindex = maxindex - perpage
displaylist = pubs[minindex+count*perpage:maxindex+count*perpage]

print 'Content-type: text/html; charset=UTF-8\n\n'
for pub in displaylist:
    mergedlist = json.JSONDecoder().decode(pub[2])
    merged_str = ', '.join(mergedlist).encode('utf-8')
    column1 = pub[0]
    if sorting != 'alphabetical' and letter != 'search':
        pubindex = lookuplist.index(pub[0])
        column1 = '<a href="http://ol-bots.us.archive.org/cgi-bin/publishersbackup.py?page=%s&letter=%s&showmerged=%s&sorting=alphabetical%s">%s</a>' % ((pubindex + ALPHA_PER_PAGE-1)/ALPHA_PER_PAGE, letter, showmerged, searchsuffix, pub[0])
    if showmerged:
        row = '<tr><td>%s</td><td>%s</td><td><input type="checkbox" name="checkbox" value="%s"></td><td><input type="radio" name="radio" value="%s"></td><td>%s</td></tr>' % (column1, pub[1], pub[0], pub[0], merged_str)
    else:
        row = '<tr><td>%s</td><td>%s</td><td><input type="checkbox" name="checkbox" value="%s"></td><td><input type="radio" name="radio" value="%s"></td></tr>' % (column1, pub[1], pub[0], pub[0])
    print row
