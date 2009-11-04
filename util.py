import urllib


ROBOT_NAME = 'notifiy'
ROBOT_ID = 'wave-email-notifications'
ROBOT_ADDRESS = "%s@appspot.com" % ROBOT_ID
ROBOT_BASE_URL = 'http://%s.appspot.com' % (ROBOT_ID)
ROBOT_EMAIL = "wave-email-notifications@ecuarock.net"
ROBOT_HOME_PAGE = "http://wave-email-notifications.googlecode.com/"

INITIAL_MESSAGE = 'To receive email notifications for this wave visit the \
preferences at the following link and activate them.'

MESSAGE_TEMPLATE = '''\
%s

======
Visit this wave: %s
Change notification preferences: %s
[%s:%s]
'''


def get_blip(context, event):
    return context.GetBlipById(event.properties["blipId"])


def get_url(participant, waveId):
    domain = participant.split('@')[1]
    if waveId and domain == 'googlewave.com':
        return 'https://wave.google.com/wave/#restored:wave:%s' % urllib.quote(waveId)
    else:
        return 'invalid domain!!!'

