#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import urllib
import urllib2
import uuid
import datetime

from google.appengine.ext import db
from google.appengine.ext import webapp

from notifiy import model
from notifiy import util
from notifiy import templates

LOG = '''\
--- TYPE: %s ---
participant: %s
activation: %s
phone uid: %s
phone token: %s
subscription type: %s
expiration date: %s'''

JSON = '''{
    'phones': [ %s ],
    'subscription_type': "%s",
    'expiration_date': "%s",
    'response': "OK"
}'''


def get_account(participant):
    query = model.Account.all()
    query.filter('participant =', participant)
    return query.get()


def save_history(original_account):
    account = model.Account.get_by_pk(original_account.account_id,
                                      datetime.datetime.now(), create=True)
    account.subscription_type = original_account.subscription_type
    account.expiration_date = original_account.expiration_date
    account.put()


def send_message(wavelet, pwp, modified_by, blip, message):
    account = get_account(pwp.participant)

    query = model.AccountPhone.all()
    query.filter('account_id =', account.account_id)

    message = (templates.PHONE_MESSAGE % (wavelet.title, modified_by, message[:40])).encode('ISO-8859-1')
    url = util.get_url(pwp.participant, wavelet.wave_id)
    for phone in query:
        if phone.phone_type == 'iphone':
            send_message_to_iphone(phone, message, url)


def send_message_to_iphone(phone, message, url):
    try:
        remote_url = model.ApplicationSettings.get('remote-server');
        data = {
            'uid': phone.phone_uid,
            'token': phone.phone_token,
            'message': message,
            'url': url}
        logging.debug(urllib.urlencode(data))
        urllib2.urlopen(remote_url, urllib.urlencode(data))
        logging.info('Success calling remote notification server')
    except urllib2.URLError, e:
        logging.warn('Error calling remote notification server: %s' % e)


class Phone(webapp.RequestHandler):

    def get(self):
        self.response.contentType = 'application/json'

        path = [urllib.unquote(a) for a in self.request.path.split('/')[2:]]
        type = path[0]

        participant = self.request.get('participant')
        activation = self.request.get('activation')

        subscription_type = self.request.get('subscription_type')
        expiration_date = self.request.get('expiration_date')

        phone_uid = self.request.get('phone_uid')
        phone_type = self.request.get('phone_type')
        phone_token = self.request.get('phone_token')
        phone_token = phone_token.replace('+', ' ')

        logging.debug(LOG % (type, participant, activation, phone_uid,
                             phone_token, subscription_type, expiration_date))

        account = get_account(participant)

        if type == 'activate':
            query = model.ParticipantPreferences.all()
            query.filter('participant =', participant);
            query.filter('activation =', activation);
            pp = query.get()

            if pp:
                if not account:
                    account = model.Account.get_by_pk(uuid.uuid4(), None, create=True)
                else:
                    save_history(account)

                account.subscription_type = subscription_type
                account.expiration_date = expiration_date
                account.put()

                phone = model.ApplicationPhone.get_by_pk(account.account_id, phone_uid, create=True)
                phone.phone_type = phone_type
                phone.phone_token = phone_token
                phone.put()

        elif account and type == 'deactivate':
            query = model.AccountPhone.all()
            query.filter('phone_uid =', phone_uid);
            query.filter('phone_token =', phone_token);
            db.delete(query)

            save_history(account)
            db.delete(account)
            self.response.out.write('''{ 'response': "OK" }''')
            return


        if account:
            query = model.AccountPhone.all()
            query.filter('account_id =', account.account_id)
            phones = [phone.phone_uid for phone in query]

            self.response.out.write(JSON % (', '.join(phones),
                                            account.subscription_type,
                                            account.expiration_date))
        else:
            self.response.out.write('''{ 'response': "ERROR" }''')
