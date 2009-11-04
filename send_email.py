#!/usr/bin/env python

import logging

from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.labs import taskqueue

import model
import preferences
from util import *


class Preferences(webapp.RequestHandler):

    def post(self):
        path_parts = urllib.unquote(self.request.path).split('/')
        if path_parts[2] == 'prepare':
            prepare(self.request.get('title'),
                    self.request.get('waveId'),
                    self.request.get('waveletId'),
                    self.request.get('participant'),
                    self.request.get('mail_from'),
                    self.request.get('message'),
                    self.request.get('ignore') == 'True')
        elif path_parts[2] == 'send':
            send(self.request.get('mail_from'),
                 self.request.get('mail_to'),
                 self.request.get('subject'),
                 self.request.get('body'))


def prepare(title, waveId, waveletId, participant, mail_from, message, ignore):
    pp = model.get_pp(participant, create=True)
    if not pp.notify or not mail.is_email_valid(pp.email): return

    pwp = model.get_pwp(participant, waveId, create=True)
    if not ignore and not pwp.notify: return

    url = get_url(participant, waveId)
    prefs_url = preferences.get_url(participant, waveId)
    subject = '[wave] %s' % title
    body = MESSAGE_TEMPLATE % (message, url, prefs_url, waveId, waveletId)
    mail_from = '%s <%s>' % (mail_from.replace('@', ' at '), ROBOT_EMAIL)
    mail_to = pp.email
    logging.debug('emailing %s "%s"' % (mail_to, message))

    taskqueue.Task(url='/send_email/send',
                   params={ 'mail_from': mail_from,
                            'mail_to': mail_to,
                            'subject': subject,
                            'body': body }).add(queue_name='send-email-send')


def send(mail_from, mail_to, subject, body):
    mail.send_mail(mail_from, mail_to, subject, body, reply_to=mail_from)


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([('/send_email/.*', Preferences)]))
