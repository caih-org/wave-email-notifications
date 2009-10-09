import os
import urllib

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model

class Preferences(webapp.RequestHandler):
    def get(self):
        path_parts = urllib.unquote(self.request.path).split("/")

        if len(path_parts) == 5:
            query = model.ParticipantWavePreferences.all()
            query.filter('participant =', path_parts[2])
            query.filter('waveId =', path_parts[3])
            template_values = { 'pwp': query.get() }

        elif len(path_parts) == 4:
            query = model.ParticipantPreferences.all()
            query.filter('participant =', path_parts[2])
            template_values = { 'pp': query.get() }

        else:
            template_values = {}

        path = os.path.join(os.path.dirname(__file__), 'preferences.html')
        self.response.out.write(template.render(path, template_values))

    def post(self):
        path_parts = urllib.unquote(self.request.path).split("/")

        if len(path_parts) == 5:
            query = model.ParticipantWavePreferences.all()
            query.filter('participant =', path_parts[2])
            query.filter('waveId =', path_parts[3])
            pwp = query.get()
            pwp.notify = self.request.get('pwp_notify') == '1'
            pwp.put()

        elif len(path_parts) == 4:
            query = model.ParticipantPreferences.all()
            query.filter('participant =', path_parts[2])
            pp = query.get()
            pp.notify = self.request.get('pp_notify') == '1'
            pp.email = self.request.get('pp_email')
            pp.put()


if __name__ == "__main__":
  run_wsgi_app(webapp.WSGIApplication([('/prefs/.*', Preferences)]))
