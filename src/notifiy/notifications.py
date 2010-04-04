# -*- coding: UTF-8 -*-

from notifiy import email
from notifiy import model
from notifiy import phone
from notifiy import templates


def notify_created(wavelet, blip, modified_by):
    """Sends a created notification to all participants except the modified_by"""

    for participant in wavelet.participants:
        if participant == modified_by: continue
        notify_participant(participant, wavelet, modified_by, blip, blip.text)


def notify_submitted(wavelet, blip, modified_by):
    """Sends a submitted notification to all participants except the modified_by"""

    for participant in wavelet.participants:
        if participant == modified_by: continue
        notify_participant(participant, wavelet, modified_by, blip, blip.text)


def notify_deleted(wavelet, modified_by):
    """Sends a deleted notification to all participants except the modified_by"""

    for participant in wavelet.participants:
        if participant == modified_by: continue
        notify_participant(participant, wavelet, modified_by,
                           wavelet.root_blip, templates.CONTENT_DELETED)


def notify_participant(participant, wavelet, modified_by, blip, message):
    """Sends a notification to the participant"""

    pp = model.ParticipantPreferences.get_by_pk(participant)
    if not pp or not pp.notify: return

    pwp = model.ParticipantWavePreferences.get_by_pk(participant, wavelet.wave_id)
    if not pwp or pwp.notify_type == model.NOTIFY_NONE: return

    if pwp.notify_type == model.NOTIFY_ONCE:
        if not pwp.visited: return
        message = templates.NOTIFY_ONCE_TEMPLATE % message
        pwp.visited = False

    email.send_message(wavelet, pwp, modified_by, blip, message)
    phone.send_message(wavelet, pwp, modified_by, blip, message)
