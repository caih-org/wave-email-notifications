#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import urllib
import datetime

from google.appengine.ext import webapp
from google.appengine.ext import deferred

from waveapi import simplejson

from notifiy import model
from notifiy import general
from notifiy import preferences
from notifiy.robot import create_robot


class Process(webapp.RequestHandler):

    def get(self):
        self.response.contentType = 'application/json'

        path = [urllib.unquote(a) for a in self.request.path.split('/')[2:]]
        notification_type = path[0]

        if not hasattr(self, notification_type): return

        self.participant = self.request.get('participant')
        self.wave_id = self.request.get('wave_id')

        getattr(self, notification_type)()

    def status(self):
        self.toggle(False)
        
    def toggle(self, toggle=True):
        pp = model.ParticipantPreferences.get_by_pk(self.participant)
        pwp = model.ParticipantWavePreferences.get_by_pk(self.participant, self.wave_id, create=toggle)
        data = ''

        if pwp:
            if toggle:
                pwp.notify_type = (pwp.notify_type + 1) % model.NOTIFY_TYPE_COUNT
                pwp.put()
            status = pwp.notify_type
            email = pwp.notify_type
            phones = [ 1 ] # TODO count phones
            if len(phones) == 0:
                phone = -1
            if pwp.notify_type != model.NOTIFY_NONE:
                phone = model.NOTIFY_ONCE
            else:
                phone = model.NOTIFY_NONE
            data = simplejson.dumps({ 'status': status,
                                      'email': email,
                                      'phone': phone,
                                      'preferencesWaveId': pp and pp.preferences_wave_id or '' })
        else:
            data = simplejson.dumps({ 'status': 0,
                                      'email': 0,
                                      'phone': 0,
                                      'preferencesWaveId': pp and pp.preferences_wave_id or '' })

        self.response.out.write(data);

    def offline(self):
        self.online(False)

    def online(self, online=True):
        pwp = model.ParticipantWavePreferences.get_by_pk(self.participant, self.wave_id)

        if pwp:
            pwp.last_visited = datetime.datetime.now()
            pwp.put()
            if not online:
                visited(pwp.participant, self.wave_id, pwp)
            else:
                deferred.defer(visited, pwp.participant, pwp.wave_id,
                               pwp.last_visited, _queue='visited', _countdown=150)

        self.response.out.write(simplejson.dumps({ 'status': 0 }))

    def reset(self):
        domain = self.participant.split('@')[1]
        robot = create_robot(run=False, domain=domain)

        preferences.create_preferences_wave(robot, self.participant)

        #wavelet = robot.fetch_wavelet(self.wave_id, '%s!root+conv' % domain)
        #general.participant_init(wavelet, self.participant)
        #general.participant_wavelet_init(wavelet, self.participant, self.participant)

        self.response.out.write(simplejson.dumps({ 'status': 0 }))


def visited(participant, wave_id=None, last_visited=None):
    if not wave_id: return
    pwp = model.ParticipantWavePreferences.get_by_pk(participant, wave_id)
    if pwp.last_visited == last_visited:
        pwp.visited = True
        pwp.put()
