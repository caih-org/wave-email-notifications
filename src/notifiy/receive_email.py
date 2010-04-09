# -*- coding: UTF-8 -*-

import logging

from google.appengine.api import mail
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

from notifiy import constants
from notifiy import model
from notifiy import templates
from notifiy import notifications
from notifiy import util
from notifiy.robot import create_robot


class ReceiveEmail(InboundMailHandler):

    def receive(self, message):
        body = '\n'.join([b.decode() for (a, b) in message.bodies(content_type='text/plain')])

        if '<' in message.to and '>' in message.to:
            to = message.to[message.to.find('<') + 1:message.to.find('>')]
        else:
            to = message.to

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
                       templates.UNSUBSCRIBED_BODY)

    def process_incoming(self, body, sender, to):
        to = to.split('@')[0].split('.')
        participant = util.modified_b64decode(to[0])
        wave_id = util.modified_b64decode(to[1])
        wavelet_id = util.modified_b64decode(to[2])
        blip_id = util.modified_b64decode(to[3])
        body = '%s: %s' % (participant, util.process_body(body))

        logging.debug('incoming email from %s [participant=%s, wave_id=%s, wavelet_id=%s, blip_id=%s]: %s'
                      % (sender, participant, wave_id, wavelet_id, blip_id, body))

        robot = create_robot(run=False, domain=participant.split('@')[1])

        # TODO wavelet = robot.fetch_wavelet(wave_id, wavelet_id, participant)
        wavelet = robot.fetch_wavelet(wave_id, wavelet_id)
        if blip_id:
            blip = wavelet.blips[blip_id]
            blip.reply().append(body)
        else:
            wavelet.reply(body)
        robot.submit(wavelet)
        notifications.notify_submitted(wavelet, blip, participant)
