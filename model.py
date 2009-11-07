#!/usr/bin/env python

from google.appengine.ext import db


class ParticipantPreferences(db.Model):
    participant = db.StringProperty(required=True)
    notify = db.BooleanProperty(default=True)
    email = db.StringProperty()
    preferencesWaveId = db.StringProperty()
