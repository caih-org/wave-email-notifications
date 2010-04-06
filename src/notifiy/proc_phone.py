# -*- coding: UTF-8 -*-

import logging
import urllib
import datetime

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
subscription type: %s
expiration date: %s'''


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

        self.account = phone.get_account(self.participant)

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
            phone.save_history(self.account)

            if not self.account:
                self.account = phone.get_account(self.participant, create=True)

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
            phone.save_history(self.account)
            db.delete(self.account)
            data = { 'response': "OK" }
            self.response.out.write(simplejson.dumps(data))
            return

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
