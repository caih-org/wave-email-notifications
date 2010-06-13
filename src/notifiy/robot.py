# -*- coding: UTF-8 -*-

import logging

from waveapi import appengine_robot_runner
from waveapi import events
from waveapi.robot import Robot

from notifiy import constants
from notifiy import model
from notifiy import notifications
from notifiy import preferences
from notifiy import templates
from notifiy import general


###################################################
# General handlers
###################################################

def on_wavelet_self_added(event, wavelet):
    if preferences.is_preferences_wave(wavelet): return
    logging.info('%s called', event.type)
    setup_oauth(wavelet.robot, wavelet.domain)

    general.wavelet_init(wavelet, event.modified_by)


def on_wavelet_self_removed(event, wavelet):
    if preferences.is_preferences_wave(wavelet): return
    logging.info('%s called', event.type)
    setup_oauth(wavelet.robot, wavelet.domain)

    general.wavelet_deinit(wavelet)


def on_wavelet_participants_changed(event, wavelet):
    if preferences.is_preferences_wave(wavelet): return
    logging.info('%s called', event.type)
    setup_oauth(wavelet.robot, wavelet.domain)

    if wavelet.root_blip and event.blip_id == wavelet.root_blip.blip_id:
        general.wavelet_init(wavelet, event.modified_by)

    message = templates.ADDED_MESSAGE % event.modified_by
    for participant in event.participants_added:
        general.participant_wavelet_init(wavelet, participant,
                                         event.modified_by, message)


###################################################
# Content change handlers
###################################################

def on_blip_submitted(event, wavelet):
    if preferences.is_preferences_wave(wavelet): return
    logging.info('%s called', event.type)
    setup_oauth(wavelet.robot, wavelet.domain)

    if wavelet.root_blip and event.blip_id == wavelet.root_blip.blip_id:
        general.wavelet_init(wavelet, event.modified_by)

    notifications.notify_submitted(wavelet, event.blip, event.modified_by)


def on_wavelet_blip_removed(event, wavelet):
    if preferences.is_preferences_wave(wavelet): return
    logging.info('%s called', event.type)
    setup_oauth(wavelet.robot, wavelet.domain)

    if wavelet.root_blip and event.blip_id == wavelet.root_blip.blip_id:
        general.wavelet_init(wavelet, event.modified_by)

    notifications.notify_removed(wavelet, event.modified_by)


###################################################
# Preferences handlers
###################################################

def on_form_button_clicked(event, wavelet):
    if not preferences.is_preferences_wave(wavelet): return
    logging.info('%s called', event.type)
    setup_oauth(wavelet.robot, wavelet.domain)

    preferences.handle_event(event, wavelet)


###################################################
# Main functions
###################################################

def create_robot(run=True, domain=None):
    robot = Robot(constants.ROBOT_NAME.title(), image_url=constants.ROBOT_IMG,
                  profile_url=constants.ROBOT_BASE_URL)

    robot.register_handler(events.WaveletSelfAdded, on_wavelet_self_added, context=[ events.Context.ROOT ])
    robot.register_handler(events.WaveletSelfRemoved, on_wavelet_self_removed, context=[ events.Context.ROOT ])

    robot.register_handler(events.WaveletParticipantsChanged, on_wavelet_participants_changed, context=[ events.Context.ROOT ])

    robot.register_handler(events.BlipSubmitted, on_blip_submitted, context=[ events.Context.SELF ])
    robot.register_handler(events.WaveletBlipRemoved, on_wavelet_blip_removed, context=[ events.Context.SELF ])

    robot.register_handler(events.FormButtonClicked, on_form_button_clicked, context=[ events.Context.ALL ])

    # Needed to reauthenticate robot
    # verification_token = model.ApplicationSettings.get("verification-token")
    # security_token = model.ApplicationSettings.get("security-token")
    # robot.set_verification_token_info(verification_token, security_token)

    if domain:
        setup_oauth(robot, domain)

    if run:
        appengine_robot_runner.run(robot)

    return robot


def setup_oauth(robot, domain):
    consumer_key = model.ApplicationSettings.get("consumer-key")
    consumer_secret = model.ApplicationSettings.get("consumer-secret")
    if domain in constants.RPC_URL:
        url = constants.RPC_URL[domain]
    else:
        url = constants.RPC_URL['googlewave.com'] # TODO
    robot.setup_oauth(consumer_key, consumer_secret, url)
