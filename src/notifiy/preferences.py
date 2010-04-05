# -*- coding: UTF-8 -*-

from waveapi import element
from waveapi import robot

from notifiy import constants
from notifiy import model
from notifiy import templates

PARTICIPANT_DATA_DOC = '%s/participant' % constants.ROBOT_ADDRESS
WAVEID_DATA_DOC = '%s/preferencesWaveId' % constants.ROBOT_ADDRESS
VERSION_DATA_DOC = '%s/preferencesVersion' % constants.ROBOT_ADDRESS
PREFERENCES_VERSION = '12'

SETTIE_ROBOT = 'settie@a.gwave.com'


def is_preferences_wave(wavelet):
    return VERSION_DATA_DOC in wavelet.root_blip.datadocs


def find_participant(wavelet, participant=None):
    if participant == None:
        data = wavelet.root_blip.datadocs[PARTICIPANT_DATA_DOC]
        if data:
            return data

    return participant


def preferences_wave_create(wavelet, participant):
    domain = participant.split('@')[1]
    participants =[ constants.ROBOT_ADDRESS, SETTIE_ROBOT, participant ]
    prefs_wavelet = wavelet.robot.new_wave(domain, participants, submit=True)
    preferences_wave_update(prefs_wavelet, participant)


def preferences_wave_update(wavelet, participant=None, force=False):
    if not force and wavelet.root_blip.datadocs[VERSION_DATA_DOC] == PREFERENCES_VERSION: return

    participant = find_participant(participant)
    pp = model.ParticipantPreferences.get_by_pk(participant)

    wavelet.root_blip.all().delete()

    wavelet.title = 'Notifiy global preferences'

    wavelet.root_blip.datadocs[PARTICIPANT_DATA_DOC] = participant
    wavelet.root_blip.datadocs[WAVEID_DATA_DOC] = pp.preferences_wave_id
    wavelet.root_blip.datadocs[VERSION_DATA_DOC] = PREFERENCES_VERSION

    wavelet.root_blip.append('\n')
    wavelet.root_blip.append([ element.Check('notify', pp.notify), ' Notify me to this email:\n', element.Input('email', pp.email), '\n' ])
    wavelet.root_blip.append([ element.Check('notify_initial', pp.notify_initial), ' Send initial notifications\n'])
    wavelet.root_blip.append('\n')
    wavelet.root_blip.append('Phone activation code: %s\n' % pp.activation)
    wavelet.root_blip.append('\n')
    wavelet.root_blip.append([ element.Button('save_pp', 'Save'), ' ', element.Button('refresh_pp', 'Refresh'), '\n' ])
    wavelet.root_blip.append('\n')
    wavelet.root_blip.append([ 'Execute global commands: (try "help")', element.Input('command', ''), element.Button('exec_pp', 'Exec') ])


def preferences_wave_delete(wavelet):
    participant = find_participant(wavelet)
    pp = model.ParticipantPreferences.get_by_pk(participant)
    if not pp: return

    prefs_wavelet = wavelet.robot.fetch_wavelet(pp.preferencesWaveId, None)
    prefs_wavelet.root_blip.all().delete()
    prefs_wavelet.append('Please delete this wave')


def handle_event(event, wavelet):
    if not PARTICIPANT_DATA_DOC in wavelet.root_blip.datadocs: return
    participant = wavelet.root_blip.datadocs[PARTICIPANT_DATA_DOC]
    if participant != event.modified_by: return

    if event.button_name == 'save_pp':
        pp = model.ParticipantPreferences.get_by_pk(participant)
        for p in ['notify', 'email', 'notify_initial']:
            pp.__setattr__(p, wavelet.root_blip.elements['notify'].value)
        wavelet.reply(templates.PREFERENCES_SAVED)

    elif event.button_name == 'refresh_pp':
        if ExecHandler(event, wavelet).refresh():
            wavelet.reply(templates.COMMAND_SUCCESSFUL % 'refresh')
        elif result == False:
            wavelet.reply(templates.ERROR_TRY_AGAIN)

    elif event.button_name == 'exec_pp':
        eh = ExecHandler(event, wavelet)
        command = wavelet.root_blip.elements['command'].value.split(' ')
        if hasattr(eh, command[0]):
            result = getattr(eh, command[0])(*command[1:])
            if result == True:
                wavelet.reply(templates.COMMAND_SUCCESSFUL % command)
            elif result == False:
                wavelet.reply(templates.ERROR_TRY_AGAIN)

        else:
            wavelet.reply(templates.COMMAND_UNKNOWN % command)


class ExecHandler(object):

    def __init__(self, event, wavelet):
        self.event = event
        self.wavelet = wavelet

    def help(self):
        self.wavelet.reply(templates.COMMANDS_HELP)

    def refresh(self):
        preferences_wave_update(self.wavelet, self.event.modified_by, force=True)
        return True

    def clean(self):
        for blip in self.wavelet.blips:
            if blip.blip_id != self.wavelet.root_blip.blip_id:
                self.wavelet.remove(blip)

    def reset(self):
        preferences_wave_delete(self.wavelet)
        preferences_wave_create(self.wavelet, self.event.modified_by)
        return True
