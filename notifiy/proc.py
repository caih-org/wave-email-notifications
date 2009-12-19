#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

import urllib
import datetime

from google.appengine.ext import webapp
from google.appengine.ext import deferred

from . import model
from . import preferences


class Process(webapp.RequestHandler):

    def get(self):
        self.response.contentType = 'text/plain'

        path = self.request.path.split('/')
        participant = urllib.unquote(path[2])
        waveId = urllib.unquote(path[3])
        notification_type = urllib.unquote(path[4])
        toggle = (notification_type == 'toggle')

        pwp = preferences.get_pwp(participant, waveId, create=toggle)

        if pwp:
            if notification_type == "email":
                self.response.out.write(str(pwp.notify_type))
            elif notification_type == "phone":
                pp = preferences.get_pp(participant)
                if pwp.notify_type != 0 and pp and len(pp.get_phone_preferences()) > 0:
                    self.response.out.write("1")
                else:
                    self.response.out.write("0")
            elif notification_type == "status":
                self.response.out.write(str(pwp.notify_type))
            elif notification_type == "online":
                pwp.last_visited = datetime.datetime.now();
                pwp.put()
                deferred.defer(visited, pwp, _countdown=90);
            elif notification_type == "toggle":
                pwp.notify_type = (pwp.notify_type + 1) % model.NOTIFY_TYPE_COUNT
                pwp.put()
        else:
            self.response.out.write(str(model.NOTIFY_NONE))


def visited(pwp):
    current_pwp = preferences.get_pwp(pwp.participant, pwp.waveId)
    if current_pwp.last_visited == pwp.last_visited:
        current_pwp.visited = True;
        current_pwp.put();
