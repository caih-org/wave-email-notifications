# -*- coding: UTF-8 -*-

from google.appengine.ext import deferred

from notifiy import email
from notifiy import model
from notifiy import phone
from notifiy import templates


def notify_created(wavelet, blip, modified_by):
    """Sends a created notification to all participants except the modified_by"""

    for participant in wavelet.participants:
        if participant == modified_by: continue
        notify_participant(participant, wavelet, modified_by, blip, blip.text)


def notify_submitted(wavelet, blip, modified_by, message=None):
    """Sends a submitted notification to all participants except the modified_by"""

    for participant in wavelet.participants:
        if participant == modified_by: continue
        notify_participant(participant, wavelet, modified_by, blip,
                           message or (blip and blip.text) or '[no content]')


def notify_removed(wavelet, modified_by):
    """Sends a deleted notification to all participants except the modified_by"""

    for participant in wavelet.participants:
        if participant == modified_by: continue
        notify_participant(participant, wavelet, modified_by,
                           wavelet.root_blip, templates.CONTENT_DELETED)


def notify_participant(participant, wavelet, modified_by, blip, message):
    deferred.defer(notify_participant_deferred,
                   participant=participant,
                   modified_by=modified_by,
                   title=wavelet.title,
                   wave_id=wavelet.wave_id,
                   wavelet_id=wavelet.wavelet_id,
                   blip_id=blip and blip.blip_id or '',
                   message=message,
                   _queue='notify-participant')


def notify_participant_deferred(participant, modified_by, title, wave_id, wavelet_id, blip_id, message):
    """Sends a notification to the participant"""

    pp = model.ParticipantPreferences.get_by_pk(participant)
    if not pp or not pp.notify: return

    pwp = model.ParticipantWavePreferences.get_by_pk(participant, wave_id)
    if not pwp or pwp.notify_type == model.NOTIFY_NONE: return

    if pwp.notify_type == model.NOTIFY_ONCE:
        if not pwp.visited: return
        message = templates.NOTIFY_ONCE_TEMPLATE % message
        pwp.visited = False

    email.send_message(pwp, modified_by, title, wave_id, wavelet_id, blip_id, message)
    phone.send_message(pwp, modified_by, title, wave_id, wavelet_id, blip_id, message)
