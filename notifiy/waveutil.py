#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

import urllib

from waveapi import document

from . import constants


##########################################################
# Wave utils

def get_wavelet(event, context, private=True):
    return context.GetRootWavelet() or private and context.GetWaveletById(get_blip(event, context).waveletId)


def get_blip(event, context):
    return context.GetBlipById(event.properties['blipId'])


def get_form_element(form, element):
    for e in form:
        if form[e].type == document.ELEMENT_TYPE.CHECK:
            if form[e].value == None:
                form[e].value = form[e].name
                form[e].name = form[e].label
            if isinstance(form[e].value, basestring):
                form[e].value = form[e].value == 'true'
        if form[e].name == element:
            return form[e]


def reply_wavelet(wavelet, message):
    doc = wavelet.CreateBlip().GetDocument()
    doc.SetText(message)


def get_url(participant, wave_id):
    domain = participant.split('@')[1]
    quoted_wave_id = urllib.quote(urllib.quote(wave_id))

    if wave_id and wave_id.startswith('pending'):
        return 'Please search for it at Google Wave\'s settings section.'
    elif wave_id and domain == 'googlewave.com':
        return 'https://wave.google.com/wave/#restored:wave:%s' % quoted_wave_id
    elif wave_id:
        return 'https://wave.google.com/a/%s/#restored:wave:%s' % (quoted_wave_id, domain)
    else:
        return ''


def get_remove_url(email):
    return 'remove-%s@%s.appspotmail.com' % (constants.modified_b64encode(email), constants.ROBOT_ID)

