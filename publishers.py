#!/usr/bin/env python

import cgi
import psycopg2
import string
import json
import codecs
import sys

ALPHA_PER_PAGE = 50
COUNT_PER_PAGE = 10

conn = psycopg2.connect('dbname=vandalism user=dmontalvo password=iawatchbot')
c = conn.cursor()

def merge(masterpub, mergelist):
    count = 0
    compoundlist = []
    for pub in mergelist:
        c.execute('select * from publishers where publisher=%s', (pub,))      
        row = c.fetchone()
        count += row[1]
        if row[2] is None:
            sublist = []
        else:
            sublist = json.JSONDecoder().decode(row[2])
        compoundlist += sublist
        c.execute('delete from publishers where publisher=%s', (pub,))        
    publist = mergelist
    publist.remove(masterpub)
    publist += compoundlist
    jsonlist = json.JSONEncoder().encode(publist)
    c.execute("insert into publishers (publisher, count, list) values (%s, %s, %s)", (masterpub, count, jsonlist))
    conn.commit()

form = cgi.FieldStorage()
letter = None
pagenum = 1
master = None
showmerged = True
perpage = ALPHA_PER_PAGE
sorting = "alphabetical"
searchstr = None
if form.getlist("letter"):
    letter = form.getlist("letter")[0]
if form.getlist("page"):
    pagenum = int(form.getlist("page")[0])
if form.getlist("radio"):
    master = form.getlist("radio")[0]
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
merges = form.getlist("checkbox")
print "Content-type: text/html; charset=UTF-8\n\n"
print "<html><body><title>Publishers</title>"
if len(merges) == 1:
    print "Error: Must select at least 2 publishers to merge.</body></html>"
    exit()
if master is not None and master not in merges:
    print "Error: Master must be one of the merged publishers.</body></html>"
    exit()

if len(merges) > 1:
    if master is None:
        print "Error: A master publisher must be chosen.</body></html>"
        exit()
    merge(master, merges)
    mergestring = json.JSONEncoder().encode(merges)
    c.execute("insert into pubqueue (master, merges) values (%s, %s)", (master, mergestring))
    conn.commit()

for x in range(65, 91):
    if letter is not None and string.lower(letter) == string.lower(chr(x)):
        print chr(x)
    else:
        print '<a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?letter=%s&showmerged=%s&sorting=%s%s">%s</a>' % (chr(x), showmerged, sorting, searchsuffix, chr(x))
if letter == 'other':
    print "* "
else:
    print '<a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?letter=other&showmerged=%s&sorting=%s%s">*</a>' % (showmerged, sorting, searchsuffix)
if letter == "search":
    value = ''
    if searchstr is not None:
        value = ' value="%s"' % searchstr
    print 'Search<p><form name="myform" method="POST"><input type="text" name="pubsearch"%s /><input type="submit" value="Submit"></form>' % value
    if searchstr is None:
        print '</body></html>'
        exit()
else:
    print '<a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?letter=search&showmerged=%s&sorting=%s%s">Search</a><br>' % (showmerged, sorting, searchsuffix)

if letter is None:
    print '</body></html>'
    exit()

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
displaylist = pubs[minindex:maxindex]
maxpage = (len(pubs)+perpage-1)/perpage+1
print "Sorting: "
if sorting == "alphabetical":
    print 'Alphabetical <a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?letter=%s&showmerged=%s&sorting=count%s">Count</a><br>' % (letter, showmerged, searchsuffix)
else:
    print '<a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?letter=%s&showmerged=%s&sorting=alphabetical%s">Alphabetical</a> Count<br>' % (letter, showmerged, searchsuffix)
print "Page: "
if pagenum == 12:
    print '<a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?page=1&letter=%s&showmerged=%s&sorting=%s%s">1</a>' % (letter, showmerged, sorting, searchsuffix)
elif pagenum > 12:
    print '<a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?page=1&letter=%s&showmerged=%s&sorting=%s%s">1</a> ... ' % (letter, showmerged, sorting, searchsuffix)
for x in range(max(1, pagenum - 10), min(pagenum + 10, maxpage)):
    if x == pagenum:
        print x
    else:
        print '<a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?page=%s&letter=%s&showmerged=%s&sorting=%s%s">%s</a>' % (x, letter, showmerged, sorting, searchsuffix, x)
if maxpage - pagenum > 11:
    print '... <a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?page=%s&letter=%s&showmerged=%s&sorting=%s%s">%s</a>' % (maxpage-1, letter, showmerged, sorting, searchsuffix, maxpage-1)
elif maxpage - pagenum == 11:
    print '<a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?page=%s&letter=%s&showmerged=%s&sorting=%s%s">%s</a>' % (maxpage-1, letter, showmerged, sorting, searchsuffix, maxpage-1)
if showmerged:
    print '<br>Show Merged: Yes <a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?page=%s&letter=%s&showmerged=False&sorting=%s%s">No</a>' % (pagenum, letter, sorting, searchsuffix)
else:
    print '<br>Show Merged: <a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?page=%s&letter=%s&showmerged=True&sorting=%s%s">Yes</a> No' % (pagenum, letter, sorting, searchsuffix)
if showmerged:
    print '<p><form name="myform" method="POST"><table border=1 id="testtable"><tr><th>Master Publisher</th><th>Count</th><th>Merge</th><th>Master</th><th>Merged</th></tr>'
else:
    print '<p><form name="myform" method="POST"><table border=1 id="testtable"><tr><th>Master Publisher</th><th>Count</th><th>Merge</th><th>Master</th></tr>'
for pub in displaylist:
    merged_str = ''
    if pub[2] is not None:
        mergedlist = json.JSONDecoder().decode(pub[2])
        merged_str = ', '.join(mergedlist).encode('utf-8')
    column1 = pub[0]
    if sorting != 'alphabetical' and letter != 'search':
        pubindex = lookuplist.index(pub[0])
        column1 = '<a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py?page=%s&letter=%s&showmerged=%s&sorting=alphabetical%s">%s</a>' % ((pubindex + ALPHA_PER_PAGE-1)/ALPHA_PER_PAGE, letter, showmerged, searchsuffix, pub[0])
    if showmerged:
        row = '<tr><td>%s</td><td>%s</td><td><input type="checkbox" name="checkbox" value="%s"></td><td><input type="radio" name="radio" value="%s"></td><td>%s</td></tr>' % (column1, pub[1], pub[0], pub[0], merged_str)
    else:
        row = '<tr><td>%s</td><td>%s</td><td><input type="checkbox" name="checkbox" value="%s"></td><td><input type="radio" name="radio" value="%s"></td></tr>' % (column1, pub[1], pub[0], pub[0])
    print row
if maxindex < len(pubs):
    print '</table><br><div id="showmore"><a href="http://ol-bots.us.archive.org/cgi-bin/publishers.py">Show More</a></div><p><input type="submit" value="Submit"></form>'
else:
    print '</table><p><input type="submit" value="Submit"></form>'
print '<script src="http://openlibrary.org/static/upstream/js/jquery-1.3.2.min.js"></script>'
print '''<script>
var $count = 0
$(document).ready(function(){
$("#showmore").click(function(event){
event.preventDefault();
$count++
$.get('pubfetch.py', {"letter": "%s", "pagenum": "%s", "showmerged": "%s", "sorting": "%s", "pubsearch": "%s", "count":$count},function(data) {
  $("#testtable").append(data);
  if(%s + $count * %s >= %s) {
    $("#showmore").hide()
  }
});
});
});
</script>''' % (letter, pagenum, showmerged, sorting, searchstr, maxindex, perpage, len(pubs))
print '</body></html>'
c.close()
