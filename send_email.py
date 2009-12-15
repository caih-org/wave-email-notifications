#!/usr/bin/env python

import logging
import base64

from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import model
from util import *


class SendEmail(webapp.RequestHandler):

    def post(self):
        mail_from = self.request.get('mail_from')
        mail_to = self.request.get('mail_to')
        subject = self.request.get('subject')
        waveId = modified_b64encode(self.request.get('waveId'))
        waveletId = modified_b64encode(self.request.get('waveletId'))
        body = self.request.get('body')

        reply_to = '%s.%s@%s.appspotmail.com' % (waveId, waveletId, ROBOT_ID)

        logging.debug('emailing %s "%s"' % (mail_to, subject))

        mail.send_mail(mail_from, mail_to, subject, body, reply_to=reply_to)


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([('/send_email', SendEmail)]))

