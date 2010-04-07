# -*- coding: UTF-8 -*-

from waveapi.element import Gadget

from notifiy import constants
from notifiy import model
from notifiy import preferences

GADGET_URL = '%s/%s.xml' % (constants.ROBOT_BASE_URL, constants.ROBOT_ID)


def is_gadget_present(wavelet):
    return bool(wavelet.root_blip.first(Gadget, url=GADGET_URL))


def gadget_add(wavelet):
    if not is_gadget_present(wavelet):
        wavelet.root_blip.at(1).insert(Gadget(GADGET_URL))


def gadget_remove(wavelet):
    if is_gadget_present(wavelet):
        wavelet.root_blip.all(GADGET_URL).delete()


def handle_state_change(event, wavelet):
    if not wavelet.root_blip.blip_id == event.blip_id: return
    if not wavelet.root_blip.all(Gadget)[event.index].url == GADGET_URL: return

    pp = model.ParticipantPreferences.get_by_pk(event.modified_by)
    preferences_wavelet = preferences.fetch_preferences_wavelet(wavelet, pp.preferences_wave_id, None)
    eh = preferences.ExecHandler(event, preferences_wavelet)
    eh.reset()
