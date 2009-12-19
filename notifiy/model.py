#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

import logging
import random

from google.appengine.ext import db
from google.appengine.api import memcache

from migrationmodel import MigratingModel

NOTIFY_NONE = 0
NOTIFY_ONCE = 1
NOTIFY_ALL = 2

NOTIFY_TYPE_COUNT = 3


class ParticipantPhone(MigratingModel):
    migration_version = 1

    participant = db.StringProperty(required=True)
    phone_uid = db.StringProperty()
    phone_token = db.StringProperty()

    @classmethod
    def get_key(self, participant, phone_uid, phone_token):
        return '%s:%s:%s' % (participant, phone_uid, phone_token)

class ParticipantPreferences(MigratingModel):
    migration_version = 2

    participant = db.StringProperty(required=True)
    notify = db.BooleanProperty(default=True)
    notify_initial = db.BooleanProperty(default=True)
    email = db.StringProperty()
    activation = db.StringProperty()
    preferencesWaveId = db.StringProperty()

    def __init__(self, *args, **kwds):
        self.activation = random_activation()
        super(ParticipantPreferences, self).__init__(*args, **kwds)

    @classmethod
    def get_key(self, participant):
        return participant

    def get_phone_preferences(self):
        query = ParticipantPhone.all()
        query.filter('participant =', self.participant)
        return list(query);

    def put(self, *args, **kwds):
        key_name = ParticipantPreferences.get_key(self.participant)
        memcache.set(key_name, self, namespace='pp')
        super(ParticipantPreferences, self).put(*args, **kwds)

    def migrate_1(self):
        if self.notify_initial == None:
            self.notify_initial = True

    def migrate_2(self):
        if self.activation == None:
            self.activation = random_activation()


class ParticipantWavePreferences(MigratingModel):
    migration_version = 1

    participant = db.StringProperty(required=True)
    waveId = db.StringProperty(required=True)
    notify_type = db.IntegerProperty(default=NOTIFY_NONE)
    visited = db.BooleanProperty(default=False)
    last_visited = db.DateTimeProperty()

    notify = db.BooleanProperty(default=None) # Deprecated use notify_type

    @classmethod
    def get_key(self, participant, waveId):
        return '%s:%s' % (participant, waveId)

    def put(self, *args, **kwds):
        key_name = ParticipantWavePreferences.get_key(self.participant, self.waveId)
        memcache.set(key_name, self, namespace='pwp')
        super(ParticipantWavePreferences, self).put(*args, **kwds)

    def migrate_1(self):
        if self.notify != None:
            if self.notify:
                self.notify_type = NOTIFY_ALL
            self.notify = None


class ApplicationSettings(MigratingModel):
    migration_version = 0

    keyname = db.StringProperty()
    value = db.StringProperty()

    def get_key(self):
        return self.keyname

    @classmethod
    def get(self, keyname):
        query = ApplicationSettings.all()
        query.filter('keyname =', keyname)
        return query.get().value


def random_activation():
    return ''.join([str(random.randint(0, 9)) for a in range(9)])

