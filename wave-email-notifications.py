#!/usr/bin/env python

"""
Google Wave Email Notifications it's a wave robot that sends an email to the
participants of a wave whenever the wave is updated. It only sends the
notification once until the participant reads the updated wave.
"""
import urllib
import logging

from google.appengine.api.labs import taskqueue

from waveapi import events
from waveapi import robot

import model
import preferences
from util import *


def notify_initial(context, wavelet, participants, modified_by, message):
    for participant in participants:
        if participant == ROBOT_ADDRESS: continue

        url = preferences.get_url(participant, wavelet.waveId, 'enable')

        pp = model.get_pp(participant)
        pwp = model.get_pwp(participant, wavelet.waveId)
        if not pwp or not pp: # or not pp.preferencesWaveId:
            #preferences.create_pwp_form(context, participant)
            send_notification(wavelet, participant, modified_by,
                              '%s\n\n%s' % (message, url), ignore=True)
        #if not pp or not pp.preferencesWaveId:
        #    preferences.create_pp_form(context, participant)


def notify(wavelet, modified_by, message):
    for participant in wavelet.participants:
        if participant != ROBOT_ADDRESS and participant != modified_by:
            send_notification(wavelet, participant, modified_by, message)


def send_notification(wavelet, participant, mail_from, message, ignore=False):
    if not message.strip(): return

    logging.debug('adding task to send_email_prepare queue for %s => %s'
                  % (wavelet.waveId, participant))

    taskqueue.Task(url='/send_email/prepare',
                   params={ 'title': wavelet.title,
                            'waveId': wavelet.waveId,
                            'waveletId': wavelet.waveletId,
                            'participant': participant,
                            'mail_from': mail_from,
                            'message': message,
                            'ignore': ignore }).add(queue_name='send-email-prepare')


class NotificationsRobot(robot.Robot):
    """
    This is the main notifications robot class
    """

    def __init__(self):
        robot.Robot.__init__(self, ROBOT_NAME, 
                             image_url='%s/inc/icon.png' % ROBOT_BASE_URL,
                             version='9', profile_url=ROBOT_BASE_URL)

        self.RegisterListener(self)

    def on_wavelet_self_added(self, event, context):
        logging.debug('on_wavelet_self_added')
        wavelet = context.GetRootWavelet()
        preferencesWaveId = preferences.get_preferencesWaveId(context)

        if preferencesWaveId:
            logging.debug('preferences wave')
            for participant in wavelet.participants:
                pp = model.get_pp(participant)
                if pp.preferencesWaveId != preferencesWaveId:
                    wavelet.SetDataDocument(ROBOT_ADDRESS, wavelet.waveId)
                    pp.preferencesWaveId = wavelet.waveId;
                    pp.put()

        else:
            logging.debug('normal wave')
            modified_by = event.modifiedBy
            message = 'The notifiy robot has been added to this wave. ' + INITIAL_MESSAGE
            participants = wavelet.participants
            notify_initial(context, wavelet, participants, modified_by, message)

    def on_wavelet_self_removed(self, event, context):
        logging.debug('on_wavelet_self_removed')
        if preferences.is_preferences_wave(context): return

        wavelet = context.GetRootWavelet()
        preferences.clear(wavelet.waveId)
        # TODO delete also the private replies

    def on_wavelet_participants_changed(self, event, context):
        logging.debug('on_wavelet_participants_changed')
        if preferences.is_preferences_wave(context): return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        message = '%s added you as a participant to this wave.' % modified_by + INITIAL_MESSAGE
        participants = event.properties[events.PARTICIPANTS_ADDED]
        notify_initial(context, wavelet, participants, modified_by, message)

    def on_blip_submitted(self, event, context):
        logging.debug('on_blip_submitted')
        if preferences.is_preferences_wave(context): return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        blip = get_blip(context, event)
        if blip:
            content = blip.content
            notify(wavelet, modified_by, content)

    def on_blip_deleted(self, event, context):
        logging.debug('on_blip_deleted')
        if preferences.is_preferences_wave(context): return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        notify(wavelet, modified_by, '*** Some content was deleted from the wave ***')

    def on_form_button_clicked(self, event, context):
        logging.debug('on_form_button_clicked')
        if not preferences.is_preferences_wave(context): return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        blip = get_blip(context, event)
        form = blip.GetElements()

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

