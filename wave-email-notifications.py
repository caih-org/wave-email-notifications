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


def new_participants(properties, context):
    wave = get_wave(context)
    for participant in properties[events.PARTICIPANTS_ADDED]:
        send_notification(wave, participant,
                          'You have been added as a participant to the "%s" wave. It is available at the following url:'
                          % wave.title)


def notify(properties, context):
    wave = get_wave(context)
    for participant in wave.participants:    
        send_notification(wave, participant,
                          'The "%s" wave has been updated. Please visit the following url to see the changes:'
                          % wave.title)


def send_notification(wave, participant, message):
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


if __name__ == '__main__':
    myRobot = robot.Robot(ROBOT_NAME, 
                          image_url='%s/icon.png' % ROBOT_BASE_URL,
                          version='1',
                          profile_url=ROBOT_BASE_URL)

    myRobot.RegisterHandler(events.WAVELET_PARTICIPANTS_CHANGED, new_participants)
    myRobot.RegisterHandler(events.WAVELET_TIMESTAMP_CHANGED, notify)

    myRobot.Run()
