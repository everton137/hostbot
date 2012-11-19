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

import MySQLdb
import urllib2
import wikitools
import settings
from BeautifulSoup import BeautifulStoneSoup as bss
from BeautifulSoup import BeautifulSoup as bs

wiki = wikitools.Wiki(settings.apiurl)
wiki.login(settings.username, settings.password)

conn = MySQLdb.connect(host = 'db67.pmtpa.wmnet', db = 'jmorgan', read_default_file = '~/.my.cnf', use_unicode=1, charset="utf8" )
cursor = conn.cursor()

##global variables and output templates
securl = u'http://en.wikipedia.org/w/api.php?action=parse&page=Wikipedia%3ATeahouse%2FHost+landing&prop=sections&format=xml'

#the page where inactive host profiles are displayed 
host_breakroom = 'Teahouse/Host_breakroom'

#the page where active host profiles are displayed
host_landing = 'Teahouse/Host_landing' 

page_namespace = u'Wikipedia:'

breakroom_template = '''%s
'''

host_landing_template = '''=Hosts=
{{TOC hidden}}

<br/>
</noinclude>
%s
'''

##functions
# gets the hosts who are not currently active from the database table
def findInactiveHosts():
	cursor.execute('''
		SELECT
		user_name
		FROM th_up_hosts
		WHERE num_edits_2wk = 0
		AND in_breakroom = 0
		AND retired = 0
		AND colleague = 0
		AND join_date is not null;
		''')

	inac_list = []
	rows = cursor.fetchall()
	for row in rows:
		inac_host = unicode(row[0],'utf-8')
		inac_list.append(inac_host)
	
	return inac_list

#gets the host landing page metadata: section numbers and titles
def getSectionData(securl):
	usock = urllib2.urlopen(securl)
	sections = usock.read()
	usock.close()
	soup = bss(sections, selfClosingTags = ['s'])
	
	return soup
	
#gets all of the sections, including those I want to remove
def getAllSections(soup):
	all_sec = []
	for x in soup.findAll('s',toclevel="2"):
		all_sec.append(x['index'])
	
	return all_sec

#identifies those sections that need to be removed and stores their numbers in a list	
def getSectionsToRemove(soup, inactive_list):
	i = 0
	inac_sec = []
	while i< len(inactive_list):
		for x in soup.findAll(name='s', line=inactive_list[i]):
			if x:
				inactive = x['index']
				inac_sec.append(inactive)
		i+=1
	
	return inac_sec

#compares all profiles to inactive profiles, and tells which ones to retain
def getSectionsToRetain(all_hosts, inactive_hosts):

	ac_sec = [x for x in all_hosts if x not in inactive_hosts]
	
	return ac_sec

#collects the profiles of inactive hosts	
def grabInactiveHostProfiles(inactive_hosts):	
	#first, gets all the ones we want to move over
	all_inac_profiles = []
	i = 0
	while i < len(inactive_hosts):	
		sec = inactive_hosts[i]
		hostPageURL = u'http://en.wikipedia.org/w/index.php?title=Wikipedia%%3ATeahouse%%2FHost+landing&action=raw&section=%s' % sec
		usock = urllib2.urlopen(hostPageURL)
		section = usock.read()
		usock.close()
		section = unicode(section, 'utf8')
		section = section.strip()
		profile_text = u'''%s
		
		''' % section
		i += 1
		all_inac_profiles.append(profile_text)
	
	#then, gets the first one from the breakroom and appends it
	breakroomURL = u'http://en.wikipedia.org/w/index.php?title=Wikipedia%3ATeahouse%2FHost+breakroom&action=raw&section=2'
	usock = urllib2.urlopen(breakroomURL)
	section = usock.read()
	usock.close()
	section = unicode(section, 'utf8')
	section = section.strip()
	profile_text = u'''%s
			
		''' % section
	all_inac_profiles.append(profile_text)
	
	return all_inac_profiles

#collects the profiles of active hosts
def grabActiveHostProfiles(active_hosts):

	#first, gets all the ones we want to move over
	all_ac_profiles = []
	i = 0
	while i < len(active_hosts):	
		sec = active_hosts[i]
		hostPageURL = u'http://en.wikipedia.org/w/index.php?title=Wikipedia%%3ATeahouse%%2FHost+landing&action=raw&section=%s' % sec
		usock = urllib2.urlopen(hostPageURL)
		section = usock.read()
		usock.close()
		section = unicode(section, 'utf8')
		section = section.strip()
		profile_text = u'''%s
		
		''' % section
		i += 1
		all_ac_profiles.append(profile_text)
		
	return all_ac_profiles

#moves the inactive profiles to the breakroom
def moveInactiveProfiles(all_inactive_profiles):
	breakroom_string = page_namespace + host_breakroom
	removed = wikitools.Page(wiki, breakroom_string)
	removed_profiles = breakroom_template % '\n'.join(all_inactive_profiles)
	removed_profiles = removed_profiles.encode('utf-8')
	removed.edit(removed_profiles, section=2, summary="HostBot is automatically moving profiles for currently inactive hosts from [[WP:Teahouse/Host_landing]]", bot=1)
	
#returns the profiles of still-active hosts to the host landing page
def returnActiveProfiles(all_active_profiles):
	landing_string = page_namespace + host_landing
	returned = wikitools.Page(wiki, landing_string)
	returned_profiles = host_landing_template % '\n'.join(all_active_profiles)
	returned_profiles = returned_profiles.encode('utf-8')
	returned.edit(returned_profiles, section=1, summary="HostBot is automatically moving profiles for currently inactive hosts to [[WP:Teahouse/Host_breakroom]]", bot=1)	
	

#writes this operation to the database
def updateHostsInBreakroom(inactive_list):
	
	for host in inactive_list:
		cursor.execute('''
	UPDATE th_up_hosts
		set featured = 0, in_breakroom = 1, last_move_date = NOW()
		where user_name = "%s";
	''' % host)
		conn.commit()


##main
inactive_list = findInactiveHosts()
if inactive_list:
	soup = getSectionData(securl)
	all_hosts = getAllSections(soup)
	inactive_hosts = getSectionsToRemove(soup, inactive_list)
# 	print ("inactive hosts are: ", inactive_hosts)
	active_hosts = getSectionsToRetain(all_hosts, inactive_hosts)
# 	print ("active hosts: ", active_hosts)
	all_inactive_profiles = grabInactiveHostProfiles(inactive_hosts)
	all_active_profiles = grabActiveHostProfiles(active_hosts)
	
	moveInactiveProfiles(all_inactive_profiles)
	returnActiveProfiles(all_active_profiles)
	updateHostsInBreakroom(inactive_list)
else:
	pass

cursor.close()
conn.close()