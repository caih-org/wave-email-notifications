#!/usr/bin/env python

from google.appengine.ext import db

NOTIFY_NONE = 0
NOTIFY_ONCE = 1
NOTIFY_ALL = 2

NOTIFY_TYPE_COUNT = 3

class ParticipantPreferences(db.Model):
    participant = db.StringProperty(required=True)
    notify = db.BooleanProperty(default=True)
    notify_initial = db.BooleanProperty(default=True)
    email = db.StringProperty()
    preferencesWaveId = db.StringProperty()


class ParticipantWavePreferences(db.Model):
    participant = db.StringProperty(required=True)
    waveId = db.StringProperty(required=True)
    notify_type = db.IntegerProperty(default=NOTIFY_NONE)
    visited = db.BooleanProperty(default=False)
    notify = db.BooleanProperty(default=None)


def upgrade():
    query = ParticipantPreferences.all()
    query.filter('notify_initial =', None)
    for pp in query:
        pp.notify_initial = True
        pp.put()

    query = ParticipantPreferences.all()
    query.filter('notify =', True)
    query.filter('notify_type =', NOTIFY_NONE)
    for pwp in query:
        pwp.notify_type = NOTIFY_ALL
        pwp.notify = None
        pwp.put()

