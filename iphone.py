#!/usr/bin/env python

import logging
import urllib

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import model
from util import *


class IPhone(webapp.RequestHandler):

    def get(self):
        self.response.contentType = 'text/plain'

        path = self.request.path.split('/')
        participant = urllib.unquote(path[2])
        activation = urllib.unquote(path[3])
        phone_uid = urllib.unquote(path[4])
        phone_token = urllib.unquote(path[5])

        logging.debug("participant: %s" % participant)
        logging.debug("activation: %s" % activation)
        logging.debug("iPhone uid: %s" % phone_uid)
        logging.debug("iPhone token: %s" % phone_token.replace('+', ' '))

        query = model.ParticipantPreferences.all()
        query.filter("participant =", participant);
        query.filter("activation =", activation);
        pp = query.get()

        if pp:
            pp.phone_uid = phone_uid
            pp.phone_token = phone_token
            pp.put()
            self.response.out.write('OK')
        else:
            self.response.out.write('INVALID')


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([('/iphone/.*', IPhone)]))

