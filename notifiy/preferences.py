#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

import logging
import uuid

from google.appengine.api import memcache

from waveapi import document
from waveapi import robot_abstract

from . import constants
from . import model
from . import waveutil

##########################################################
# Wave State

def get_preferencesWaveId(event, context):
    wavelet = waveutil.get_wavelet(event, context)
    if not wavelet: return
    data = wavelet.GetDataDocument(constants.PREFERENCES_WAVEID_DATA_DOC)

    # FIXME TEMPORAL remove 1/1/2010
    if not data:
        data = wavelet.GetDataDocument(constants.ROBOT_ADDRESS)
        if data:
            wavelet.SetDataDocument(constants.ROBOT_ADDRESS, None)
            wavelet.SetDataDocument(constants.PREFERENCES_WAVEID_DATA_DOC, data)
    # END TEMPORAL

    logging.debug('filtering %s == %s' % (wavelet.waveId, data))
    if data and data.startswith('pending') or data == wavelet.waveId:
        return data


def set_preferencesWaveId(event, context, participant, wavelet):
    wavelet.SetDataDocument(constants.PREFERENCES_WAVEID_DATA_DOC, wavelet.waveId)
    pp = get_pp(participant, create=True, context=context)
    pp.preferencesWaveId = wavelet.waveId
    pp.put()


def get_type(event, context):
    if bool(get_preferencesWaveId(event, context)):
        logging.debug('preferences wavelet')
        return constants.WAVELET_TYPE.PREFERENCES
    else:
        logging.debug('normal wavelet')
        return constants.WAVELET_TYPE.NORMAL


##########################################################
# Preferences

def get_pp(participant, create=False, context=None):
    pp = None #memcache.get(participant, namespace='pp')

    if not pp:
        query = model.ParticipantPreferences.all()
        query.filter('participant =', participant)
        pp = query.get()
        memcache.add(participant, pp, namespace='pp')

    if create and context:
        if not pp:
            pp = create_pp(context, participant)
            memcache.add(participant, pp, namespace='pp')
        create_pp_wave(context, pp)

    return pp


def get_pwp(participant, waveId, create=False):
    pwp = None #memcache.get('%s:%s' % (participant, waveId), namespace='pwp')

    if not pwp:
        query = model.ParticipantWavePreferences.all()
        query.filter('participant =', participant)
        query.filter('waveId =', waveId)
        pwp = query.get()
        memcache.add('%s:%s' % (participant, waveId), pwp, namespace='pwp')

    if not pwp and create:
        pwp = model.ParticipantWavePreferences(participant=participant,
                                               waveId=waveId)
        pwp.put()
        memcache.add('%s:%s' % (participant, waveId), pwp, namespace='pwp')

    return pwp


def create_pp(context, participant):
    logging.debug('creating pp for %s' % participant)

    pp = model.ParticipantPreferences(participant=participant)

    if participant.endswith('appspot.com'):
        pp.notify = False
        pp.email = None
    else:
        # FIXME This should be more generic
        pp.email = participant.replace('@googlewave.com', '@gmail.com')

    pp.put()
    create_pp_wave(context, pp)

    return pp


def create_pp_wave(context, pp):
    if pp.preferencesWaveId: return
    logging.debug('creating pp form for %s' % pp.participant)

    pp.preferencesWaveId = 'pending:%s' % uuid.uuid1()
    pp.put()

    wavelet = robot_abstract.NewWave(context, [pp.participant, constants.SETTIE_ROBOT])
    update_pp_form(context, wavelet, pp)


def update_pp_form(context, wavelet, pp, ignore=False):
    if not wavelet.GetDataDocument(constants.PREFERENCES_VERSION_DATA_DOC):
        wavelet.AddParticipant(constants.SETTIE_ROBOT)

    if not ignore and wavelet.GetDataDocument(constants.PREFERENCES_VERSION_DATA_DOC) == constants.PREFERENCES_VERSION: return

    rootblip = context.GetBlipById(wavelet.GetRootBlipId())

    doc = rootblip.GetDocument()
    doc.Clear()

    wavelet.SetTitle('Notifiy global preferences')
    wavelet.SetDataDocument(constants.PREFERENCES_WAVEID_DATA_DOC, pp.preferencesWaveId)
    wavelet.SetDataDocument(constants.PREFERENCES_VERSION_DATA_DOC, constants.PREFERENCES_VERSION)

    doc.AppendText('\n')

    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'notify', pp.notify, pp.notify))
    doc.AppendText(' Notify me to this email:\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.INPUT, 'email', pp.email, pp.email))
    doc.AppendText('\n')

    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'notify_initial', pp.notify_initial, pp.notify_initial))
    doc.AppendText(' Send initial notifications\n')
    doc.AppendText('\n')

    doc.AppendText('iPhone activation code: %s\n' % pp.activation)
    doc.AppendText('\n')

    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'save_pp', 'Save'))
    doc.AppendText(' ')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'refresh_pp', 'Refresh'))

    doc.AppendText('\n\nExecute global commands: (try "help")')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.INPUT, 'command', ''))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'exec_pp', 'Exec'))
