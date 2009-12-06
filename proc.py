#!/usr/bin/env python

import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import model
from util import *


class Process(webapp.RequestHandler):

    def get(self):
        self.response.contentType = 'text/plain'

        participant = self.request.get('participant')
        waveId = self.request.get('waveId')
        toggle = self.request.get('toggle')

        pwp = get_pwp(participant, waveId, create=bool(toggle))

        if pwp:
            if toggle:
                logging.debug("before: %s" % pwp.notify_type)
                pwp.notify_type = (pwp.notify_type + 1) % model.NOTIFY_TYPE_COUNT
                logging.debug("after: %s" % pwp.notify_type)

            pwp.visited = True;
            pwp.put()
            self.response.out.write(str(pwp.notify_type))
        else:
            self.response.out.write(str(model.NOTIFY_NONE))


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([('/proc', Process)]))

