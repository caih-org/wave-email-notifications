#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

import urllib

from google.appengine.ext import webapp

from . import model
from . import preferences


class Process(webapp.RequestHandler):

    def get(self):
        self.response.contentType = 'text/plain'

        path = self.request.path.split('/')
        participant = urllib.unquote(path[2])
        waveId = urllib.unquote(path[3])
        notification_type = urllib.unquote(path[4])

        toggle = self.request.get('toggle')

        pwp = preferences.get_pwp(participant, waveId, create=bool(toggle))

        if pwp:
            if toggle:
                pwp.notify_type = (pwp.notify_type + 1) % model.NOTIFY_TYPE_COUNT
                pwp.put()
            else:
                pwp.visited = True;
                pwp.put()

            if notification_type == "email":
                self.response.out.write(str(pwp.notify_type))
            else:
                pp = preferences.get_pp(participant)
                if pwp.notify_type != 0 and pp and pp.phone_token:
                    self.response.out.write("1")
                else:
                    self.response.out.write("0")
        else:
            self.response.out.write(str(model.NOTIFY_NONE))

