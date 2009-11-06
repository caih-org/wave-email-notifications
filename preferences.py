import logging
import os
import urllib

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model
from util import *


def get_preferencesWaveId(context):
    wavelet = context.GetRootWavelet()
    data = wavelet.GetDataDocument(ROBOT_ADDRESS)
    logging.debug('filtering %s == "%s"' % (wavelet.waveId, data))
    if data and data.startswith('pending') or data == wavelet.waveId:
        return data


def is_preferences_wave(context):
    return bool(get_preferencesWaveId(context))


def clear(waveId):
    query = model.ParticipantWavePreferences.all()
    query.filter('waveId =', waveId)
    for pwp in query:
        pwp.delete()


class Preferences(webapp.RequestHandler):

    def get(self):
        path_parts = urllib.unquote(self.request.path).split('/')
        template_values = {}

        if len(path_parts) == 5:
            participant = path_parts[2]
            waveId = path_parts[3]
            action = path_parts[4]
            pwp = get_pwp(participant, waveId)
            pp = get_pp(participant)
            if pp and pwp:
                if action == 'enable':
                    pwp.notify = True
                    pwp.put()
                waveurl = get_url(pp.participant, pp.preferencesWaveId) 
                template_values = { 'action': action,
                                    'pwp': pwp,
                                    'waveurl': waveurl }

        elif len(path_parts) == 4:
            participant = path_parts[2]
            pp = get_pp(participant)
            template_values = { 'pp': pp }

        path = os.path.join(os.path.dirname(__file__), 'preferences.html')
        self.response.out.write(template.render(path, template_values))

    def post(self):
        path_parts = urllib.unquote(self.request.path).split('/')

        if len(path_parts) == 5:
            participant = path_parts[2]
            waveId = path_parts[3]
            pwp = get_pwp(participant, waveId)
            pwp.notify = self.request.get('pwp_notify') == '1'
            pwp.put()
            self.redirect('.')
        elif len(path_parts) == 4:
            participant = path_parts[2]
            pp = get_pp(participant)
            pp.notify = self.request.get('pp_notify') == '1'
            pp.email = self.request.get('pp_email')
            pp.put()
            self.redirect('.')


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([('/prefs/.*', Preferences)]))
