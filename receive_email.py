import logging
import base64

from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler


class ReceiveEmail(InboundMailHandler):

    def receive(self, message):
        body = '\n'.join([b.decode() for (a, b) in message.bodies(content_type='text/plain')])
        sender = message.sender
        to = message.to.split('@')[0].split('.')
        waveId = base64.urlsafe_b64decode(to[0])
        waveletId = base64.urlsafe_b64decode(to[1])
        #date returns the message date.
        #attachments is a list of element pairs containing file types and contents.

        logging.debug('incoming email from %s [waveId=%s, waveletId=%s]: %s'
                      % (sender, waveId, waveletId, body))


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([('/_ah/mail/.+', ReceiveEmail)]))

