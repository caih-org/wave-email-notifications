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

        to  =to.split('@')

        if '<' in message.sender and '>' in message.sender:
            sender = message.sender[message.sender.find('<') + 1:message.sender.find('>')]
        else:
            sender = message.sender.split('@')

        logging.debug('incoming email from %s to %s@%s', sender, *to);

        if to[0].startswith('remove-'):
            self.remove(to)
        else:
            self.process_incoming(body, sender, to)

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
        to = to[0].split('.')
        participant = util.modified_b64decode(to[0])
        wave_id = util.modified_b64decode(to[1])
        wavelet_id = util.modified_b64decode(to[2])
        blip_id = util.modified_b64decode(to[3])

        q = model.ParticipantPreferences.all()
        q.filter('participant =', participant)
        q.filter('email =', sender)
        if not q.get():
            logging.debug('Invalid email %s not registered to %s', sender, participant)
            return

        logging.debug('incoming email from %s [participant=%s, wave_id=%s, ' +
                      'wavelet_id=%s, blip_id=%s]: %s', sender, participant,
                      wave_id, wavelet_id, blip_id, body)

        robot = create_robot(run=False, domain=participant.split('@')[1])

        # TODO wavelet = robot.fetch_wavelet(wave_id, wavelet_id, participant)
        wavelet = robot.fetch_wavelet(wave_id, wavelet_id)
        body = '%s: %s' % (participant, util.process_body(body))
        if blip_id in wavelet.blips:
            blip = wavelet.blips[blip_id]
            blip = blip.reply()
            blip.append(body)
        else:
            blip = wavelet.reply(body)

        robot.submit(wavelet)
        notifications.notify_submitted(wavelet, blip, participant)
