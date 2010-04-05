# -*- coding: UTF-8 -*-

import logging

from google.appengine.api import mail
from google.appengine.ext import deferred

from notifiy import constants
from notifiy import model
from notifiy import templates
from notifiy import util


def send_message(wavelet, pwp, modified_by, blip, message):
    pp = model.ParticipantPreferences.get_by_pk(pwp.participant)
    if not pp.email: return

    wave_url = util.get_url(pwp.participant, wavelet.wave_id)
    prefs_url = util.get_url(pwp.participant, pp.preferences_wave_id)
    unsuscribe_email = 'remove-%s@%s.appspotmail.com' % (util.modified_b64encode(pwp.participant), constants.ROBOT_ID)
    body = templates.MESSAGE_TEMPLATE % (message, wave_url, prefs_url, unsuscribe_email)

    deferred.defer(post,
                   participant=pwp.participant,
                   mail_from='%s <%s>' % (modified_by, constants.ROBOT_EMAIL),
                   mail_to=pp.email,
                   subject=wavelet.title,
                   wave_id=wavelet.wave_id,
                   wavelet_id=wavelet.wavelet_id,
                   blip_id=blip.blip_id,
                   body=body,
                   _queue='send-email')


def post(participant, mail_from, mail_to, subject, wave_id, wavelet_id, blip_id, body):
    participant = util.modified_b64encode(participant)
    wave_id = util.modified_b64encode(wave_id)
    wavelet_id = util.modified_b64encode(wavelet_id)
    blip_id = util.modified_b64encode(blip_id)
    reply_to = '%s.%s.%s.%s@%s.appspotmail.com' % (participant, wave_id, wavelet_id, blip_id, constants.ROBOT_ID)

    logging.debug('emailing %s "%s"' % (mail_to, subject))

    mail.send_mail(mail_from, mail_to, subject, body, reply_to=reply_to)
