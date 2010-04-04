# -*- coding: UTF-8 -*-

import logging

from waveapi import appengine_robot_runner
from waveapi import events
from waveapi import robot

from notifiy import constants
from notifiy import notifications
from notifiy import preferences
from notifiy import templates
from notifiy import general


###################################################
# General handlers
###################################################

def on_wavelet_self_added(event, wavelet):
    if preferences.is_preferences_wave(wavelet): return
    logging.info('%s called' % event.type)

    general.wavelet_init(wavelet, event.modified_by)


def on_wavelet_self_removed(event, wavelet):
    if preferences.is_preferences_wave(wavelet): return
    logging.info('%s called' % event.type)

    general.wavelet_deinit(wavelet)


def on_wavelet_participants_changed(event, wavelet):
    if preferences.is_preferences_wave(wavelet): return
    logging.info('%s called' % event.type)

    message = templates.ADDED_MESSAGE % event.modified_by
    for participant in event.participants_added:
        general.participant_wavelet_init(wavelet, participant, message)


###################################################
# Content change handlers
###################################################

def on_wavelet_blip_created(event, wavelet):
    if preferences.is_preferences_wave(wavelet): return
    logging.info('%s called' % event.type)

    notifications.notify_created(wavelet, event.blip, event.modified_by)


def on_wavelet_blip_removed(event, wavelet):
    if preferences.is_preferences_wave(wavelet): return
    logging.info('%s called' % event.type)

    notifications.notify_removed(wavelet, event.blip, event.modified_by)


def on_wavelet_blip_submitted(event, wavelet):
    if preferences.is_preferences_wave(wavelet): return
    logging.info('%s called' % event.type)

    notifications.notify_submitted(wavelet, event.blip, event.modified_by)


###################################################
# Preferences handlers
###################################################

def on_form_button_clicked(event, wavelet):
    if not preferences.is_preferences_wave(wavelet): return
    logging.info('%s called' % event.type)

    preferences.handle_event(event, wavelet)


###################################################
# Main function
###################################################

def create_robot():
    image_url = '%s/%s' % (constants.ROBOT_BASE_URL, 'favicon.png')

    notifiy = robot.Robot(constants.ROBOT_NAME, image_url=image_url,
                          profile_url=constants.ROBOT_BASE_URL)

    notifiy.register_handler(events.WaveletSelfAdded, on_wavelet_self_added, context = [events.Context.ROOT])
    notifiy.register_handler(events.WaveletSelfRemoved, on_wavelet_self_removed, context = [events.Context.ROOT])

    notifiy.register_handler(events.WaveletParticipantsChanged, on_wavelet_participants_changed, context = [events.Context.ROOT])

    notifiy.register_handler(events.WaveletBlipCreated, on_wavelet_blip_created, context = [events.Context.SELF])
    notifiy.register_handler(events.WaveletBlipRemoved, on_wavelet_blip_removed, context = [events.Context.SELF])
    notifiy.register_handler(events.WaveletBlipSubmitted, on_wavelet_blip_submitted, context = [events.Context.SELF])

    notifiy.register_handler(events.FormButtonClicked, on_form_button_clicked, context = [events.Context.ALL])

    appengine_robot_runner.run(notifiy)
