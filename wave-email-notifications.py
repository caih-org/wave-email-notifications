#!/usr/bin/env python

"""
Google Wave Email Notifications it's a wave robot that sends an email to the
participants of a wave whenever the wave is updated. It only sends the
notification once until the participant reads the updated wave.
"""
import urllib

from google.appengine.api import mail

from waveapi import document
from waveapi import events
from waveapi import model
from waveapi import robot

from model import ParticipantPreferences, ParticipantWavePreferences

ROBOT_NAME = 'notifiy'
ROBOT_ID = 'wave-email-notifications'
ROBOT_ADDRESS = "%s@appspot.com" % ROBOT_ID
ROBOT_BASE_URL = 'http://%s.appspot.com' % (ROBOT_ID)
ROBOT_EMAIL = "wave-email-notifications@caih.org"
ROBOT_HOME_PAGE = "http://wave-email-notifications.googlecode.com/"


def get_wavelet(context):
    return context.wavelets.values()[0]


def get_url(participant, waveId):
    domain = participant.split('@')[1]
    if domain == 'googlewave.com':
        return 'https://wave.google.com/wave/#restored:wave:%s' % urllib.quote(waveId)
    else:
        return 'invalid domain!!!'


def notify(wavelet, modified_by, message):
    for participant in wavelet.participants:
        if participant != modified_by:
            send_notification(wavelet, participant, modified_by, message)


def get_pp(participant, create=False):
    query = ParticipantPreferences.all()
    query.filter('participant =', participant)
    pp = query.get()

    if create and not pp:
        pp = ParticipantPreferences(participant=participant)
        # FIXME This should be more generic
        pp.email = participant.replace('@googlewave.com', '@gmail.com')
        pp.put()

    return pp


def get_pwp(participant, waveId, create=False):
    query = ParticipantWavePreferences.all()
    query.filter('participant =', participant)
    query.filter('waveId =', waveId)
    pwp = query.get()

    if create and not pwp:
        pwp = ParticipantWavePreferences(participant=participant,
                                         waveId=waveId)
        pwp.put()

    return pwp


def send_notification(wavelet, participant, mail_from, message):
    if not message.strip():
        return

    pp = get_pp(participant, create=True)

    if not pp.notify or not mail.is_email_valid(pp.email):
        return

    pwp = get_pwp(participant, waveId, create=True)

    if not pwp.notify:
        return

    url = get_url(participant, urllib.quote(wavelet.waveId))
    prefs_url = '%s/prefs/%s/%s/' % (ROBOT_BASE_URL, urllib.quote(participant),
                                     wavelet.waveId)
    subject = '[wave] %s' % wavelet.title
    body = '''%s

======
Visit this wave: %s
Change notification preferences: %s
''' % (message, url, prefs_url)

    mail.send_mail('%s <%s>' % (mail_from.replace('@', ' at '), ROBOT_EMAIL),
                   pp.email, subject, body, reply_to=mail_from)


class NotificationsRobot(robot.Robot):

    def __init__(self,):
        robot.Robot.__init__(self, ROBOT_NAME, 
                             image_url='%s/inc/icon.png' % ROBOT_BASE_URL,
                             version='7', profile_url=ROBOT_BASE_URL)

        self.RegisterListener(self)

    def on_wavelet_self_added(self, event, context):
        wavelet = get_wavelet(context)
        modified_by = event.modifiedBy
        message = 'The Notify Robot has been added to this wave. To receive \
email notifications for this wave visit the preferences at the following link \
and activate them.'
        for participant in wavelet.participants:
            if not get_pwp(participant, wavelet.waveId):
                send_notification(wavelet, participant, modified_by, message)

    def on_wavelet_participants_changed(self, event, context):
        wavelet = get_wavelet(context)
        modified_by = event.modifiedBy
        message = '%s added you as a participant to the "%s" wave.' \
                  % (wavelet.title, modified_by)
        for participant in event.properties[events.PARTICIPANTS_ADDED]:
            send_notification(wavelet, participant, modified_by, message)

    def on_blip_submitted(self, event, context):
        wavelet = get_wavelet(context)
        modified_by = event.modifiedBy
        content = context.GetBlipById(event.properties["blipId"]).content
        notify(wavelet, modified_by, content)

    def on_blip_deleted(self, event, context):
        wavelet = get_wavelet(context)
        modified_by = event.modifiedBy
        content = context.GetBlipById(event.properties["blipId"]).content
        notify(wavelet, modified_by, '***The following content was deleted from the wave***\n\n%s' % content)


if __name__ == '__main__':
    NotificationsRobot().Run()

