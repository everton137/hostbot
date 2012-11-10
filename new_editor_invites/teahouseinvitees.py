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

import datetime
import MySQLdb
import wikitools
import settings

report_title = settings.rootpage + '/Hosts/Database_reports#Daily_Report'

report_template = u'''==Daily Report==

===Highly active new editors===
Below is a list of editors who joined within the last 24 hours, have since made more than 10 edits, and were not blocked at the time the report was generated.
 
{| class="wikitable sortable plainlinks"
|-
! Guest #
! Guest Name
! Edit Count
! Email enabled?
! Contribs
! Already Invited?
|-
%s
|}


===New Autoconfirmed Editors===
Below is a list of editors who gained [[Wikipedia:User_access_levels#Autoconfirmed_users|autoconfirmed status]] today, who were not previously invited to Teahouse after their first day, and were not blocked at the time the report was generated.
 
{| class="wikitable sortable plainlinks"
|-
! Guest #
! Guest Name
! Edit Count
! Email enabled?
! Contribs
! Already Invited?
|-
%s
|}

{{Wikipedia:Teahouse/Layout-end}}
{{Wikipedia:Teahouse/Host navigation}}
'''

wiki = wikitools.Wiki(settings.apiurl)
wiki.login(settings.username, settings.password)
conn = MySQLdb.connect(host = 'db67.pmtpa.wmnet', db = 'jmorgan', read_default_file = '~/.my.cnf' )
cursor = conn.cursor()

cursor.execute('''
insert ignore into th_up_invitees 
	(user_id, user_name, user_registration, user_editcount, email_status, sample_date, sample_type, invite_status, hostbot_invite, hostbot_personal, hostbot_skipped)
SELECT
user_id,
user_name,
user_registration,
user_editcount,
user_email_authenticated,
NOW(),
1,
0,
0,
0,
0
FROM enwiki.user
WHERE user_registration > DATE_FORMAT(DATE_SUB(NOW(),INTERVAL 1 DAY),'%Y%m%d%H%i%s')
AND user_editcount > 10
AND user_name not in (SELECT REPLACE(log_title,"_"," ") from enwiki.logging where log_type = "block" and log_action = "block" and log_timestamp >  DATE_FORMAT(DATE_SUB(NOW(),INTERVAL 2 DAY),'%Y%m%d%H%i%s'));
''')
conn.commit()


cursor.execute('''
SELECT
id,
user_name,
user_editcount,
email_status
FROM th_up_invitees
WHERE date(sample_date) = date(NOW())
AND sample_type = 1;
''')

output1 = []
fields = cursor.fetchall()
for field in fields:
	number = field[0]
	user_name = unicode(field[1], 'utf-8')	
	user_editcount = field[2]
	email_status = field[3]
	email_string = "No"
	if email_status is not None:
		email_string = '[[Special:EmailUser/%s|Yes]]' % user_name
	talk_page = '[[User_talk:%s|%s]]' % (user_name, user_name)
	user_contribs = '[[Special:Contributions/%s|contribs]]' % user_name
	email_user = '[[Special:EmailUser/%s|Yes]]' % user_name
	table_row = u'''| %d
| %s
| %d
| %s
| %s
|
|-''' % (number, talk_page, user_editcount, email_string, user_contribs)
	output1.append(table_row)


# autoconfirmed editors
cursor.execute('''
insert ignore into th_up_invitees
	(user_id, user_name, user_registration, user_editcount, email_status, sample_date, sample_type, invite_status, hostbot_invite, hostbot_personal, hostbot_skipped)
	SELECT
		user_id,
		user_name,
		user_registration,
		user_editcount,
		user_email_authenticated,
		NOW(),
		2,
		0,
		0,
		0,
		0
			from enwiki.user 
				where user_editcount > 10 
				and user_registration 
					between DATE_FORMAT(DATE_SUB(NOW(),INTERVAL 5 DAY),'%Y%m%d%H%i%s') 
					and DATE_FORMAT(DATE_SUB(NOW(),INTERVAL 4 DAY),'%Y%m%d%H%i%s')
					AND user_name not in 
						(SELECT REPLACE(log_title,"_"," ") from enwiki.logging 
							where log_type = "block" 
							and log_action = "block" 
							and log_timestamp >  DATE_FORMAT(DATE_SUB(NOW(),INTERVAL 5 DAY),'%Y%m%d%H%i%s'));
''')
conn.commit()

cursor.execute('''
SELECT
id,
user_name,
user_editcount,
email_status
FROM th_up_invitees
WHERE date(sample_date) = date(NOW())
AND sample_type = 2;
''')

output2 = []
fields = cursor.fetchall()
for field in fields:
	number = field[0]
	user_name = unicode(field[1], 'utf-8')	
	user_editcount = field[2]
	email_status = field[3]
	email_string = "No"
	if email_status is not None:
		email_string = '[[Special:EmailUser/%s|Yes]]' % user_name
	talk_page = '[[User_talk:%s|%s]]' % (user_name, user_name)
	user_contribs = '[[Special:Contributions/%s|contribs]]' % user_name
	table_row = u'''| %d
| %s
| %d
| %s
| %s
|
|-''' % (number, talk_page, user_editcount, email_string, user_contribs)
	output2.append(table_row)	
	

#updates the sample type. Used to divide users into experimental and control groups. Now its all experimental, baby.
cursor.execute('''
UPDATE th_up_invitees
SET sample_group = "exp"
WHERE date(sample_date) = date(NOW());
''')
conn.commit()

#adds in talkpage ids for later link checks
cursor.execute('''
UPDATE jmorgan.th_up_invitees as i, enwiki.page as p
SET i.user_talkpage = p.page_id
WHERE date(i.sample_date) = date(NOW())
AND p.page_namespace = 3
AND REPLACE(i.user_name, " ", "_") = p.page_title;
''')

conn.commit()


report = wikitools.Page(wiki, report_title)
report_text = report_template % ('\n'.join(output1), '\n'.join(output2))
report_text = report_text.encode('utf-8')
report.edit(report_text, section=1, summary="Automatic daily invitee report generated by [[User:HostBot|HostBot]].", bot=1)

cursor.close()
conn.close()
	

