#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

import base64

from waveapi.util import StringEnum

ME = 'cesar.izurieta@googlewave.com'

ROBOT_NAME = 'notifiy'
ROBOT_ID = 'wave-email-notifications'
ROBOT_ADDRESS = '%s@appspot.com' % ROBOT_ID
ROBOT_BASE_URL = 'http://%s.appspot.com' % ROBOT_ID
ROBOT_EMAIL = '%s@ecuarock.net' % ROBOT_ID
ROBOT_HOME_PAGE = 'http://%s.googlecode.com/' % ROBOT_ID

GADGET_URL = '%s/%s.xml' % (ROBOT_BASE_URL, ROBOT_ID)

INITIAL_MESSAGE = u'To receive email notifications visit this wave and activate them.'
ROBOT_ADDED = u'The notifiy robot has been added to this wave. '
ADDED_MESSAGE = u'%s added you as a participant to this wave.'
CHANGES_MESSAGE = u'There are updates to this wave.'
MESSAGE_TEMPLATE = u'''\
%s

---
Visit this wave: %s
Change global notification preferences: %s
To unsubscribe please visit your preferences or send an email to: %s
'''
CONTENT_DELETED = u'*** Some content was deleted from the wave ***'
CONTENT_SUPRESSED = u'%s... [some content was supressed from this email]'
COMMANDS_HELP = u'''
help: Show this help
refresh: Recreate the preferences wave
clean: Clean all messages in this wave.
reset: Reset your specific wave preferenes (for all waves) and refresh this form.
'''
COMMAND_SUCCESSFUL = u'Command %s ran successfully'
COMMAND_UNKNOWN = u'Command %s not found'
PREFERENCES_SAVED = u'Preferences saved'
ERROR_TRY_AGAIN = u'There was an error, please try again in a few moments'
UNSUBSCRIBED_SUBJECT = u'Unsubscribed'
UNSUBSCRIBED = u'Your email has been unsubscribed from the Notifiy robot. To receive notifications again please visit Google Wave and update your preferences. Your email may still show there, just click the refresh button.'

WAVELET_TYPE = StringEnum('NORMAL', 'PREFERENCES')
SETTIE_ROBOT = 'settie@a.gwave.com'

PREFERENCES_WAVEID_DATA_DOC = '%s/preferencesWaveId' % ROBOT_ADDRESS
PREFERENCES_VERSION_DATA_DOC = '%s/preferencesVersion' % ROBOT_ADDRESS
PREFERENCES_VERSION = '10'
PARTICIPANT_DATA_DOC = '%s/%s/notify' % (ROBOT_ADDRESS, '%s')


##########################################################
# General utils

def modified_b64encode(s):
    if type(s) == unicode:
        s = s.decode('UTF-8')

    return base64.urlsafe_b64encode(s).replace('=', '')

def modified_b64decode(s):
    while len(s) % 4 != 0:
        s = s + '='

    return base64.urlsafe_b64decode(s).encode('UTF-8')


