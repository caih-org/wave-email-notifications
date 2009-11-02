import os
import urllib

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from waveapi import robot_abstract
from waveapi import document

import model
from util import *


def get_preferences_url(participant, waveId):
    return '%s/prefs/%s/%s/' % (ROBOT_BASE_URL, urllib.quote(participant), waveId)


def create_pwp_form(context, participant):
    wavelet = context.GetRootWavelet()
    pwp = model.get_pp(participant, wavelet.waveId)
    wavelet = context.builder.WaveletCreate(wavelet.waveId, '', [ participant ])
    rootblip = context.GetBlipById(wavelet.GetRootBlipId())
    doc = rootblip.GetDocument()
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'notify', pwp.notify, False, 'Enable notifications for this wave'))
    doc.AppendText('\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'save_pwp', 'save', 'save'))
    doc.AppendText('\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'command', '', '', 'Execute commands (not yet available)'))
    doc.AppendText('\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'exec', 'exec', 'exec'))


def create_pp_form(context, participant):
    pp = model.get_pp(participant, True)
    if pp.preferencesWaveId: return
    pp.preferencesWaveId = "pending"
    pp.put()

    wavelet = robot_abstract.NewWave(context, [ participant ])
    wavelet.SetTitle("Notifiy preferences")
    wavelet.SetDataDocument(ROBOT_ADDRESS, "preferences")
    rootblip = context.GetBlipById(wavelet.GetRootBlipId()) 
    doc = rootblip.GetDocument() 
    doc.AppendText('\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.INPUT, 'email', pp.email, '', 'Email to receive notifications at'))
    doc.AppendText('\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'notify', pp.notify, False, 'Enable notifications'))
    doc.AppendText('\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'save_pp', 'save', 'save'))


def filter_preferences(context):
    wavelet = context.GetRootWavelet()
    return wavelet.GetDataDocument(ROBOT_ADDRESS) == "preferences"


class Preferences(webapp.RequestHandler):

    def get(self):
        path_parts = urllib.unquote(self.request.path).split("/")
        template_values = {}

        if len(path_parts) == 5:
            participant = path_parts[2]
            waveId = path_parts[3]
            pwp = model.get_pwp(participant, waveId)
            pp = model.get_pp(participant)
            if pp:
                waveurl = get_url(pp.participant, pp.preferencesWaveId) 
                template_values = { 'pwp': pwp, 'waveurl': waveurl }

        elif len(path_parts) == 4:
            participant = path_parts[2]
            pp = model.get_pp(participant)
            template_values = { 'pp': pp }

        path = os.path.join(os.path.dirname(__file__), 'preferences.html')
        self.response.out.write(template.render(path, template_values))

    def post(self):
        path_parts = urllib.unquote(self.request.path).split("/")

        if len(path_parts) == 5:
            participant = path_parts[2]
            waveId = path_parts[3]
            pwp = model.get_pwp(participant, waveId)
            pwp.notify = self.request.get('pwp_notify') == '1'
            pwp.put()
            self.redirect(".")
        elif len(path_parts) == 4:
            participant = path_parts[2]
            pp = model.get_pp(participant)
            pp.notify = self.request.get('pp_notify') == '1'
            pp.email = self.request.get('pp_email')
            pp.put()
            self.redirect(".")


if __name__ == "__main__":
  run_wsgi_app(webapp.WSGIApplication([('/prefs/.*', Preferences)]))
