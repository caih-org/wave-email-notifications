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
    content_buffer = []

    for line in body.split('\n'):
        if not line:
            new_body = new_body + content_buffer + [ line ]
            content_buffer = []
        elif line.strip()[0] == '>':
            content_buffer = []
        else:
            content_buffer.append(line)

    new_body = new_body + content_buffer

    return '\n'.join(new_body).strip()


def fetch_wavelet(wave_id, wavelet_id, participant):
    from notifiy.robot import create_robot
    robot = create_robot(run=False, domain=participant.split('@')[1])

    # TODO return robot.fetch_wavelet(wave_id, wavelet_id, participant)
    return robot.fetch_wavelet(wave_id, wavelet_id)


def reply_wavelet(wave_id, wavelet_id, blip_id, participant, message):
    wavelet = fetch_wavelet(wave_id, wavelet_id, participant)
    body = '%s: %s' % (participant, message) # TODO remove when proxy_for works
    if blip_id in wavelet.blips:
        blip = wavelet.blips[blip_id]
        blip = blip.reply()
        blip.append(body)
    else:
        blip = wavelet.reply(body)

    wavelet.robot.submit(wavelet)

    from notifiy import notifications
    notifications.notify_submitted(wavelet, blip, participant, message)
