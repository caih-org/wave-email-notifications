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


def get_account(participant, create=False):
    query = model.ParticipantAccount.all()
    query.filter('participant =', participant)
    pa = query.get()

    if not pa and not create: return

    if not pa:
        account = model.Account.get_by_pk(uuid.uuid4(), None, create=True)
        account.put()
        pa = model.ParticipantAccount.get_by_pk(account.account_id, participant)
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

        self.participant = self.request.get('participant')
        self.activation = self.request.get('activation')

        self.subscription_type = self.request.get('subscription_type')
        self.expiration_date = self.request.get('expiration_date')

        self.phone_uid = self.request.get('phone_uid')
        self.phone_type = self.request.get('phone_type')
        self.phone_token = self.request.get('phone_token')
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

        if self.account:
            query = model.AccountPhone.all()
            query.filter('account_id =', self.account.account_id)
            phones = [phone.phone_uid for phone in query]

            self.response.out.write(JSON % (', '.join(phones),
                                            self.account.subscription_type,
                                            self.account.expiration_date))
        else:
            self.response.out.write('''{ 'response': "ERROR" }''')

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
