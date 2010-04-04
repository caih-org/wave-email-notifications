# -*- coding: UTF-8 -*-

import logging

from google.appengine.api import mail
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext import deferred

from notifiy import constants
from notifiy import model
from notifiy import templates
from notifiy import util


def send_message(wavelet, pwp, modified_by, blip, message):
    wave_url = util.get_url(pwp.participant, wavelet.wave_id)
    pp = model.ParticipantPreferences.get_by_pk(pwp.participant)
    prefs_url = util.get_url(pwp.participant, pp.preferences_wave_id)
    unsuscribe_email = 'remove-%s@%s.appspotmail.com' % (util.modified_b64encode(pwp.participant), constants.ROBOT_ID)
    body = templates.MESSAGE_TEMPLATE % (message, wave_url, prefs_url, unsuscribe_email)

    deferred.defer(post,
                   mail_from='%s <%s>' % (modified_by, constants.ROBOT_EMAIL),
                   mail_to=pwp.participant,
                   subject=wavelet.title,
                   wave_id=wavelet.wave_id,
                   wavelet_id=wavelet.wavelet_id,
                   blip_id=blip.blip_id,
                   body=body,
                   _queue='send-email')


def post(mail_from, mail_to, subject, wave_id, wavelet_id, blip_id, body):
    reply_to = '%s.%s.%s@%s.appspotmail.com' % (wave_id, wavelet_id, blip_id, constants.ROBOT_ID)

    logging.debug('emailing %s "%s"' % (mail_to, subject))

    mail.send_mail(mail_from, mail_to, subject, body, reply_to=reply_to)


class ReceiveEmail(InboundMailHandler):

    def receive(self, message):
        body = '\n'.join([b.decode() for (a, b) in message.bodies(content_type='text/plain')])

        if '<' in message.to and '>' in message.to:
            to = message.to[message.to.find('<') + 1:message.to.find('>')].split('@')
        else:
            to = message.to.split('@')

        logging.debug('incoming email to %s@%s' % tuple(to));

        if to[0].startswith('remove-'):
            self.remove(to)
        else:
            self.process_incoming(body, message.sender, to)

    def remove(self, mail_to):
        mail_to = util.modified_b64decode(mail_to[0][7:])
        logging.debug('unsubscribe %s' % mail_to)
        query = model.ParticipantPreferences.all()
        query.filter('email =', mail_to)
        for pp in query:
            pp.email = ''
            pp.put()
        mail.send_mail(constants.ROBOT_EMAIL,
                       mail_to,
                       templates.UNSUBSCRIBED_SUBJECT,
                       templates.UNSUBSCRIBED)

    def process_incoming(self, body, sender, to):
        to = to[0].split('.')
        wave_id = util.modified_b64decode(to[0])
        wavelet_id = util.modified_b64decode(to[1])
        blip_id = util.modified_b64decode(to[2])

        logging.debug('incoming email from %s [wave_id=%s, wavelet_id=%s, blip_id=%s]: %s'
                      % (sender, wave_id, wavelet_id, blip_id, body))
