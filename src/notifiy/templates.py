# -*- coding: UTF-8 -*-

###################################################
# General mail template
###################################################

MESSAGE_TEMPLATE = u'''\
%s

---
Reply to this message to add a blip to the wave
Visit this wave: %s
Change global notification preferences: %s
To unsubscribe please visit your preferences or send an email to: %s
'''

NOTIFY_ONCE_TEMPLATE = u'''\
%s

[NOTE: you will not recive further messages until you visit this wave]
'''

###################################################
# Individual email messages
###################################################

INITIAL_MESSAGE = u'To receive email notifications visit this wave and activate them.'

ROBOT_ADDED = u'The notifiy robot has been added to this wave. '

ADDED_MESSAGE = u'%s added you as a participant to this wave.'

CONTENT_DELETED = u'Some content was deleted from the wave'

CONTENT_SUPRESSED = u'%s... [some content was supressed]'

PHONE_MESSAGE = 'The wave "%s" has been updated by %s: "%s..."'

###################################################
# Unsubscribed messages
###################################################

UNSUBSCRIBED_SUBJECT = u'Unsubscribed'

UNSUBSCRIBED_BODY = u'Your email has been unsubscribed from the Notifiy robot. \
To receive notifications again please visit Google Wave and update your preferences. \
Your email may still show there, just click the refresh button.'

###################################################
# Preferences wave messages
###################################################

COMMANDS_HELP = u'''
help: Show this help
refresh: Recreate the preferences wave
clean: Clean all messages in this wave.
regen: Regenerate the activation code.
reset: Reset your specific wave preferenes (for all waves) and refresh this form.
'''

COMMAND_SUCCESSFUL = u'Command %s ran successfully'

COMMAND_UNKNOWN = u'Command %s not found'

PREFERENCES_SAVED = u'Preferences saved'

ERROR_TRY_AGAIN = u'There was an error, please try again in a few moments'
