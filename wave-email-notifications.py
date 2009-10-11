#!/usr/bin/env python

"""
Google Wave Email Notifications it's a wave robot that sends an email to the
participants of a wave whenever the wave is updated. It only sends the
notification once until the participant reads the updated wave.
"""
import urllib

from google.appengine.api import mail

from waveapi import events
from waveapi import model
from waveapi import robot

from model import ParticipantPreferences, ParticipantWavePreferences

ROBOT_NAME = 'wave-email-notifications'
ROBOT_ADDRESS = "%s@appspot.com" % ROBOT_NAME
ROBOT_BASE_URL = 'http://%s.appspot.com' % (ROBOT_NAME)


def get_wavelet(context):
    return context.wavelets.values()[0]


def get_url(participant, waveId):
    domain = participant.split('@')[1]
    if domain == 'google.com':
        return 'https://wave.google.com/wave/#restored:wave:%s' % waveId
    else:
        return 'invalid domain!!!'


def notify(wavelet, modifiedBy, message):
    for participant in wavelet.participants:
        if participant != modifiedBy:
            send_notification(wavelet, participant, modifiedBy, message)


def send_notification(wavelet, participant, mail_from, message):
    query = ParticipantPreferences.all()
    query.filter('participant =', participant)
    pp = query.get()

    if not pp:
        pp = ParticipantPreferences(participant=participant)
        pp.put()
    elif not pp.notify:
        return

    query = ParticipantWavePreferences.all()
    query.filter('participant =', participant)
    query.filter('waveId =', wavelet.waveId)
    pwp = query.get()

    if not pwp:
        pwp = ParticipantWavePreferences(participant=participant,
                                         waveId=wavelet.waveId)
        pwp.put()
    elif not pwp.notify:
        return

    url = get_url(participant, urllib.quote(wavelet.waveId))
    prefs_url = '%s/prefs/%s/%s/' % (ROBOT_BASE_URL, urllib.quote(participant),
                                     urllib.quote(wavelet.waveId))
    subject = '[wave] %s' % wavelet.title
    body = '''
%s

%s

To change your notification preferences please visit:

%s
''' % (message, url, prefs_url)

    mail.send_mail(mail_from, participant, subject, body)


class NotificationsRobot(robot.Robot):

    def __init__(self,):
        robot.Robot.__init__(self, ROBOT_NAME, 
                             image_url='%s/icon.png' % ROBOT_BASE_URL,
                             version='2', profile_url=ROBOT_BASE_URL)

        self.RegisterListener(self)

    def on_wavelet_participants_changed(self, event, context):
        wavelet = get_wavelet(context)
        modifiedBy = event.modifiedBy
        for participant in event.properties[events.PARTICIPANTS_ADDED]:
            send_notification(wavelet, participant, modifiedBy,
                              'You have been added as a participant to the "%s" wave. It is available at the following url:'
                              % wavelet.title)

    def on_blip_submitted(self, event, context):
        wavelet = get_wavelet(context)
        modifiedBy = event.modifiedBy
        notify(wavelet, modifiedBy,
               'The "%s" wave has been updated by %s. Please visit the following url to see the changes:'
               % (wavelet.title, modifiedBy))

    def on_blip_deleted(self, event, context):
        wavelet = get_wavelet(context)
        modifiedBy = event.modifiedBy
        notify(wavelet, modifiedBy,
               'The "%s" wave has been updated by %s. Please visit the following url to see the changes:'
               % (wavelet.title, modifiedBy))


if __name__ == '__main__':
    NotificationsRobot().Run()
