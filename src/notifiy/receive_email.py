# -*- coding: UTF-8 -*-

import logging
import traceback

from google.appengine.api import mail
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

from notifiy import constants
from notifiy import model
from notifiy import templates
from notifiy import util


class ReceiveEmail(InboundMailHandler):

    def receive(self, message):
        body = '\n'.join([b.decode() for (a, b) in message.bodies(content_type='text/plain')])

        if '<' in message.to and '>' in message.to:
            to = message.to[message.to.find('<') + 1:message.to.find('>')]
        else:
            to = message.to

        to  =to.split('@')

        if '<' in message.sender and '>' in message.sender:
            sender = message.sender[message.sender.find('<') + 1:message.sender.find('>')]
        else:
            sender = message.sender.split('@')

        logging.debug('incoming email from %s to %s@%s', sender, *to);

        try:
            if to[0].startswith('remove-'):
                self.remove(sender)
            else:
                self.process_incoming(message.subject, body, sender, to)
        except Exception, e:
            logging.exception('Error processing email %s', e)
            mail.send_mail('Notifiy <%s>' % constants.ROBOT_EMAIL,
                           sender,
                           'RE: %s' % message.subject,
                           templates.ERROR_BODY % (message.subject, e, body))

    def remove(self, sender):
        logging.debug('unsubscribe %s' % sender)
        query = model.ParticipantPreferences.all()
        query.filter('email =', sender)
        for pp in query:
            pp.email = ''
            pp.put()
        mail.send_mail(constants.ROBOT_EMAIL,
                       sender,
                       templates.UNSUBSCRIBED_SUBJECT,
                       templates.UNSUBSCRIBED_BODY)

    def process_incoming(self, subject, body, sender, to):
        to = to[0].split('.')
        participant = util.modified_b64decode(to[0])
        wave_id = util.modified_b64decode(to[1])
        wavelet_id = util.modified_b64decode(to[2])
        blip_id = util.modified_b64decode(to[3])

        q = model.ParticipantPreferences.all()
        q.filter('participant =', participant)
        q.filter('email =', sender)
        if not q.get():
            error = 'Invalid email %s not registered to %s' % (sender, participant)
            logging.info(error)
            mail.send_mail('Notifiy <%s>' % constants.ROBOT_EMAIL, sender,
                           subject, templates.ERROR_BODY % (subject, error, body))
            return

        logging.debug('incoming email from %s [participant=%s, wave_id=%s, ' +
                      'wavelet_id=%s, blip_id=%s]: %s', sender, participant,
                      wave_id, wavelet_id, blip_id, body)

        util.reply_wavelet(wave_id, wavelet_id, blip_id, participant,
                           util.process_body(body))