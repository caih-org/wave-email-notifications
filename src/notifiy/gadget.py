# -*- coding: UTF-8 -*-

from waveapi.element import Gadget

from notifiy import constants

GADGET_URL = '%s/%s' % (constants.ROBOT_BASE_URL, 'notifiy.xml')


def is_gadget_present(wavelet):
    return wavelet.root_blip.first(GADGET_URL) is not None


def gadget_add(wavelet):
    if not is_gadget_present(wavelet):
        wavelet.root_blip.at(0).insert(Gadget(GADGET_URL))


def gadget_remove(wavelet):
    if is_gadget_present(wavelet):
        wavelet.root_blip.all(GADGET_URL).delete()
