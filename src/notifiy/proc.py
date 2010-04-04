#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import urllib
import datetime

from google.appengine.ext import webapp
from google.appengine.ext import deferred

from notifiy import model


class Process(webapp.RequestHandler):

    def get(self):
        self.response.contentType = 'application/json'

        path = [urllib.unquote(a) for a in self.request.path.split('/')[2:]]
        notification_type = path[0]
        toggle = (notification_type == 'toggle')

        participant = self.request.get('participant')
        wave_id = self.request.get('wave_id')

        pwp = model.ParticipantWavePreferences.get_by_pk(participant, wave_id, create=toggle)

        if notification_type == "status" or notification_type == "toggle":
            if pwp:
                if toggle:
                    pwp.notify_type = (pwp.notify_type + 1) % model.NOTIFY_TYPE_COUNT
                    pwp.put()
                status = pwp.notify_type
                email = pwp.notify_type
                pp = model.ParticipantPreferences.get_by_pk(participant)
                if pwp.notify_type != model.NOTIFY_NONE and pp and len(pp.get_phone_preferences()) > 0:
                    phone = model.NOTIFY_ONCE
                else:
                    phone = model.NOTIFY_NONE
                self.response.out.write('{status:%s,email:%s,phone:%s}' % (status, email, phone))
            else:
                self.response.out.write('{status:0,email:0,phone:0}')
        elif notification_type == "offline" or notification_type == "online":
            if pwp:
                pwp.last_visited = datetime.datetime.now();
                pwp.put()
                if notification_type == "offline":
                    visited(pwp);
                else:
                    deferred.defer(visited, pwp, _countdown=150);
            self.response.out.write('{status:0}')


def visited(pwp):
    current_pwp = model.ParticipantWavePreferences.get_by_pk(pwp.participant, pwp.wave_id)
    if current_pwp.last_visited == pwp.last_visited:
        current_pwp.visited = True;
        current_pwp.put();
