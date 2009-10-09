#!/usr/bin/env python

from google.appengine.ext import db


class ParticipantPreferences(db.Model):
    participant = db.StringProperty(required=True)
    notify = db.BooleanProperty(default=True)
    email = db.StringProperty()


class ParticipantWavePreferences(db.Model):
    participant = db.StringProperty(required=True)
    waveId = db.StringProperty(required=True)
    wave_title = db.StringProperty()
    notify = db.BooleanProperty(default=True)
    last_updated = db.DateTimeProperty()
