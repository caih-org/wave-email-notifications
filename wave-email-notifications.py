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

ROBOT_NAME = 'wave-email-notifications'
ROBOT_ADDRESS = "%s@appspot.com" % ROBOT_NAME
ROBOT_BASE_URL = 'http://%s.appspot.com/' % (ROBOT_NAME)


def get_wave(context):
    return context.waves[context.wavelets.values()[0]]


def notify(wave, modifiedBy, message):
    wave = get_wave(context)
    for participant in wave.participants:
        if participant != modifiedBy:
            send_notification(wave, participant, message)


def send_notification(wave, participant, message):
    query = model.ParticipantPreferences.all()
    query.filter('participant =', path_parts[2])
    pp = query.get()

    if not pp:
        pp = model.ParticipantPreferences(participant=participant)
        pp.put()
    elif not pp.notify:
        return

    query = model.ParticipantWavePreferences.all()
    query.filter('participant =', path_parts[2])
    query.filter('waveId =', path_parts[3])
    pwp = query.get()

    if not pwp:
        pwp = model.ParticipantWavePreferences(participant=participant, waveId=wave.waveId)
        pwp.put()
    elif not pwp.notify:
        return

    url = 'https://wave.google.com/wave/#restored:wave:%s' % urllib.quote(wave.waveId)
    prefs_url = '%s/prefs/%s/%s/' % (ROBOT_BASE_URL, urllib.quote(participant), urllib.quote(wave.waveId))
    subject = '[wave] %s' % wave.title
    body = '''
%s

%s

To change your notification preferences please visit:

%s
''' % (message, url, prefs_url)

    mail.send_mail(ROBOT_ADDRESS, participant, subject, body)


class NotificationsRobot(robot.Robot):

    def __init__(self,):
        Robot.__init__(self, ROBOT_NAME, 
                       image_url='%s/icon.png' % ROBOT_BASE_URL, version='1',
                       profile_url=ROBOT_BASE_URL)

        self.RegisterListener(self)

    def on_wavelet_participants_changed(properties, context):
        wave = get_wave(context)
        for participant in properties[events.PARTICIPANTS_ADDED]:
            send_notification(wave, participant,
                              'You have been added as a participant to the "%s" wave. It is available at the following url:'
                              % wave.title)

    def on_blip_submitted(properties, context):
        wave = get_wave(context)
        modifiedBy = properties['modifiedBy']
        notify(wave, modifiedBy,
               'The "%s" wave has been updated by %s. Please visit the following url to see the changes:'
               % wave.title)

    def on_blip_deleted(properties, context):
        wave = get_wave(context)
        modifiedBy = properties['modifiedBy']
        notify(wave, modifiedBy,
               'The "%s" wave has been updated by %s. Please visit the following url to see the changes:'
               % wave.title)

    def on_document_changed(properties, context):
        wave = get_wave(context)
        modifiedBy = properties['modifiedBy']
        notify(wave, modifiedBy,
               'The "%s" wave has been updated by %s. Please visit the following url to see the changes:'
               % wave.title)


if __name__ == '__main__':
    NotificationsRobot().run()
