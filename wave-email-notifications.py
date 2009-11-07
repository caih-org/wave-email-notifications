#!/usr/bin/env python

"""
Google Wave Email Notifications it's a wave robot that sends an email to the
participants of a wave whenever the wave is updated. It only sends the
notification once until the participant reads the updated wave.
"""
import logging

from waveapi import events
from waveapi import robot

import model
import preferences
from util import *


class NotificationsRobot(robot.Robot):
    """
    This is the main notifications robot class
    """

    def __init__(self):
        robot.Robot.__init__(self, ROBOT_NAME, 
                             image_url='%s/favicon.png' % ROBOT_BASE_URL,
                             version='11', profile_url=ROBOT_BASE_URL)

        self.RegisterListener(self)

    def on_wavelet_self_added(self, event, context):
        logging.debug('on_wavelet_self_added')
        wavelet = context.GetRootWavelet()
        preferencesWaveId = preferences.get_preferencesWaveId(context)

        if preferencesWaveId:
            logging.debug('preferences wave')
            for participant in wavelet.participants:
                pp = get_pp(participant, context=context)
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

    def on_wavelet_participants_changed(self, event, context):
        logging.debug('on_wavelet_participants_changed')
        if preferences.is_preferences_wave(context): return
        logging.debug('processing on_wavelet_participants_changed')

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        message = '%s added you as a participant to this wave.' % modified_by + INITIAL_MESSAGE
        participants = event.properties[events.PARTICIPANTS_ADDED]
        notify_initial(context, wavelet, participants, modified_by, message)

    def on_blip_submitted(self, event, context):
        logging.debug('on_blip_submitted')
        if preferences.is_preferences_wave(context): return
        logging.debug('processing on_blip_submitted')

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        blip = get_blip(context, event)

        if blip:
            content = blip.content
            notify(context, wavelet, modified_by, content)

    def on_blip_deleted(self, event, context):
        logging.debug('on_blip_deleted')
        if preferences.is_preferences_wave(context): return
        logging.debug('processing on_blip_deleted')

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        notify(context, wavelet, modified_by, '*** Some content was deleted from the wave ***')

    def on_form_button_clicked(self, event, context):
        logging.debug('on_form_button_clicked')
        if not preferences.is_preferences_wave(context): return
        logging.debug('processing on_form_button_clicked')

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        blip = get_blip(context, event)
        form = blip.GetElements()

        if event.properties['button'] == 'save_pp':
            pp = get_pp(modified_by, context=context)
            pp.notify = get_form_element(form, 'notify').value
            pp.email = get_form_element(form, 'email').value
            pp.put()

        elif event.properties['button'] == 'save_pwp':
            pwp = get_pwp(modified_by, wavelet.waveId)
            pwp.notify = get_form_element(form, 'notify').value
            pwp.put()

        elif event.properties['button'] == 'exec_pp':
            command = get_form_element(form, 'command').value
            logging.debug('executing command: %s' % command)
            # FIXME add commands

    def on_document_changed(self, event, context):
        logging.debug('on_document_changed')
        if not preferences.is_preferences_wave(context): return
        logging.debug('processing on_document_changed')

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy

        pp = get_pp(modified_by, context=context)
        if pp:
            pp.preferencesWaveId = wavelet.waveId;
            pp.put()

    def on_wavelet_self_removed(self, event, context):
        logging.debug('on_wavelet_self_removed')
        wavelet = context.GetRootWavelet()
        preferencesWaveId = preferences.get_preferencesWaveId(context)
        modified_by = event.modifiedBy

        if preferencesWaveId:
            pp = get_pp(modified_by, context=context)
            pp.preferencesWaveId = None;
            pp.put()
        else:
            wavelet = context.GetRootWavelet()
            preferences.clear(wavelet.waveId)
            # TODO delete also the private replies


if __name__ == '__main__':
    NotificationsRobot().Run()

