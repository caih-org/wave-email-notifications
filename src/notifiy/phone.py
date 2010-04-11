# -*- coding: UTF-8 -*-

import logging
import urllib
import urllib2
import uuid
import datetime

from google.appengine.ext import deferred

from notifiy import model
from notifiy import util
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


def send_message(pwp, modified_by, title, wave_id, wavelet_id, blip_id, message):
    account = get_account(pwp.participant)
    if not account: return
    logging.debug('Sending message to phones for account %s' % account.account_id)
    if not account.expiration_date or account.expiration_date < datetime.date.today(): return

    message = (templates.PHONE_MESSAGE % (title, modified_by, message[:40])).encode('ISO-8859-1')
    url = util.get_url(pwp.participant, wave_id)

    query = model.Phone.all()
    query.filter('account_id =', account.account_id)
    for phone in query:
        logging.debug('Sending message to %s %s' % (phone.phone_type, phone.phone_uid))
        if phone.phone_type == 'iphone':
            deferred.defer(send_message_to_iphone,
                           participant=pwp.participant,
                           phone_uid=phone.phone_uid,
                           phone_token=phone.phone_token,
                           wave_id=wave_id,
                           wavelet_id=wavelet_id,
                           blip_id=blip_id,
                           message=message,
                           url=url,
                           _queue="send-phone")


def send_message_to_iphone(participant, phone_uid, phone_token, wave_id, wavelet_id, blip_id, message, url):
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
