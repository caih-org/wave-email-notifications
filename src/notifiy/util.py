# -*- coding: UTF-8 -*-

import base64
import urllib


def get_url(participant, wave_id):
    domain = participant.split('@')[1]
    if wave_id:
        wave_id = urllib.quote(urllib.quote(wave_id))

    if wave_id and domain == 'googlewave.com':
        return 'https://wave.google.com/wave/#restored:wave:%s' % wave_id
    elif wave_id:
        return 'https://wave.google.com/a/%s/#restored:wave:%s' % (wave_id, domain)
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


def process_body(body):
    new_body = []
    buffer = []

    for line in body.split('\n'):
        if not line:
            new_body = new_body + buffer + [ line ]
            buffer = []
        elif line.strip()[0] == '>':
            buffer = []
        else:
            buffer.append(line)

    new_body = new_body + buffer

    return '\n'.join(new_body).strip()
