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

import random
import urllib2
import itertools
import wikitools
import settings
from BeautifulSoup import BeautifulStoneSoup as bss
import MySQLdb

wiki = wikitools.Wiki(settings.apiurl)
wiki.login(settings.username, settings.password)

conn = MySQLdb.connect(host = 'db67.pmtpa.wmnet', db = 'jmorgan', read_default_file = '~/.my.cnf', use_unicode=1, charset="utf8" )
cursor = conn.cursor()


### output path components ###
page_namespace = u'Wikipedia:'


#the page where active host profiles are displayed
page_section = 'Teahouse/Host_landing'

### output templates ###

page_template = '''=Hosts=
{{TOC hidden}}

<br/>
</noinclude>
%s
'''

### API calls ###

securl = u'http://en.wikipedia.org/w/api.php?action=parse&page=Wikipedia%3ATeahouse%2FHost+landing&prop=sections&format=xml'

		
### FUNCTIONS ###

def findNewHosts():
	# gets the hosts who joined most recently
	cursor.execute('''
	SELECT
	user_name
	FROM th_up_hosts
	WHERE featured = 1
	AND num_edits_2wk != 0
	ORDER BY join_date desc
	LIMIT 15
	''')

	new_list = []
	rows = cursor.fetchall()
	for row in rows:
		feat_host = unicode(row[0],'utf-8')
		new_list.append(feat_host)

	#then, find the 10 most active hosts
	cursor.execute('''
	SELECT
	user_name
	FROM th_up_hosts
	WHERE featured = 1
	AND join_date < DATE_FORMAT(DATE_SUB(NOW(),INTERVAL 14 DAY), '%s')
	ORDER BY num_edits_2wk desc
	LIMIT 10
	''' % "%Y%m%d%H%i%s")
	
	active_list = []
	rows = cursor.fetchall()
	for row in rows:
		feat_host = unicode(row[0],'utf-8')
		active_list.append(feat_host)
	
	feat_list = list(set(itertools.chain(new_list, active_list)))
	
	return feat_list
		
def getSectionData(securl):
	usock = urllib2.urlopen(securl)
	sections = usock.read()
	usock.close()
	soup = bss(sections, selfClosingTags = ['s'])
	
	return soup

#get the section ids of all the profiles on the Host_landing page	
def getAllSections(soup):
	all_sec = []
	for x in soup.findAll('s',toclevel="2"):
		all_sec.append(x['index'])
	
	return all_sec

def getSectionsToMove(soup, featured_hosts):
	i = 0
	feat_sec = []
	while i< len(featured_hosts):
		for x in soup.findAll(name='s', line=featured_hosts[i]):
			if x:
				featured = x['index']
				feat_sec.append(featured)
		i+=1
	
	return feat_sec

#gets the profiles for new hosts
def getFeaturedProfiles(featured_sections):	
	feat_profiles = []
	for sec in featured_sections:	
		hostPageURL = u'http://en.wikipedia.org/w/index.php?title=Wikipedia%%3ATeahouse%%2FHost+landing&action=raw&section=%s' % sec
		usock = urllib2.urlopen(hostPageURL)
		section = usock.read()
		usock.close()
		section = unicode(section, 'utf8')
		section = section.strip()
		profile_text = u'''%s
		
		''' % section
		feat_profiles.append(profile_text)	
		
	return feat_profiles

#gets all the other profile sections, the ones we don't want to feature
def getNonFeaturedProfiles(profile_sections, featured_sections):
	nonfeat_sec = [x for x in profile_sections if x not in featured_sections]
	nonfeat_profiles = []	
	for sec in nonfeat_sec:	
		hostPageURL = u'http://en.wikipedia.org/w/index.php?title=Wikipedia%%3ATeahouse%%2FHost+landing&action=raw&section=%s' % sec
		usock = urllib2.urlopen(hostPageURL)
		section = usock.read()
		usock.close()
		section = unicode(section, 'utf8')
		section = section.strip()
		profile_text = u'''%s
		
		''' % section
		nonfeat_profiles.append(profile_text)	
	
	return nonfeat_profiles	

#returns the host profiles to the page, with the newest hosts on top	
def returnReorderedProfiles(all_profiles):

	report_title = page_namespace + page_section
	report = wikitools.Page(wiki, report_title)
	profiles = page_template % '\n'.join(all_profiles)
	profiles = profiles.encode('utf-8')
	report.edit(profiles, section=1, summary="HostBot is moving new hosts and highly active hosts to the top, in random order", bot=1)	


##main##
featured_hosts = findNewHosts()
soup = getSectionData(securl)
profile_sections = getAllSections(soup)
featured_sections = getSectionsToMove(soup, featured_hosts)

featured_profiles = getFeaturedProfiles(featured_sections)
random.shuffle(featured_profiles) #shuffles the profile order for new and highly active hosts.
nonfeatured_profiles = getNonFeaturedProfiles(profile_sections, featured_sections)
random.shuffle(nonfeatured_profiles) #shuffles the profile order
all_profiles = featured_profiles + nonfeatured_profiles


returnReorderedProfiles(all_profiles)
