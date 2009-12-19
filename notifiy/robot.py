#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

"""
Google Wave Email Notifications it's a wave robot that sends an email to the
participants of a wave whenever the wave is updated. It only sends the
notification once until the participant reads the updated wave.
"""

import logging

from google.appengine.ext import db
from google.appengine.api import memcache

from waveapi import events
from waveapi import robot

from  . import constants
from  . import model
from  . import notifyutil
from  . import preferences
from  . import waveutil


class NotificationsRobot(robot.Robot):
    """
    This is the main notifications robot class
    """

    def __init__(self):
        robot.Robot.__init__(self, constants.ROBOT_NAME,
                             image_url='%s/favicon.png' % constants.ROBOT_BASE_URL,
                             version='13', profile_url=constants.ROBOT_BASE_URL)

        self.RegisterListener(self)

    def on_wavelet_self_added(self, event, context):
        wavelet = waveutil.get_wavelet(event, context)
        wavelet_type = preferences.get_type(event, context)

        if wavelet_type == constants.WAVELET_TYPE.PREFERENCES:
            for participant in wavelet.participants:
                if participant == constants.ROBOT_ADDRESS: continue
                preferences.set_preferencesWaveId(event, context, participant, wavelet)

        elif wavelet_type == constants.WAVELET_TYPE.NORMAL:
            modified_by = event.modifiedBy
            message = constants.ROBOT_ADDED + constants.INITIAL_MESSAGE
            participants = wavelet.participants
            notifyutil.init_wave(event, context)

            if notifyutil.get_notify_initial(context, participants):
                notifyutil.notify_initial(context, wavelet, participants, modified_by, message)

    def on_wavelet_participants_changed(self, event, context):
        if preferences.get_type(event, context) != constants.WAVELET_TYPE.NORMAL: return

        wavelet = waveutil.get_wavelet(event, context)
        modified_by = event.modifiedBy
        message = constants.ADDED_MESSAGE % modified_by + constants.INITIAL_MESSAGE
        participants = event.properties[events.PARTICIPANTS_ADDED]

        if notifyutil.get_notify_initial(context, participants):
            notifyutil.notify_initial(context, wavelet, participants, modified_by, message)

    def on_blip_submitted(self, event, context):
        if preferences.get_type(event, context) != constants.WAVELET_TYPE.NORMAL: return

        wavelet = waveutil.get_wavelet(event, context)
        blip = waveutil.get_blip(event, context)
        if not blip or not wavelet: return

        modified_by = event.modifiedBy
        notifyutil.notify(event, context, wavelet, modified_by, blip.content)

    def on_blip_deleted(self, event, context):
        if preferences.get_type(event, context) != constants.WAVELET_TYPE.NORMAL: return

        wavelet = waveutil.get_wavelet(event, context)
        if not wavelet: return

        modified_by = event.modifiedBy
        notifyutil.notify(event, context, wavelet, modified_by, constants.CONTENT_DELETED)

    def on_form_button_clicked(self, event, context):
        if preferences.get_type(event, context) != constants.WAVELET_TYPE.PREFERENCES: return

        wavelet = waveutil.get_wavelet(event, context)
        blip = waveutil.get_blip(event, context)
        modified_by = event.modifiedBy
        preferences.set_preferencesWaveId(event, context, modified_by, wavelet)
        form = blip.GetElements()

        pp = preferences.get_pp(modified_by, context=context)
        if event.properties['button'] == 'save_pp':
            try:
                pp.notify = waveutil.get_form_element(form, 'notify').value
                pp.notify_initial = waveutil.get_form_element(form, 'notify_initial').value
                pp.email = waveutil.get_form_element(form, 'email').value
                pp.put()
            except Exception, e:
                preferences.update_pp_form(context, wavelet, pp, True)
                waveutil.reply_wavelet(wavelet, constants.ERROR_TRY_AGAIN)
                logging.error(e)
            else:
                preferences.update_pp_form(context, wavelet, pp)
                waveutil.reply_wavelet(wavelet, constants.PREFERENCES_SAVED)

        elif event.properties['button'] == 'refresh_pp':
            preferences.update_pp_form(context, wavelet, pp, True)
            waveutil.reply_wavelet(wavelet, constants.COMMAND_SUCCESSFUL % 'refresh')

        elif event.properties['button'] == 'exec_pp':
            command = waveutil.get_form_element(form, 'command').value
            logging.debug('executing command: %s' % command)
            if command == 'help':
                waveutil.reply_wavelet(wavelet, constants.COMMANDS_HELP)
                return

            if command == 'refresh':
                preferences.update_pp_form(context, wavelet, pp, True)
            elif command == 'clean':
                waveutil.reply_wavelet(wavelet, "Not implemented yet")
                return
            elif command == 'reset':
                query = model.ParticipantWavePreferences.all()
                query.filter('participant =', modified_by)
                db.delete(query)
                preferences.update_pp_form(context, wavelet, pp, True)
            else:
                waveutil.reply_wavelet(wavelet, constants.COMMAND_UNKNOWN % command)
                return

            waveutil.reply_wavelet(wavelet, constants.COMMAND_SUCCESSFUL % command)

    def on_wavelet_self_removed(self, event, context):
        wavelet_type = preferences.get_type(event, context)
        wavelet = waveutil.get_wavelet(event, context)

        if wavelet_type == constants.WAVELET_TYPE.PREFERENCES:
            for participant in wavelet.participants:
                pp = preferences.get_pp(participant, context=context)
                pp.preferencesWaveId = None
                pp.put()
        elif wavelet_type == constants.WAVELET_TYPE.NORMAL:
            # TODO delete the widget
            pass

