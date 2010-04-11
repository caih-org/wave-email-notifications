# -*- coding: UTF-8 -*-

import datetime
import hashlib
import logging
import re

from google.appengine.api import mail
from google.appengine.api.labs import taskqueue
from google.appengine.ext import deferred

from notifiy import constants
from notifiy import model
from notifiy import templates
from notifiy import util


def send_message(pwp, modified_by, title, wave_id, wavelet_id, blip_id, message, extra=None):
    if not message: return

    pp = model.ParticipantPreferences.get_by_pk(pwp.participant)
    if not pp.email: return

    wave_url = util.get_url(pwp.participant, wave_id)
    prefs_url = util.get_url(pwp.participant, pp.preferences_wave_id)
    unsuscribe_email = 'remove-%s@%s.appspotmail.com' % (util.modified_b64encode(pwp.participant), constants.ROBOT_ID)
    body = templates.MESSAGE_TEMPLATE % (message, wave_url, prefs_url, unsuscribe_email)

    m = hashlib.md5()
    m.update(unicode(title).encode("UTF-8"))
    m.update(unicode(message).encode("UTF-8"))
    if extra:
        m.update(str(datetime.datetime.now()))
    text_hash = m.hexdigest()
    name = '%s-%s-%s' % (wave_id, pp.email, text_hash)
    name = re.compile('[^a-zA-Z0-9-]').sub('X', name)

    try:
        deferred.defer(post,
                       participant=pwp.participant,
                       mail_from='%s <%s>' % (modified_by, constants.ROBOT_EMAIL),
                       mail_to=pp.email,
                       subject=title,
                       wave_id=wave_id,
                       wavelet_id=wavelet_id,
                       blip_id=blip_id,
                       body=body,
                       _queue='send-email',
                       _name=name)
    except taskqueue.TombstonedTaskError, e:
        logging.warn('Repeated email %s', e)


def post(participant, mail_from, mail_to, subject, wave_id, wavelet_id, blip_id, body):
    participant = util.modified_b64encode(participant)
    wave_id = util.modified_b64encode(wave_id)
    wavelet_id = util.modified_b64encode(wavelet_id)
    blip_id = util.modified_b64encode(blip_id)
    reply_to = '%s <%s.%s.%s.%s@%s.appspotmail.com>' % \
               (constants.ROBOT_NAME.title(), participant, wave_id, wavelet_id,
                blip_id, constants.ROBOT_ID)

    logging.debug('emailing %s "%s"', mail_to, subject)

    mail.send_mail(mail_from, mail_to, '[wave] %s' % subject, body, reply_to=reply_to)
