#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import random

from google.appengine.ext import db
# TODO from google.appengine.api import memcache

from migrationmodel import MigratingModel

NOTIFY_NONE = 0
NOTIFY_ONCE = 1
NOTIFY_ALL = 2

NOTIFY_TYPE_COUNT = 3


class AccountPhone(MigratingModel):
    migration_version = 1

    account_id = db.StringProperty(required=True)
    phone_uid = db.StringProperty()
    phone_type = db.StringProperty()
    phone_token = db.StringProperty()

    pk = ['account_id', 'phone_uid']


class Account(MigratingModel):
    migration_version = 1

    account_id = db.StringProperty(required=True)
    to_date = db.DateProperty()
    subscription_type = db.StringProperty()
    expiration_date = db.DateProperty()

    pk = ['account_id', 'to_date']


class ParticipantAccount(MigratingModel):
    migration_version = 1

    account_id = db.StringProperty(required=True)
    participant = db.StringProperty(required=True)

    pk = ['account_id', 'participant']

    def get_key_name(self):
        return ParticipantAccount.get_key(self.account_id, self.participant)


class ParticipantPreferences(MigratingModel):
    migration_version = 3

    participant = db.StringProperty(required=True)
    notify = db.BooleanProperty(default=True)
    notify_initial = db.BooleanProperty(default=True)
    email = db.EmailProperty()
    activation = db.StringProperty()
    preferences_wave_id = db.StringProperty()

    pk = ['participant']

    preferencesWaveId = db.StringProperty(default=None) # Deprecated use preferences_wave_id

    def __init__(self, *args, **kwds):
        self.activation = random_activation()
        super(ParticipantPreferences, self).__init__(*args, **kwds)

    def put(self, *args, **kwds):
        # TODO memcache.set(self.get_key(), self, namespace='pp')
        super(ParticipantPreferences, self).put(*args, **kwds)

    def migrate_1(self):
        if self.notify_initial == None:
            self.notify_initial = True

    def migrate_2(self):
        if self.activation == None:
            self.activation = random_activation()

    def migrate_2(self):
        if self.preferencesWaveId:
            self.preferences_wave_id = self.preferencesWaveId;


class ParticipantWavePreferences(MigratingModel):
    migration_version = 2

    participant = db.StringProperty(required=True)
    wave_id = db.StringProperty(required=True)
    notify_type = db.IntegerProperty(default=NOTIFY_NONE)
    visited = db.BooleanProperty(default=False)
    last_visited = db.DateTimeProperty()

    pk = ['participant', 'wave_id']

    waveId = db.StringProperty(default=None) # Deprecated use wave_id
    notify = db.BooleanProperty(default=None) # Deprecated use notify_type

    def put(self, *args, **kwds):
        # TODO memcache.set(self.get_key(), self, namespace='pwp')
        super(ParticipantWavePreferences, self).put(*args, **kwds)

    def migrate_1(self):
        if self.notify != None:
            if self.notify:
                self.notify_type = NOTIFY_ALL
            self.notify = None

    def migrate_2(self):
        if self.waveId:
            self.wave_id = self.waveId;


class ApplicationSettings(MigratingModel):
    migration_version = 0

    keyname = db.StringProperty()
    value = db.StringProperty()

    pk = ['keyname']

    @classmethod
    def get(class_, keyname):
        return class_.get_by_pk(keyname)


def random_activation():
    return ''.join([str(random.randint(0, 9)) for a in range(9)])

