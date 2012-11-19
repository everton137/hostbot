#! /usr/bin/env python

# Copyright 2012 Jtmorgan
 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# import BeautifulSoup as bs
from BeautifulSoup import BeautifulStoneSoup as bss
import urllib2
import wikitools
import re
import settings
import MySQLdb

wiki = wikitools.Wiki(settings.apiurl)
wiki.login(settings.username, settings.password)

conn = MySQLdb.connect(host = 'db67.pmtpa.wmnet', db = 'jmorgan', read_default_file = '~/.my.cnf', use_unicode=1, charset="utf8" )
cursor = conn.cursor()

##global variables#
profileurl = u'http://en.wikipedia.org/w/index.php?title=Wikipedia%%3ATeahouse%%2FHost+landing&action=raw&section=%s'

securl = u'http://en.wikipedia.org/w/api.php?action=parse&page=Wikipedia%3ATeahouse%2FHost+landing&prop=sections&format=xml'


### output path components ###
page_namespace = 'Wikipedia:'

page_section = 'Teahouse/Host/Featured/%i'
 
report_template = '''{{Wikipedia:Teahouse/Host_featured
|username=%s
|image=%s
}}'''


def getFeatured():
	cursor.execute('''
	SELECT
	user_name
	FROM th_up_hosts
	WHERE featured = 1
	AND num_edits_2wk != 0
	LIMIT 25
	''')
	
	feat_list = []
	rows = cursor.fetchall()
	for row in rows:
		feat_host = unicode(row[0],'utf-8')
		feat_list.append(feat_host)
	
	return feat_list

def getSectionData(securl):
	usock = urllib2.urlopen(securl)
	sections = usock.read()
	usock.close()
	soup = bss(sections, selfClosingTags = ['s'])
	
	return soup


def getSectionsToMove(soup, featured_list):
	i = 0
	feat_sec = []
	while i< len(featured_list):
		for x in soup.findAll(name='s', line=featured_list[i]):
			if x:
				featured = x['index']
				feat_sec.append(featured)
		i+=1
	
	return feat_sec


def getFeaturedProfiles(featured_sections, profileurl):	
	feat_profiles = []
	for sec in featured_sections:	
		host_data = []
		usock = urllib2.urlopen(profileurl % sec)
		profile_text = usock.readlines()
		usock.close()
		for line in profile_text:
			if re.match('\|\s*username\s*=', line):
				user_string = line[10:]
				host_data.insert(0,user_string)
			if re.match('\|\s*image\s*=', line):
				image_string = line[7:]
				host_data.insert(1,image_string)
		feat_profiles.append(host_data)
		
	return feat_profiles	
		

def updateFeaturedHosts(featured_profiles):	
	i = 1
	for profile in featured_profiles:
		report_title = page_namespace + page_section % i
		report = wikitools.Page(wiki, page_namespace + page_section % i)
		report_text = report_template % (profile[0], profile[1])
		i += 1
		report.edit(report_text, summary="Automatic update of [[Wikipedia:Teahouse/Host/Featured|featured host gallery]] by [[User:HostBot|HostBot]]", bot=1)
	
				
##MAIN##
featured_list = getFeatured()
soup = getSectionData(securl)
featured_sections = getSectionsToMove(soup, featured_list)
featured_profiles = getFeaturedProfiles(featured_sections, profileurl)
updateFeaturedHosts(featured_profiles)

             