#!/usr/bin/env python

from google.appengine.ext import db


class ParticipantPreferences(db.Model):
    participant = db.StringProperty(required=True)
    notify = db.BooleanProperty(default=True)
    email = db.StringProperty()
    preferencesWaveId = db.StringProperty()


class ParticipantWavePreferences(db.Model):
    participant = db.StringProperty(required=True)
    waveId = db.StringProperty(required=True)
    notify = db.BooleanProperty(default=False)


def get_pp(participant, create=False):
    query = ParticipantPreferences.all()
    query.filter('participant =', participant)
    pp = query.get()

    if create and not pp:
        pp = ParticipantPreferences(participant=participant)
        # FIXME This should be more generic
        pp.email = participant.replace('@googlewave.com', '@gmail.com')
        pp.put()

    return pp


def get_pwp(participant, waveId, create=False):
    query = ParticipantWavePreferences.all()
    query.filter('participant =', participant)
    query.filter('waveId =', waveId)
    pwp = query.get()

    if create and not pwp:
        pwp = ParticipantWavePreferences(participant=participant, waveId=waveId)
        pwp.put()

    return pwp

