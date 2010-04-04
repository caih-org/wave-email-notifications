# -*- coding: UTF-8 -*-

import base64
import urllib


def get_url(participant, wave_id):
    domain = participant.split('@')[1]
    quoted_wave_id = urllib.quote(urllib.quote(wave_id))

    if wave_id and domain == 'googlewave.com':
        return 'https://wave.google.com/wave/#restored:wave:%s' % quoted_wave_id
    elif wave_id:
        return 'https://wave.google.com/a/%s/#restored:wave:%s' % (quoted_wave_id, domain)
    else:
        return ''


def modified_b64encode(s):
    if type(s) == unicode:
        s = s.decode('UTF-8')

    return base64.urlsafe_b64encode(s).replace('=', '')

def modified_b64decode(s):
    while len(s) % 4 != 0:
        s = s + '='

    return base64.urlsafe_b64decode(s).encode('UTF-8')
