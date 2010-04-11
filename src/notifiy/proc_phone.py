# -*- coding: UTF-8 -*-

import datetime
import logging
import urllib
import urllib2

from google.appengine.ext import db
from google.appengine.ext import webapp

from waveapi import simplejson

from notifiy import model
from notifiy import util
from notifiy import phone

LOG = '''\
--- TYPE: %s ---
participant: %s
activation: %s
phone uid: %s
phone token: %s
receipt data: %s'''

ITUNES_URL = 'https://buy.itunes.apple.com/verifyReceipt'


def freetrial(d):
    return datetime.date(d.year, d.month + 1, d.day)


def oneyear(d):
    return datetime.date(d.year + 1, d.month, d.day)


def sixmonths(d):
    return datetime.date(d.year, d.month + 6, d.day)

FREE_TRIAL = 'com.wavenotifications.notifiy.FreeTrial001'

PRODUCT_IDS = {
    FREE_TRIAL : freetrial,
    'com.wavenotifications.notifiy.OneYear001': oneyear,
    'com.wavenotifications.notifiy.SixMonths001': sixmonths
}


class PhoneProcess(webapp.RequestHandler):

    def post(self, *args):
        self.get()

    def get(self, *args):
        self.response.contentType = 'application/json'

        path = [urllib.unquote(a) for a in self.request.path.split('/')[2:]]
        req_type = path[0]

        self.participant = self.request.get('participant')
        self.activation = self.request.get('activation')

        self.receipt_data = self.request.get('receipt_data')

        self.phone_uid = self.request.get('phone_uid')
        self.phone_type = self.request.get('phone_type')
        self.phone_token = self.request.get('phone_token')
        if self.phone_token:
            self.phone_token = self.phone_token.replace('+', ' ')

        logging.debug(LOG, req_type, self.participant, self.activation,
                      self.phone_uid, self.phone_token, self.receipt_data)

        self.account = None

        if req_type.startswith('_'): return
        error = getattr(self, req_type)()
        if error == False: return

        data = None
        if not error and self.account:
            query = model.Phone.all()
            query.filter('account_id =', self.account.account_id)
            phones = [phone1.phone_uid for phone1 in query]

            query = model.ParticipantPreferences.all()
            query.filter('account_id =', self.account.account_id)
            participants = [pa.participant for pa in query]

            data = { 'phones': phones,
                     'participants': participants,
                     'subscription_type': self.account.subscription_type,
                     'expiration_date': str(self.account.expiration_date),
                     'response': "OK" }
        else:
            data = { 'response': "ERROR", 'message': error or 'Invalid Google Wave account' }

        self.response.out.write(simplejson.dumps(data))

    def info(self):
        '''Gets info about an account by participant of phone'''

        if self.participant:
            self.account = phone.get_account(self.participant)
            if not self.account: return 'No account found for participant'

        self._find_account_by_phone()
        if not self.account and not self.participant:
            return 'No account found for phone'

    def activate(self):
        '''Activates either a phone or a participant'''

        if self.participant and not self._validate():
            return 'Invalid Google Wave account or activation code'

        self.account = phone.get_account(self.participant)
        self._find_account_by_phone() or self._create_account()

        if not self.account:
            return 'No account found or account could not be created.'

        if self.receipt_data:
            error = self._update_account()
        else:
            error = self._register_phone()

        return error

    def deactivate(self):
        if self.participant:
            if not self._validate():
                return 'Invalid Google Wave account or activation code'

            self.account = phone.get_account(self.participant)
            if not self.account:
                return 'Participant doesn\'t have an account'

            query = model.ParticipantPreferences.all()
            query.filter('account_id =', self.account.account_id)
            if len(list(query)) == 1:
                return 'Cannot deactivate this participant from account. There\'s only participant linked to the account.'

            pp = model.ParticipantPreferences.get_by_pk(self.participant)
            pp.account_id = None
            pp.put()

        elif self.phone_type and self.phone_uid and self.phone_token:
            self._find_account_by_phone()

            query = model.Phone.all()
            query.filter('phone_type =', self.phone_type)
            query.filter('phone_uid =', self.phone_uid)
            query.filter('phone_token =', self.phone_token)
            db.delete(query)

    def reply(self):
        participant = self.request.get('participant')
        wave_id = self.request.get('wave_id')
        wavelet_id = self.request.get('wavelet_id')
        blip_id = self.request.get('blip_id')
        message = self.request.get('message')

        logging.debug('incoming reply from phone [participant=%s, wave_id=%s,' +
                      'wavelet_id=%s, blip_id=%s]: %s', participant, wave_id,
                      wavelet_id, blip_id, message)

        util.reply_wavelet(wave_id, wavelet_id, blip_id, participant, message)

    def fetch(self):
        participant = self.request.get('participant')
        wave_id = self.request.get('wave_id')
        wavelet_id = self.request.get('wavelet_id')
        blip_id = self.request.get('blip_id')

        wavelet = util.fetch_wavelet(wave_id, wavelet_id, participant)
        if blip_id in wavelet.blips:
            blip = wavelet.blips[blip_id]
            data = { 'content': blip.text }
            self.response.out.write(simplejson.dumps(data))
            return False
        else:
            return 'Blip not found'

    def _validate(self):
        '''Check for activation code for phone'''

        query = model.ParticipantPreferences.all()
        query.filter('participant =', self.participant)
        query.filter('activation =', self.activation)

        return bool(query.get())

    def _find_account_by_phone(self):
        '''Try to get account linked to phone if possible'''

        if not self.account and self.phone_type and self.phone_uid and self.phone_token:
            query = model.Phone.all()
            query.filter('phone_type =', self.phone_type)
            query.filter('phone_uid =', self.phone_uid)
            query.filter('phone_token =', self.phone_token)
            account_phone = query.get()

            if not account_phone: return False

            self.account = model.Account.get_by_pk(account_phone.account_id,
                                                   None)
            if self.participant:
                pp = model.ParticipantPreferences.get_by_pk(self.participant)
                pp.account_id = self.account.account_id
                pp.put()

        return bool(self.account)

    def _create_account(self):
        '''Try to create an account'''

        if self.account or not self.participant: return

        self.account = phone.get_account(self.participant, create=True)

    def _update_account(self):
        '''Update account or create one if it does not exist yet'''

        if not self.receipt_data: return

        if self.receipt_data == FREE_TRIAL:
            if self.account.subscription_type:
                return 'Cannot activate the free trial, a subscription already exists.'

            purchase_date = datetime.datetime.now()
            transaction_id = FREE_TRIAL
            subscription_type = FREE_TRIAL
        else:
            data = simplejson.dumps({ 'receipt-data': self.receipt_data })
            json = simplejson.loads(urllib2.urlopen(ITUNES_URL, data).read())

            if json['status'] != 0:
                return 'Invalid receipt'

            subscription_type = json['receipt']['product_id']
            transaction_id = json['receipt']['transaction_id']

            query = model.Account.all()
            query.filter('transaction_id =', transaction_id)
            if query.get():
                return 'Cannot use receipt, account already activated with this receipt.'

            if self.account.transaction_id and self.account.transaction_id != transaction_id:
                purchase_date = self.account.expiration_date
            else:
                purchase_date = json['receipt']['purchase_date'].split(" ")[0]
                purchase_date = datetime.datetime.strptime(purchase_date, "%Y-%m-%d")

        if subscription_type in PRODUCT_IDS:
            self._save_history()
            self.account.expiration_date = PRODUCT_IDS[subscription_type](purchase_date)
            self.account.subscription_type = subscription_type
            self.account.transaction_id = subscription_type
            self.account.receipt_data = self.receipt_data
            self.account.put()
        else:
            return "Invalid Product ID %s" % self.account.subscription_type

    def _save_history(self):
        account = model.Account.get_by_pk(self.account.account_id,
                                          datetime.datetime.now(), create=True)
        account.subscription_type = self.account.subscription_type
        account.expiration_date = self.account.expiration_date
        account.receipt_data = self.account.receipt_data
        account.transaction_id = self.account.transaction_id
        account.put()

    def _register_phone(self):
        '''Create or update Phone'''

        if self.phone_uid and self.phone_type and self.phone_token:
            ap = model.Phone.get_by_pk(self.phone_type, self.phone_uid,
                                              self.phone_token, create=True)
            ap.account_id = self.account.account_id
            ap.put()
