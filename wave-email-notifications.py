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
        wavelet = context.GetRootWavelet()
        wavelet_type = get_type(event, context)

        if wavelet_type == WAVELET_TYPE.PREFERENCES:
            for participant in wavelet.participants:
                set_preferencesWaveId(context, modified_by, wavelet)

        elif wavelet_type == WAVELET_TYPE.NORMAL:
            modified_by = event.modifiedBy
            message = 'The notifiy robot has been added to this wave. ' + INITIAL_MESSAGE
            participants = wavelet.participants
            init_wave(event, context)

            notify_initial(context, wavelet, participants, modified_by, message)

    def on_wavelet_participants_changed(self, event, context):
        if get_type(event, context) != WAVELET_TYPE.NORMAL: return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        message = '%s added you as a participant to this wave.' % modified_by + INITIAL_MESSAGE
        participants = event.properties[events.PARTICIPANTS_ADDED]

        notify_initial(context, wavelet, participants, modified_by, message)

    def on_blip_submitted(self, event, context):
        if get_type(event, context) != WAVELET_TYPE.NORMAL: return

        wavelet = context.GetRootWavelet()
        blip = get_blip(event, context)
        modified_by = event.modifiedBy
        if not blip or not wavelet: return

        notify(event, context, wavelet, modified_by, blip.content)

    def on_blip_deleted(self, event, context):
        if get_type(event, context) != WAVELET_TYPE.NORMAL: return

        wavelet = context.GetRootWavelet()
        if not wavelet: return

        modified_by = event.modifiedBy
        notify(event, context, wavelet, modified_by,
                '*** Some content was deleted from the wave ***')

    def on_form_button_clicked(self, event, context):
        if get_type(event, context) != WAVELET_TYPE.PREFERENCES: return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy
        blip = get_blip(event, context)
        form = blip.GetElements()

        if event.properties['button'] == 'save_pp':
            pp = get_pp(modified_by, context=context)
            pp.notify = get_form_element(form, 'notify').value
            pp.email = get_form_element(form, 'email').value
            pp.put()

        elif event.properties['button'] == 'exec_pp':
            command = get_form_element(form, 'command').value
            logging.debug('executing command: %s' % command)
            # FIXME add commands

    def on_document_changed(self, event, context):
        if get_type(event, context) != WAVELET_TYPE.PREFERENCES: return

        wavelet = context.GetRootWavelet()
        modified_by = event.modifiedBy

        set_preferencesWaveId(context, modified_by, wavelet)

    def on_wavelet_self_removed(self, event, context):
        wavelet_type = get_type(event, context)
        wavelet = context.GetRootWavelet()

        if wavelet_type == WAVELET_TYPE.PREFERENCES:
            for participant in wavelet.participants:
                pp = get_pp(participant, context=context)
                pp.preferencesWaveId = None;
                pp.put()
        elif wavelet_type == WAVELET_TYPE.NORMAL:
            # TODO delete the widget
            pass


if __name__ == '__main__':
    NotificationsRobot().Run()

