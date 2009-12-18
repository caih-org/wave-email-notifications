#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

import logging

from google.appengine.api import mail
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

from . import constants
from . import model


class ReceiveEmail(InboundMailHandler):

    def receive(self, message):
        body = '\n'.join([b.decode() for (a, b) in message.bodies(content_type='text/plain')])
        sender = message.sender
        if '<' in message.to and '>' in message.to:
            to = message.to[message.to.find('<') + 1:message.to.find('>')].split('@')
        else:
            to = message.to.split('@')

        logging.debug('incoming email to %s@%s' % tuple(to));

        if to[0].startswith('remove-'):
            self.remove(to)
        else:
            self.process_incoming(body, sender, to)

    def remove(self, to):
        mail_to = constants.modified_b64decode(to[0][7:])
        logging.debug('unsubscribe %s' % mail_to)
        query = model.ParticipantPreferences.all()
        query.filter('email =', mail_to)
        for pp in query:
            pp.email = ''
            pp.put()
        mail.send_mail(constants.ROBOT_EMAIL,
                       mail_to,
                       constants.UNSUBSCRIBED_SUBJECT,
                       constants.UNSUBSCRIBED)

    def process_incoming(self, body, sender, to):
        to = to[0].split('.')
        waveId = constants.modified_b64decode(to[0])
        waveletId = constants.modified_b64decode(to[1])
        logging.debug('incoming email from %s [waveId=%s, waveletId=%s]: %s'
                      % (sender, waveId, waveletId, body))

