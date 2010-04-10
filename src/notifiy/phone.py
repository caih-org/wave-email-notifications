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
    query = model.ParticipantAccount.all()
    query.filter('participant =', participant)
    pa = query.get()

    if not pa and not create: return

    if not pa:
        account = model.Account.get_by_pk(str(uuid.uuid4()), None, create=True)
        account.put()
        pa = model.ParticipantAccount.get_by_pk(account.account_id, participant, create=True)
        pa.put()
        return account
    else:
        return model.Account.get_by_pk(pa.account_id, None)


def save_history(original_account):
    if not original_account: return

    account = model.Account.get_by_pk(original_account.account_id,
                                      datetime.datetime.now(), create=True)
    account.subscription_type = original_account.subscription_type
    account.expiration_date = original_account.expiration_date
    account.put()


def send_message(pwp, modified_by, title, wave_id, wavelet_id, blip_id, message):
    account = get_account(pwp.participant)
    if not account: return
    logging.debug('Sending message to phones for account %s' % account.account_id)
    if not account.expiration_date or account.expiration_date < datetime.date.today(): return

    message = (templates.PHONE_MESSAGE % (title, modified_by, message[:40])).encode('ISO-8859-1')
    url = util.get_url(pwp.participant, wave_id)

    query = model.AccountPhone.all()
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
