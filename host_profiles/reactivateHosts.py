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
securl = u'http://en.wikipedia.org/w/api.php?action=parse&page=Wikipedia%3ATeahouse%2FHost+breakroom&prop=sections&format=xml'

#the page where inactive host profiles are displayed 
host_breakroom = 'Teahouse/Host_breakroom'

#the page where active host profiles are displayed
host_landing = 'Teahouse/Host_landing' 

page_namespace = u'Wikipedia:'

breakroom_template = '''= Hosts on Sabbatical =
{{TOC left}}
</div>
<br/>
%s
'''

host_landing_template = '''%s
'''

# gets the hosts who are nn the breakroom, and newly active from the database table
def findReactiveHosts():
	cursor.execute('''
		SELECT
		user_name
		FROM th_up_hosts
		WHERE num_edits_2wk > 0
		AND in_breakroom = 1
		AND retired = 0
		AND colleague = 0
		AND join_date is not null;
		''')

	reac_list = []
	rows = cursor.fetchall()
	for row in rows:
		reac_host = unicode(row[0],'utf-8')
		reac_list.append(reac_host)
	
	return reac_list

#gets the host breakroom page metadata: section numbers and titles
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
def getSectionsToRemove(soup, reactive_list):
	i = 0
	reac_sec = []
	while i< len(reactive_list):
		for x in soup.findAll(name='s', line=reactive_list[i]):
			if x:
				reactive = x['index']
				reac_sec.append(reactive)
		i+=1
	
	return reac_sec

#compares all profiles to reactive profiles, and tells which ones to retain
def getSectionsToRetain(all_hosts, reactive_hosts):

	in_sec = [x for x in all_hosts if x not in reactive_hosts]
	
	return in_sec

#collects the profiles of newly active hosts	
def grabReactiveHostProfiles(reactive_hosts):	
	#first, gets all the ones we want to move over
	all_reac_profiles = []
	i = 0
	while i < len(reactive_hosts):	
		sec = reactive_hosts[i]
		breakroomURL = u'http://en.wikipedia.org/w/index.php?title=Wikipedia%%3ATeahouse%%2FHost+breakroom&action=raw&section=%s' % sec
		usock = urllib2.urlopen(breakroomURL)
		section = usock.read()
		usock.close()
		section = unicode(section, 'utf8')
		section = section.strip()
		profile_text = u'''%s
		
		''' % section
		i += 1
		all_reac_profiles.append(profile_text)
	
	#then, gets the first one from the host landing and appends it
	hostPageURL = u'http://en.wikipedia.org/w/index.php?title=Wikipedia%3ATeahouse%2FHost+landing&action=raw&section=2'
	usock = urllib2.urlopen(hostPageURL)
	section = usock.read()
	usock.close()
	section = unicode(section, 'utf8')
	section = section.strip()
	profile_text = u'''%s
			
		''' % section
	all_reac_profiles.append(profile_text)
	
	return all_reac_profiles

#collects the profiles of still inactive hosts
def grabInactiveHostProfiles(inactive_hosts):

	#grab all the ones we want to keep in the breakroom
	all_inac_profiles = []
	i = 0
	while i < len(inactive_hosts):	
		sec = inactive_hosts[i]
		breakroomURL = u'http://en.wikipedia.org/w/index.php?title=Wikipedia%%3ATeahouse%%2FHost+breakroom&action=raw&section=%s' % sec
		usock = urllib2.urlopen(breakroomURL)
		section = usock.read()
		usock.close()
		section = unicode(section, 'utf8')
		section = section.strip()
		profile_text = u'''%s
		
		''' % section
		i += 1
		all_inac_profiles.append(profile_text)
		
	return all_inac_profiles

#moves the reactive profiles to the host landing
def moveReactiveProfiles(all_reactive_profiles):
	landing_string = page_namespace + host_landing	
	removed = wikitools.Page(wiki, landing_string)
	removed_profiles = host_landing_template % '\n'.join(all_reactive_profiles)
	removed_profiles = removed_profiles.encode('utf-8')
	removed.edit(removed_profiles, section=2, summary="HostBot is automatically moving profiles of recently active hosts from [[WP:Teahouse/Host_breakroom]]", bot=1)
	
#returns the profiles of still-active hosts to the host landing page
def returnInactiveProfiles(all_inactive_profiles):
	breakroom_string = page_namespace + host_breakroom
	returned = wikitools.Page(wiki, breakroom_string)
	returned_profiles = breakroom_template % '\n'.join(all_inactive_profiles)
	returned_profiles = returned_profiles.encode('utf-8')
	returned.edit(returned_profiles, section=1, summary="HostBot is automatically moving profiles of recently active hosts to [[WP:Teahouse/Host_landing]]", bot=1)	
	

#writes this operation to the database
def updateHostsInBreakroom(reactive_list):
	
	for host in reactive_list:
		cursor.execute('''
	UPDATE th_up_hosts
		set in_breakroom = 0, featured = 1, last_move_date = NOW()
		where user_name = "%s";
	''' % host)
		conn.commit()


#main
reactive_list = findReactiveHosts()
if reactive_list:
	soup = getSectionData(securl)
	all_hosts = getAllSections(soup)
	reactive_hosts = getSectionsToRemove(soup, reactive_list)
	inactive_hosts = getSectionsToRetain(all_hosts, reactive_hosts)
# 	print ("inactive hosts: ", inactive_hosts)
# 	print ("reactive hosts: ", reactive_hosts)
	all_reactive_profiles = grabReactiveHostProfiles(reactive_hosts)
	all_inactive_profiles = grabInactiveHostProfiles(inactive_hosts)
	
	moveReactiveProfiles(all_reactive_profiles)
	returnInactiveProfiles(all_inactive_profiles)
	updateHostsInBreakroom(reactive_list)

else:
	pass

cursor.close()
conn.close()	
