# -*- coding: UTF-8 -*-

from google.appengine.ext import db
from google.appengine.ext import deferred

from notifiy import email
from notifiy import gadget
from notifiy import preferences
from notifiy import templates
from notifiy import model


def wavelet_init(wavelet, modified_by):
    """Initialize the wavelet"""

    gadget.gadget_add(wavelet)

    for participant in wavelet.participants:
        participant_wavelet_init(wavelet, participant, modified_by,
                                 message=templates.ROBOT_ADDED)


def participant_init(wavelet, participant):
    """Initialize the participant and return it"""

    pp = model.ParticipantPreferences.get_by_pk(participant)
    if pp: return pp

    pp = model.ParticipantPreferences.get_by_pk(participant, create=True)
    preferences.create_preferences_wave(wavelet.robot, participant)

    return pp


# TODO do this deferred
def participant_wavelet_init_deferred(wavelet, participant, modified_by, message):
    deferred.defer(participant_wavelet_init_deferred, wavelet, participant,
                   modified_by, message, _queue='participant-wavelet-init')


def participant_wavelet_init(wavelet, participant, modified_by, message=None):
    """Initialize the participant in the wavelet"""
    pp = participant_init(wavelet, participant)
    if not pp.notify_initial: return

    pwp = model.ParticipantWavePreferences.get_by_pk(participant, wavelet.wave_id)
    if pwp: return

    pwp = model.ParticipantWavePreferences.get_by_pk(participant, wavelet.wave_id, create=True)
    email.send_message(pwp, modified_by, wavelet.title, wavelet.wave_id,
                       wavelet.wavelet_id, wavelet.root_blip.blip_id, message)


def wavelet_deinit(wavelet):
    """De-initialize the wavelet"""

    gadget.gadget_remove(wavelet)


def participant_deinit(wavelet, participant):
    """De-initialize the participant, removes al records available and the preferences wave"""

    query = model.ParticipantPreferences.all()
    query.filter("participant =", participant);
    db.delete(query)

    query = model.ParticipantWavePreferences.all()
    query.filter("participant =", participant);
    db.delete(query)

    preferences.delete_preferences_wavelet(wavelet)
