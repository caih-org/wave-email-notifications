#!/usr/bin/env python

"""
Google Wave Email Notifications it's a wave robot that sends an email to the
participants of a wave whenever the wave is updated. It only sends the
notification once until the participant reads the updated wave.
"""
import urllib
import logging

from google.appengine.api import mail

from waveapi import events
from waveapi import robot

import model
import preferences
from util import *


def notify_initial(context, wavelet, participants, modified_by, message):
    for participant in participants:
        pp = model.get_pp(participant)
        pwp = model.get_pwp(participant, wavelet.waveId)
        if not pwp or not pp or not pp.preferencesWaveId:
            preferences.create_pwp_form(context, participant)
            send_notification(wavelet, participant, modified_by, message,
                              ignore=True)
        if not pp or not pp.preferencesWaveId:
            preferences.create_pp_form(context, participant)


def notify(wavelet, modified_by, message):
    for participant in wavelet.participants:
        if participant != modified_by:
            send_notification(wavelet, participant, modified_by, message)


def send_notification(wavelet, participant, mail_from, message, ignore=False):
    if not message.strip(): return

    pp = model.get_pp(participant, create=True)

    if not pp.notify or not mail.is_email_valid(pp.email): return

    pwp = model.get_pwp(participant, wavelet.waveId, create=True)

    if not ignore and not pwp.notify: return

    url = get_url(participant, urllib.quote(wavelet.waveId))
    prefs_url = preferences.get_preferences_url(participant, wavelet.waveId)
    subject = '[wave] %s' % wavelet.title
    body = '''%s

======
Visit this wave: %s
Change notification preferences: %s
[[[%s:%s]]]
''' % (message, url, prefs_url, wavelet.waveId, wavelet.waveletId)

    logging.debug('emailing %s "%s"' % (participant, message))
    mail.send_mail('%s <%s>' % (mail_from.replace('@', ' at '), ROBOT_EMAIL),
                   pp.email, subject, body, reply_to=mail_from)


initial_message = 'To receive email notifications for this wave visit the \
preferences at the following link and activate them.'


class NotificationsRobot(robot.Robot):

    def __init__(self):
        robot.Robot.__init__(self, ROBOT_NAME, 
                             image_url='%s/inc/icon.png' % ROBOT_BASE_URL,
                             version='8', profile_url=ROBOT_BASE_URL)

        self.RegisterListener(self)

    def on_wavelet_self_added(self, event, context):
        if preferences. filter_preferences(context): return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        message = 'The notifiy robot has been added to this wave. ' + initial_message
        participants = wavelet.participants
        notify_initial(context, wavelet, participants, modified_by, message)

    def on_wavelet_participants_changed(self, event, context):
        if preferences. filter_preferences(context): return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        message = '%s added you as a participant to this wave.' % modified_by + initial_message
        participants = event.properties[events.PARTICIPANTS_ADDED]
        notify_initial(context, wavelet, participants, modified_by, message)

    def on_blip_submitted(self, event, context):
        if preferences. filter_preferences(context): return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        content = get_blip(context, event).content
        notify(wavelet, modified_by, content)

    def on_blip_deleted(self, event, context):
        if preferences. filter_preferences(context): return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        notify(wavelet, modified_by, '*** Some content was deleted from the wave ***')

    def on_form_button_clicked(self, event, context):
        if preferences. filter_preferences(context): return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        blip = get_blip(context, event)
        form = blip.GetDocument().GetFormElements()

        if event.properties.button == 'save_pp':
            pp = model.get_pp(modified_by)
            pp.preferencesWaveId = newwave.waveId;
            pp.notify = form["notify"].GetValue()
            pp.email = form["email"].GetValue()
            pp.put()
        elif event.properties.button == 'save_pwp':
            pwp = model.get_pwp(modified_by, wavelet.waveId)
            pwp.notify = form["notify"].GetValue()
            pwp.put()


if __name__ == '__main__':
    NotificationsRobot().Run()

