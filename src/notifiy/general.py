# -*- coding: UTF-8 -*-

from google.appengine.ext import db

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
    preferences.preferences_wave_create(wavelet, participant)

    return pp


def participant_wavelet_init(wavelet, participant, modified_by, message):
    """Initialize the participant in the wavelet"""

    pp = participant_init(wavelet, participant)
    if not pp.notify_initial: return

    pwp = model.ParticipantWavePreferences.get_by_pk(participant, wavelet.wave_id)
    if pwp: return

    pwp = model.ParticipantWavePreferences.get_by_pk(participant, wavelet.wave_id, create=True)
    email.send_message(wavelet, pwp, modified_by, wavelet.root_blip, message)


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

    preferences.preferences_wave_remove(wavelet)
