#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

import hashlib
import logging
import re
import urllib
import urllib2
import datetime

from google.appengine.api import mail
from google.appengine.api.labs import taskqueue

from waveapi import document

from . import constants
from . import model
from . import preferences
from . import waveutil

GADGET_URL = '%s/%s.xml' % (constants.ROBOT_BASE_URL, constants.ROBOT_ID)


def init_wave(event, context):
    wavelet = waveutil.get_wavelet(event, context, private=False)
    if not wavelet: return
    # TODO ensure we get the root blip only
    blip = waveutil.get_blip(event, context)
    gadget = blip.GetGadgetByUrl(GADGET_URL)
    if not gadget:
        doc = blip.GetDocument()
        gadget = document.Gadget(GADGET_URL)
        doc.InsertElement(0, gadget)


def get_notify_type(wavelet, participant):
    notify_type = model.NOTIFY_NONE
    pwp = preferences.get_pwp(participant, wavelet.waveId)

    if pwp:
        notify_type = pwp.notify_type
        if pwp.notify_type == model.NOTIFY_ONCE:
            if pwp.visited:
                pwp.visited = False
                pwp.put()
            else:
                notify_type = model.NOTIFY_NONE

    return notify_type


def get_notify_initial(context, participants):
    return (not 'public@a.gwave.com' in participants
            and (not 'proxyingFor' in context.extradata
            or context.extradata['proxyingFor'] != 'no-initial'))


def notify_initial(context, wavelet, participants, modified_by, message):
    for participant in participants:
        if participant == constants.ROBOT_ADDRESS: continue
        pwp = preferences.get_pwp(participant, wavelet.waveId)
        if not pwp:
            pp = preferences.get_pp(participant, create=True, context=context)
            if pp.notify_initial:
                send_notification(context, wavelet, participant, modified_by, message)


def notify(event, context, wavelet, modified_by, message):
    for participant in wavelet.participants:
        if participant == constants.ROBOT_ADDRESS: continue
        if participant == modified_by: continue
        notify_type = get_notify_type(wavelet, participant)
        if notify_type == model.NOTIFY_ONCE:
            send_notification(context, wavelet, participant, modified_by,
                              constants.CHANGES_MESSAGE, extra=True)
        elif notify_type == model.NOTIFY_ALL:
            send_notification(context, wavelet, participant, modified_by, message)


def send_notification(context, wavelet, participant, mail_from, message, extra=False):
    if not message.strip(): return

    pp = preferences.get_pp(participant, create=True, context=context)
    url = waveutil.get_url(participant, wavelet.waveId)

    for ppp in pp.get_phone_preferences():
        try:
            remote_url = model.ApplicationSettings.get('remote-server');
            data = {
                'uid': ppp.phone_uid,
                'token': ppp.phone_token,
                'message': ('The wave "%s" has been updated by %s: "%s..."' % (wavelet.title, mail_from, message[:40])).encode('ISO-8859-1'),
                #'from': mail_from,
                #'title': wavelet.title.encode('ISO-8859-1'),
                #'body': message.encode('ISO-8859-1'),
                'url': url}
            logging.debug(urllib.urlencode(data))
            urllib2.urlopen(remote_url, urllib.urlencode(data))
            logging.info('success calling remote notification server')
        except urllib2.URLError, e:
            logging.warn('error calling remote notification server: %s' % e)

    if not pp.notify or not mail.is_email_valid(pp.email): return

    prefs_url = waveutil.get_url(participant, pp.preferencesWaveId)
    remove_url = waveutil.get_remove_url(pp.email)
    subject = '[wave] %s' % wavelet.title
    body = constants.MESSAGE_TEMPLATE % (message, url, prefs_url, remove_url)
    mail_from = '%s <%s>' % (mail_from.replace('@', ' at '), constants.ROBOT_EMAIL)
    mail_to = pp.email

    m = hashlib.md5()
    m.update(subject.encode("UTF-8"))
    m.update(message.encode("UTF-8"))
    if extra:
        m.update(str(datetime.datetime.now()))
    text_hash = m.hexdigest()
    name = '%s-%s-%s' % (wavelet.waveId, mail_to, text_hash)
    name = re.compile('[^a-zA-Z0-9-]').sub('X', name)

    if len(body) > 9000:
        body = constants.CONTENT_SUPRESSED % body[0:9000]

    logging.debug('adding task to send_email queue for %s => %s' % (name, mail_to))

    try:
        taskqueue.Task(url='/send_email', name=name,
                       params={'mail_from': mail_from,
                       'mail_to': mail_to,
                       'subject': subject,
                       'waveId': wavelet.waveId,
                       'waveletId': wavelet.waveletId,
                       'body': body}).add(queue_name='send-email')
    except taskqueue.TombstonedTaskError, e:
        logging.warn("Task with same name already added, droping duplicated message")
    except taskqueue.TaskAlreadyExistsError, e:
        logging.warn("Task with same name already added, droping duplicated message")


