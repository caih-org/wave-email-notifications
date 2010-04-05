# -*- coding: UTF-8 -*-

import logging
import urllib
import urllib2
import uuid
import datetime

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext import deferred

from waveapi import simplejson

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


def send_message(wavelet, pwp, modified_by, blip, message):
    account = get_account(pwp.participant)
    if not account: return
    logging.debug('Sending message to phones for account %s' % account.account_id)

    message = (templates.PHONE_MESSAGE % (wavelet.title, modified_by, message[:40])).encode('ISO-8859-1')
    url = util.get_url(pwp.participant, wavelet.wave_id)

    query = model.AccountPhone.all()
    query.filter('account_id =', account.account_id)
    for phone in query:
        logging.debug('Sending message to %s %s' % (phone.phone_type, phone.phone_uid))
        if phone.phone_type == 'iphone':
            deferred.defer(send_message_to_iphone,
                           participant=pwp.participant,
                           phone_uid=phone.phone_uid,
                           phone_token=phone.phone_token,
                           wave_id=wavelet.wave_id,
                           wavelet_id=wavelet.wavelet_id,
                           blip_id=blip.blip_id,
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

    urllib2.urlopen(remote_url, urllib.urlencode(data))

    logging.info('Success calling remote notification server')


class Phone(webapp.RequestHandler):

    def get(self):
        self.response.contentType = 'application/json'

        path = [urllib.unquote(a) for a in self.request.path.split('/')[2:]]
        type = path[0]

        self.participant = self.request.get('participant')
        self.activation = self.request.get('activation')

        self.subscription_type = self.request.get('subscription_type')
        self.expiration_date = self.request.get('expiration_date')
        if self.expiration_date:
            self.expiration_date = datetime.date.fromtimestamp(float(self.expiration_date))

        self.phone_uid = self.request.get('phone_uid')
        self.phone_type = self.request.get('phone_type')
        self.phone_token = self.request.get('phone_token')
        if self.phone_token:
            self.phone_token = self.phone_token.replace('+', ' ')

        logging.debug(LOG % (type, self.participant, self.activation,
                             self.phone_uid, self.phone_token,
                             self.subscription_type, self.expiration_date))

        self.account = get_account(self.participant)

        if type == 'activate':
            if not self.account:
                self.find_account_by_phone()
            self.update_account()
            self.register_phone()

        elif self.account and type == 'deactivate':
            self.deactivate()
            return

        data = None
        if self.account:
            query = model.AccountPhone.all()
            query.filter('account_id =', self.account.account_id)
            phones = [phone.phone_uid for phone in query]

            query = model.ParticipantAccount.all()
            query.filter('account_id =', self.account.account_id)
            participants = [pa.participant for pa in query]

            data = { 'phones': phones,
                     'participants': participants,
                     'subscription_type': self.account.subscription_type,
                     'expiration_date': str(self.account.expiration_date),
                     'response': "OK" }
        else:
            data = { 'response': "ERROR" }

        self.response.out.write(simplejson.dumps(data))

    def find_account_by_phone(self):
        # Try to get account linked to phone if possible and link account with participant
        if self.phone_uid and self.phone_type:
            query = model.AccountPhone.all()
            query.filter('phone_uid =', self.phone_uid)
            account_phone = query.get()
            # TODO check in Phone for phone_token?
            if account_phone:
                self.account = model.Account.get_by_pk(account_phone.account_id,
                                                       None)
                pa = model.ParticipantAccount.get_by_pk(self.account.account_id,
                                                        self.participant,
                                                        create=True)
                pa.put()

    def update_account(self):
        # Update account or create one if it does not exist yet
        if self.subscription_type and self.expiration_date:
            save_history(self.account)

            if not self.account:
                self.account = get_account(self.participant, create=True)

            self.account.subscription_type = self.subscription_type
            self.account.expiration_date = self.expiration_date
            self.account.put()

    def register_phone(self):
        # Check for activation code for phone
        query = model.ParticipantPreferences.all()
        query.filter('participant =', self.participant);
        query.filter('activation =', self.activation);
        pp = query.get()

        # Create or update AccountPhone
        if pp and self.phone_uid and self.phone_type and self.phone_token:
            phone = model.AccountPhone.get_by_pk(self.account.account_id, self.phone_uid, create=True)
            phone.phone_type = self.phone_type
            phone.phone_token = self.phone_token
            phone.put()

    def deactivate(self):
        if self.phone_uid and self.phone_type:
            query = model.AccountPhone.all()
            query.filter('phone_uid =', self.phone_uid);
            query.filter('phone_type =', self.phone_type);
            db.delete(query)

        if self.account:
            save_history(self.account)
            db.delete(self.account)
            self.response.out.write('''{ 'response': "OK" }''')
            return

    def reply(self):
        pass