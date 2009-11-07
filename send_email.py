#!/usr/bin/env python

import logging

from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.labs import taskqueue

import model
from util import *


class SendEmail(webapp.RequestHandler):

    def post(self):
        mail_from = self.request.get('mail_from')
        mail_to = self.request.get('mail_to')
        subject = self.request.get('subject')
        body = self.request.get('body')

        logging.debug('emailing %s "%s"' % (mail_to, subject))
        mail.send_mail(mail_from, mail_to, subject, body, reply_to=mail_from)


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([('/send_email', SendEmail)]))
