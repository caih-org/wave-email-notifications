import os
import urllib
import logging
import uuid

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from waveapi import robot_abstract
from waveapi import document

import model
from util import *


def get_url(participant, waveId, action=''):
    return '%s/prefs/%s/%s/%s' % (ROBOT_BASE_URL, urllib.quote(participant),
                                  waveId, action)


def create_pwp_form(context, participant):
    logging.debug('creating pwp form for %s' % participant)
    wavelet = context.GetRootWavelet()
    pwp = model.get_pp(participant, wavelet.waveId)
    new_wavelet = context.GetWaveById(wavelet.waveId).CreateWavelet([ participant ])
    new_wavelet.SetTitle('Notifiy global preferences')
    rootblip = context.GetBlipById(new_wavelet.GetRootBlipId())
    doc = rootblip.GetDocument()
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'notify', pwp.notify, False, 'Enable notifications for this wave'))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'save_pwp', 'save', 'save', 'save'))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'command', '', '', 'Execute commands (not yet available)'))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'exec_pwp', 'exec', 'exec', 'exec'))


def create_pp_form(context, participant):
    logging.debug('creating pp form for %s' % participant)
    pp = model.get_pp(participant, True)
    if pp.preferencesWaveId: return
    pp.preferencesWaveId = 'pending:%s' % uuid.uuid1()
    pp.put()

    wavelet = robot_abstract.NewWave(context, [ participant ])
    wavelet.SetTitle('Notifiy global preferences')
    wavelet.SetDataDocument(ROBOT_ADDRESS, pp.preferencesWaveId)
    rootblip = context.GetBlipById(wavelet.GetRootBlipId())
    doc = rootblip.GetDocument()
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.INPUT, 'email', pp.email, '', 'Email to receive notifications at'))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'notify', pp.notify, False, 'Enable notifications'))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'save_pp', 'save', 'save'))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'command', '', '', 'Execute global commands (not yet available)'))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'exec_pp', 'exec', 'exec', 'exec'))


def get_preferencesWaveId(context):
    wavelet = context.GetRootWavelet()
    data = wavelet.GetDataDocument(ROBOT_ADDRESS)
    logging.debug('filtering %s == "%s"' % (wavelet.waveId, data))
    if data and data.startswith('pending') or data == wavelet.waveId:
        return data


def is_preferences_wave(context):
    return bool(get_preferencesWaveId(context))


def clear(waveId):
    query = ParticipantWavePreferences.all()
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
            pwp = model.get_pwp(participant, waveId)
            pp = model.get_pp(participant)
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
            pp = model.get_pp(participant)
            template_values = { 'pp': pp }

        path = os.path.join(os.path.dirname(__file__), 'preferences.html')
        self.response.out.write(template.render(path, template_values))

    def post(self):
        path_parts = urllib.unquote(self.request.path).split('/')

        if len(path_parts) == 5:
            participant = path_parts[2]
            waveId = path_parts[3]
            pwp = model.get_pwp(participant, waveId)
            pwp.notify = self.request.get('pwp_notify') == '1'
            pwp.put()
            self.redirect('.')
        elif len(path_parts) == 4:
            participant = path_parts[2]
            pp = model.get_pp(participant)
            pp.notify = self.request.get('pp_notify') == '1'
            pp.email = self.request.get('pp_email')
            pp.put()
            self.redirect('.')


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([('/prefs/.*', Preferences)]))
