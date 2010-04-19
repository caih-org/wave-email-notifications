# -*- coding: UTF-8 -*-

import logging
import hashlib
import httplib
import urllib
import urllib2
import uuid
import datetime
import base64
import re
import string

from google.appengine.ext import deferred
from google.appengine.api.labs import taskqueue

from waveapi import simplejson

from notifiy import model
from notifiy import templates


def get_account(participant, create=False):
    if not participant: return

    pp = model.ParticipantPreferences.get_by_pk(participant)
    if not pp: return

    if not pp.account_id and not create: return

    if not pp.account_id:
        account = model.Account.get_by_pk(str(uuid.uuid4()), None, create=True)
        account.put()
        pp.account_id = account.account_id
        pp.put()
        return account
    else:
        return model.Account.get_by_pk(pp.account_id, None)


def send_message(pwp, modified_by, title, wave_id, wavelet_id, blip_id, message, extra=None):
    account = get_account(pwp.participant)
    if not account: return

    logging.debug('Sending message to phones for account %s' % account.account_id)

    if not account.expiration_date or account.expiration_date < datetime.date.today():
        logging.warn('Account expired %s' % account.expiration_date)
        return

    query = model.Phone.all()
    query.filter('account_id =', account.account_id)
    for phone in query:
        logging.debug('Sending message to %s %s' % (phone.phone_type, phone.phone_uid))
        if phone.phone_type == 'iphone':
            m = hashlib.md5()
            m.update(unicode(title).encode("UTF-8"))
            m.update(unicode(message).encode("UTF-8"))
            if extra:
                m.update(str(datetime.datetime.now()))
            text_hash = m.hexdigest()
            name = '%s-%s-%s' % (wave_id, phone.phone_token, text_hash)
            name = re.compile('[^a-zA-Z0-9-]').sub('X', name)

            try:
                deferred.defer(send_message_to_iphone,
                               participant=pwp.participant,
                               phone_token=phone.phone_token,
                               wave_id=wave_id,
                               wavelet_id=wavelet_id,
                               blip_id=blip_id,
                               title=title,
                               message=message,
                               #_name=name,
                               _queue="send-phone")

            except (taskqueue.TombstonedTaskError, taskqueue.TaskAlreadyExistsError), e:
                logging.warn('Repeated phone notification %s', e)

def send_message_to_iphone(participant, phone_token, wave_id, wavelet_id, blip_id, title, message):
    remote_url = model.ApplicationSettings.get('apn-url')[8:].split('/', 1)
    apn_type = model.ApplicationSettings.get('apn-type')
    user = model.ApplicationSettings.get('apn-key-%s' % apn_type)
    passwd = model.ApplicationSettings.get('apn-master-secret-%s' % apn_type)

    title = title.strip()
    message = message.strip()

    json = construct_message(participant, phone_token, wave_id, wavelet_id, blip_id, '', '')

    maxlen = 255 - len(json.encode("utf-8"))

    if len(title.encode("utf-8")) + len(message.encode("utf-8")) > maxlen:
        maxlen_title = int(maxlen * 0.3)
        if len(title.encode("utf-8")) > maxlen_title:
            if maxlen_title > 3:
                title = title[:maxlen_title - 3] + '...'
            else:
                title = ''
        maxlen = maxlen - len(title.encode("utf-8"))
        if len(message.encode("utf-8")) > maxlen:
            if maxlen > 3:
                message = message[:maxlen - 3] + '...'
            else:
                message = ''

    json = construct_message(participant, phone_token, wave_id, wavelet_id, blip_id, title, message)

    headers = { 'Content-Type': 'application/json',
                'Content-Length': len(json),
                'Authorization': 'Basic %s' % string.strip(base64.b64encode(user + ':' + passwd)) }

    logging.debug('%s:%s' % (user, passwd))
    logging.debug('Trying to send %s\n%s\n%s' % (remote_url, headers, json))

    conn = httplib.HTTPSConnection(remote_url[0])
    conn.request("POST", '/%s' % remote_url[1], json, headers)
    response = conn.getresponse()
    if response.status != 200:
        logging.error('Error calling remote notification server: %s %s', response.reason, response.read())
    else:
        logging.info('Done sending notification')


def construct_message(participant, phone_token, wave_id, wavelet_id, blip_id, title, message):
    message = (templates.PHONE_MESSAGE % (title, message))

    if phone_token:
        data = { 'device_tokens': [ phone_token.replace(' ', '').upper() ],
                 'aps': { 'alert': { 'body': message } },
                 'r': '%s:%s:%s:%s' % (participant, wave_id, wavelet_id, blip_id) }
    else:
        data = { 'aps': { 'alert': { 'body': message } },
                 'r': '%s:%s:%s:%s' % (participant, wave_id, wavelet_id, blip_id) }

    return simplejson.dumps(data, separators=(',', ':'))


def send_message_to_iphone_2(participant, phone_uid, phone_token, wave_id, wavelet_id, blip_id, message, url):
    remote_url = model.ApplicationSettings.get('remote-server');

    data = { 'uid': phone_uid,
             'token': phone_token,
             'participant': participant,
             'wave_id': wave_id,
             'wavelet_id': wavelet_id,
             'blip_id': blip_id,
             'message': message,
             'url': url }

    logging.debug('Trying to send %s' % urllib.urlencode(data))

    try:
        urllib2.urlopen(remote_url, urllib.urlencode(data))
        logging.info('Success calling remote notification server')
    except Exception, e:
        logging.error('Error calling remote notification server: %s' % e)
