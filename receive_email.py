import logging
import base64

from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

import model
from util import *

class ReceiveEmail(InboundMailHandler):

    def receive(self, message):
        body = '\n'.join([b.decode() for (a, b) in message.bodies(content_type='text/plain')])
        sender = message.sender
        to = message.to.split('@')[0].split('.')

        if to[0].startswith('remove-'):
            logging.debug('unsubscribe %s' % mail_from)
            mail_to = base64.urlsafe_b64decode(to[0][7:])
            query = model.ParticipantPreferences.all()
            query.filter('email =', mail_to)
            for pp in query:
                pp.email = ''
                pp.put()
            mail.send_mail(ROBOT_EMAIL, mail_to, UNSUBSCRIBED_SUBJECT, UNSUBSCRIBED)
        else:
            logging.debug('incoming email from %s [waveId=%s, waveletId=%s]: %s'
                          % (sender, waveId, waveletId, body))
            waveId = base64.urlsafe_b64decode(to[0])
            waveletId = base64.urlsafe_b64decode(to[1])


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([('/_ah/mail/.+', ReceiveEmail)]))

