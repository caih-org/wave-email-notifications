#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

import logging

from google.appengine.api import mail
from google.appengine.ext import webapp

from . import constants


class SendEmail(webapp.RequestHandler):

    def post(self):
        mail_from = self.request.get('mail_from')
        mail_to = self.request.get('mail_to')
        subject = self.request.get('subject')
        waveId = constants.modified_b64encode(self.request.get('waveId'))
        waveletId = constants.modified_b64encode(self.request.get('waveletId'))
        body = self.request.get('body')

        reply_to = '%s.%s@%s.appspotmail.com' % (waveId, waveletId, constants.ROBOT_ID)

        logging.debug('emailing %s "%s"' % (mail_to, subject))

        mail.send_mail(mail_from, mail_to, subject, body, reply_to=reply_to)

