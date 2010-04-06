# -*- coding: UTF-8 -*-

import datetime
import time
import logging
import urllib
import urllib2

from google.appengine.ext import db
from google.appengine.ext import webapp

from waveapi import simplejson

from notifiy import model
from notifiy import util
from notifiy import phone
from notifiy.robot import create_robot, setup_oauth

LOG = '''\
--- TYPE: %s ---
participant: %s
activation: %s
phone uid: %s
phone token: %s
receipt data: %s'''

ITUNES_URL = 'https://buy.itunes.apple.com/verifyReceipt'

PRODUCT_IDS = [
    'com.wavenotifications.notifiy.OneYear001',
    'com.wavenotifications.notifiy.SixMonths001'
]

class Phone(webapp.RequestHandler):

    def post(self):
        self.get()

    def get(self):
        self.response.contentType = 'application/json'

        path = [urllib.unquote(a) for a in self.request.path.split('/')[2:]]
        type = path[0]

        self.participant = self.request.get('participant')
        self.activation = self.request.get('activation')

        self.receipt_data = self.request.get('receipt_data')

        self.phone_uid = self.request.get('phone_uid')
        self.phone_type = self.request.get('phone_type')
        self.phone_token = self.request.get('phone_token')
        if self.phone_token:
            self.phone_token = self.phone_token.replace('+', ' ')

        logging.debug(LOG % (type, self.participant, self.activation,
                             self.phone_uid, self.phone_token, self.receipt_data))

        self.account = phone.get_account(self.participant)

        error = None
        if type == 'activate':
            # Check for activation code for phone
            query = model.ParticipantPreferences.all()
            query.filter('participant =', self.participant);
            query.filter('activation =', self.activation);

            if query.get():
                if not self.account:
                    error = self.find_account_by_phone()
                if not error:
                    error = self.update_account()
                    if not error:
                        error = self.register_phone()
            else:
                error = 'Invalid Google Wave account or activation code'

        elif self.account and type == 'deactivate':
            self.deactivate()
            if self.account: return

        data = None
        if not error and self.account:
            query = model.AccountPhone.all()
            query.filter('account_id =', self.account.account_id)
            phones = [phone1.phone_uid for phone1 in query]

            query = model.ParticipantAccount.all()
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

    def find_account_by_phone(self):
        '''Try to get account linked to phone if possible and link account with participant'''

        if self.phone_uid and self.phone_type:
            query = model.AccountPhone.all()
            query.filter('phone_uid =', self.phone_uid)
            account_phone = query.get()
            # TODO check in Phone for phone_token?
            if not account_phone: return ''

            self.account = model.Account.get_by_pk(account_phone.account_id,
                                                   None)
            pa = model.ParticipantAccount.get_by_pk(self.account.account_id,
                                                    self.participant,
                                                    create=True)
            pa.put()

    def update_account(self):
        '''Update account or create one if it does not exist yet'''

        if self.receipt_data:
            phone.save_history(self.account)

            if not self.account:
                self.account = phone.get_account(self.participant, create=True)

            data = simplejson.dumps({ 'receipt-data': self.receipt_data })
            response = urllib2.urlopen(ITUNES_URL, data).read()
            logging.debug(response)
            json = simplejson.loads(urllib2.urlopen(ITUNES_URL, data).read())

            if json['status'] != 0:
                return 'Invalid receipt'

            self.account.subscription_type = json['receipt']['product_id']

            purchase_date = json['receipt']['purchase_date']
            d = datetime.datetime.strptime(purchase_date.split(" ")[0], "%Y-%m-%d")

            if self.account.subscription_type == PRODUCT_IDS[0]:
                d = datetime.date(d.year + 1, d.month, d.day)
            elif self.account.subscription_type == PRODUCT_IDS[1]:
                d = datetime.date(d.year, d.month + 6, d.day)
            else:
                d = None

            if d:
                self.account.expiration_date = d
            else:
                return "Invalid Product ID %s" % self.account.subscription_type

            self.account.put()

    def register_phone(self):
        '''Create or update AccountPhone'''

        if self.phone_uid and self.phone_type and self.phone_token:
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
            phone.save_history(self.account)
            db.delete(self.account)
            data = { 'response': "OK" }
            self.response.out.write(simplejson.dumps(data))

    def reply(self):
        participant = self.request.get('participant')
        wave_id = self.request.get('wave_id')
        wavelet_id = self.request.get('wavelet_id')
        blip_id = self.request.get('blip_id')
        body = '%s: %s' % (participant, util.process_body(self.request.get('body')))

        logging.debug('incoming reply from phone [participant=%s, wave_id=%s, wavelet_id=%s, blip_id=%s]: %s'
                      % (participant, wave_id, wavelet_id, blip_id, body))

        robot = create_robot(run=False)
        setup_oauth(robot, participant.split('@')[1])

        # TODO wavelet = robot.fetch_wavelet(wave_id, wavelet_id, participant)
        wavelet = robot.fetch_wavelet(wave_id, wavelet_id)
        if blip_id:
            blip = wavelet.blips[blip_id]
            blip.reply().append(body)
        else:
            wavelet.reply(body)
        robot.submit(wavelet)
