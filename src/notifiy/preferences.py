# -*- coding: UTF-8 -*-

import logging

from waveapi import element

from notifiy import constants
from notifiy import model
from notifiy import templates

PARTICIPANT_DATA_DOC = '%s/participant' % constants.ROBOT_ADDRESS
VERSION_DATA_DOC = '%s/preferencesVersion' % constants.ROBOT_ADDRESS
PREFERENCES_VERSION = '12'

SETTIE_ROBOT = 'settie@a.gwave.com'


def is_preferences_wave(wavelet):
    return VERSION_DATA_DOC in wavelet.data_documents


def find_participant(wavelet, participant=None):
    if PARTICIPANT_DATA_DOC in wavelet.data_documents:
        return wavelet.data_documents[PARTICIPANT_DATA_DOC]
    else:
        return participant


def fetch_preferences_wavelet(wavelet, preferences_wave_id):
    preferences_wavelet = wavelet.robot.fetch_wavelet(preferences_wave_id)
    wavelet.robot.submit_with(wavelet);
    return preferences_wavelet


def create_preferences_wave(wavelet, participant):
    domain = participant.split('@')[1]
    participants =[ constants.ROBOT_ADDRESS, SETTIE_ROBOT, participant ]
    prefs_wavelet = wavelet.robot.new_wave(domain, participants, submit=True)
    update_preferences_wavelet(prefs_wavelet, participant)


def update_preferences_wavelet(wavelet, participant=None, force=False):
    if not force and wavelet.data_documents[VERSION_DATA_DOC] == PREFERENCES_VERSION: return

    participant = find_participant(wavelet, participant)
    pp = model.ParticipantPreferences.get_by_pk(participant)

    wavelet.title = 'Notifiy global preferences'

    wavelet.data_documents[PARTICIPANT_DATA_DOC] = participant
    wavelet.data_documents[VERSION_DATA_DOC] = PREFERENCES_VERSION

    content = []

    content = content + [ element.Image(url=constants.ROBOT_IMG, width=50, height=50, caption=constants.ROBOT_NAME.title()) ]
    content.append('\n')
    content = content + [ element.Check('notify', pp.notify), ' Notify me to this email:\n', element.Input('email', pp.email), '\n' ]
    content = content + [ element.Check('notify_initial', pp.notify_initial), ' Send initial notifications', '\n' ]
    content.append('\n')
    content = content + [ 'Phone activation code: %s\n' % pp.activation, '\n' ]
    content = content + [ element.Button('save_pp', 'Save'), ' ', element.Button('refresh_pp', 'Refresh'), '\n' ]
    content.append('\n')
    content = content + [ 'Execute global commands: (try "help")', element.Input('command', ''), element.Button('exec_pp', 'Exec') ]

    wavelet.root_blip.all().replace(content);


def delete_preferences_wavelet(wavelet):
    if not wavelet: return

    participant = find_participant(wavelet)
    pp = model.ParticipantPreferences.get_by_pk(participant)
    if not pp: return

    prefs_wavelet = fetch_preferences_wavelet(wavelet, pp.preferences_wave_id)
    del prefs_wavelet.data_documents[PARTICIPANT_DATA_DOC]
    del prefs_wavelet.data_documents[VERSION_DATA_DOC]
    prefs_wavelet.title = "Please delete this wave"
    prefs_wavelet.root_blip.all().delete()


def handle_event(event, wavelet):
    participant = find_participant(wavelet, event.modified_by)
    if participant != event.modified_by: return

    if event.button_name == 'save_pp':
        pp = model.ParticipantPreferences.get_by_pk(participant)
        for t, f, p in [ (element.Check, bool, 'notify'),
                         (element.Input, str, 'email'),
                         (element.Check, bool, 'notify_initial') ]:
            form_element = wavelet.root_blip.first(t, name=p).value()
            pp.__setattr__(p, f(form_element.value))
        wavelet.reply(templates.PREFERENCES_SAVED)

    elif event.button_name == 'refresh_pp':
        if ExecHandler(event, wavelet).refresh():
            wavelet.reply(templates.COMMAND_SUCCESSFUL % 'refresh')
        elif result == False:
            wavelet.reply(templates.ERROR_TRY_AGAIN)

    elif event.button_name == 'exec_pp':
        eh = ExecHandler(event, wavelet)
        form_element = wavelet.root_blip.first(element.Input, name='command').value()
        command = form_element.value.split(' ')
        if hasattr(eh, command[0]):
            result = getattr(eh, command[0])(*command[1:])
            if result == True:
                wavelet.reply(templates.COMMAND_SUCCESSFUL % command)
            elif result == False:
                wavelet.reply(templates.ERROR_TRY_AGAIN)
            elif result:
                wavelet.reply(result)

        else:
            wavelet.reply(templates.COMMAND_UNKNOWN % command)


class ExecHandler(object):

    def __init__(self, event, wavelet):
        self.event = event
        self.wavelet = wavelet

    def help(self):
        return templates.COMMANDS_HELP

    def refresh(self):
        update_preferences_wavelet(self.wavelet, self.event.modified_by, force=True)
        return True

    def clean(self):
        delete = []
        for blip_id in self.wavelet.blips:
            if blip_id != self.wavelet.root_blip.blip_id:
                delete.append(blip_id)
        for blip_id in delete:
            self.wavelet.delete(blip_id)

    def reset(self):
        delete_preferences_wavelet(self.wavelet)
        create_preferences_wave(self.wavelet, self.event.modified_by)
        return True

    def recreate(self):
        create_preferences_wave(self.wavelet, self.event.modified_by)
        return True
