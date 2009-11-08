#!/usr/bin/env python

import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import model
from util import *


class Process(webapp.RequestHandler):

    def get(self):
        participant = self.request.get('participant')
        waveId = self.request.get('waveId')
        toggle = self.request.get('toggle')

        pwp = get_pwp(participant, waveId, create=True)

        if toggle:
            pwp.notify = not pwp.notify
            pwp.put()

        if pwp.notify:
            self.redirect("star_on.gif")
        else:
            self.redirect("star_off.gif")


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([('/proc', Process)]))
