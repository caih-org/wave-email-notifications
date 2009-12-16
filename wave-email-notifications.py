#!/usr/bin/env python

"""
Google Wave Email Notifications it's a wave robot that sends an email to the
participants of a wave whenever the wave is updated. It only sends the
notification once until the participant reads the updated wave.
"""
import logging

from waveapi import events
from waveapi import robot

from google.appengine.ext import db

import model
from util import *


class NotificationsRobot(robot.Robot):
    """
    This is the main notifications robot class
    """

    def __init__(self):
        robot.Robot.__init__(self, ROBOT_NAME, 
                             image_url='%s/favicon.png' % ROBOT_BASE_URL,
                             version='13', profile_url=ROBOT_BASE_URL)

        self.RegisterListener(self)

    def on_wavelet_self_added(self, event, context):
        wavelet = get_wavelet(event, context)
        wavelet_type = get_type(event, context)
        modified_by = event.modifiedBy

        if wavelet_type == WAVELET_TYPE.PREFERENCES:
            for participant in wavelet.participants:
                set_preferencesWaveId(event, context, modified_by, wavelet)

        elif wavelet_type == WAVELET_TYPE.NORMAL:
            message = ROBOT_ADDED + INITIAL_MESSAGE
            participants = wavelet.participants
            init_wave(event, context)

            if get_notify_initial(context, participants):
                notify_initial(context, wavelet, participants, modified_by, message)

    def on_wavelet_participants_changed(self, event, context):
        if get_type(event, context) != WAVELET_TYPE.NORMAL: return

        wavelet = get_wavelet(event, context)
        modified_by = event.modifiedBy
        message = ADDED_MESSAGE % modified_by + INITIAL_MESSAGE
        participants = event.properties[events.PARTICIPANTS_ADDED]

        if get_notify_initial(context, participants):
            notify_initial(context, wavelet, participants, modified_by, message)

    def on_blip_submitted(self, event, context):
        if get_type(event, context) != WAVELET_TYPE.NORMAL: return

        wavelet = get_wavelet(event, context)
        blip = get_blip(event, context)
        modified_by = event.modifiedBy
        if not blip or not wavelet: return

        notify(event, context, wavelet, modified_by, blip.content)

    def on_blip_deleted(self, event, context):
        if get_type(event, context) != WAVELET_TYPE.NORMAL: return

        wavelet = get_wavelet(event, context)
        if not wavelet: return

        modified_by = event.modifiedBy
        notify(event, context, wavelet, modified_by, CONTENT_DELETED)

    def on_form_button_clicked(self, event, context):
        if get_type(event, context) != WAVELET_TYPE.PREFERENCES: return

        wavelet = get_wavelet(event, context)
        modified_by = event.modifiedBy
        set_preferencesWaveId(event, context, modified_by, wavelet)
        blip = get_blip(event, context)
        form = blip.GetElements()
        pp = get_pp(modified_by, context=context)
        #################
        pp1 = get_pp(modified_by, context=context)
        logging.warn(pp == pp1)
        #################

        if event.properties['button'] == 'save_pp':
            try:
                pp.notify = get_form_element(form, 'notify').value
                pp.notify_initial = get_form_element(form, 'notify_initial').value
                pp.email = get_form_element(form, 'email').value
                pp.put()
            except Exception, e:
                update_pp_form(context, wavelet, pp, True)
                reply_wavelet(wavelet, ERROR_TRY_AGAIN)
                logging.error(e)
            else:
                update_pp_form(context, wavelet, pp)
                reply_wavelet(wavelet, PREFERENCES_SAVED)

        elif event.properties['button'] == 'refresh_pp':
            update_pp_form(context, wavelet, pp, True)
            reply_wavelet(wavelet, COMMAND_SUCCESSFUL % 'refresh')

        elif event.properties['button'] == 'exec_pp':
            command = get_form_element(form, 'command').value
            logging.debug('executing command: %s' % command)
            if command == 'help':
                reply_wavelet(wavelet, COMMANDS_HELP)
                return

            if command == 'refresh':
                update_pp_form(context, wavelet, pp, True)
            elif command == 'reset':
                query = model.ParticipantWavePreferences.all()
                query.filter('participant =', modified_by)
                db.delete(query)
                update_pp_form(context, wavelet, pp, True)
            elif command == 'settings':
                a = model.ApplicationSettings(keyname='remote-server', value='http://citricstudio.com:8080/quickstart/sendNotification.action?uid=%s&token=%s&message=%s&author=%s')
                a.put()
            else:
                reply_wavelet(wavelet, COMMAND_UNKNOWN % command)
                return

            reply_wavelet(wavelet, COMMAND_SUCCESSFUL % command)

    def on_wavelet_self_removed(self, event, context):
        wavelet_type = get_type(event, context)
        wavelet = get_wavelet(event, context)

        if wavelet_type == WAVELET_TYPE.PREFERENCES:
            for participant in wavelet.participants:
                pp = get_pp(participant, context=context)
                pp.preferencesWaveId = None
                pp.put()
        elif wavelet_type == WAVELET_TYPE.NORMAL:
            # TODO delete the widget
            pass


if __name__ == '__main__':
    NotificationsRobot().Run()

