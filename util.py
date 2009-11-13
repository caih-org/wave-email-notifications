import logging
import urllib
import urllib2
import uuid

from google.appengine.api import mail
from google.appengine.api.labs import taskqueue

from waveapi import document
from waveapi import robot_abstract
from waveapi import util

import model

ROBOT_NAME = 'notifiy'
ROBOT_ID = 'wave-email-notifications'
ROBOT_ADDRESS = '%s@appspot.com' % ROBOT_ID
ROBOT_BASE_URL = 'http://%s.appspot.com' % ROBOT_ID
ROBOT_EMAIL = '%s@ecuarock.net' % ROBOT_ID
ROBOT_HOME_PAGE = 'http://%s.googlecode.com/' % ROBOT_ID

GADGET_URL = '%s/%s.xml' % (ROBOT_BASE_URL, ROBOT_ID)

INITIAL_MESSAGE = 'To receive email notifications visit this wave and activate them.'
MESSAGE_TEMPLATE = '''\
%s

======
Visit this wave: %s
Change global notification preferences: %s
[%s:%s]
'''

WAVELET_TYPE = util.StringEnum('NORMAL', 'PREFERENCES')
SETTIE_ROBOT = 'settie@a.gwave.com'

PREFERENCES_WAVEID_DATA_DOC = '%s/preferencesWaveId' % ROBOT_ADDRESS
PREFERENCES_VERSION_DATA_DOC = '%s/preferencesVersion' % ROBOT_ADDRESS
PREFERENCES_VERSION = '7'
PARTICIPANT_DATA_DOC = '%s/%s/notify' % (ROBOT_ADDRESS, '%s')


##########################################################
# Wave util

def get_wavelet(context):
    return context.GetRootWavelet()
    # TODO get actual wavelet for private replies
    #return context.GetWaveletById(event.properties['waveletId'])


def get_blip(event, context):
    return context.GetBlipById(event.properties['blipId'])


def get_form_element(form, element):
    for e in form:
        if form[e].type == document.ELEMENT_TYPE.CHECK:
            if form[e].value == None:
                logging.debug(2)
                form[e].value = form[e].name
                form[e].name = form[e].label
            if isinstance(form[e].value, basestring):
                form[e].value = form[e].value == 'true'
        if form[e].name == element:
            return form[e]


def get_url(participant, waveId):
    domain = participant.split('@')[1]
    if waveId and domain == 'googlewave.com':
        return 'https://wave.google.com/wave/#restored:wave:%s' % urllib.quote(waveId)
    if waveId:
        return 'https://wave.google.com/a/%s/#restored:wave:%s' % (urllib.quote(waveId), domain)
    else:
        return ''


##########################################################
# Wave State

def get_preferencesWaveId(context):
    wavelet = get_wavelet(context)
    if not wavelet: return
    data = wavelet.GetDataDocument(PREFERENCES_WAVEID_DATA_DOC)

    # FIXME TEMPORAL
    if not data:
        data = wavelet.GetDataDocument(ROBOT_ADDRESS)
        if data:
            wavelet.SetDataDocument(PREFERENCES_WAVEID_DATA_DOC, data)
    # END TEMPORAL

    logging.debug('filtering %s == "%s"' % (wavelet.waveId, data))
    if data and data.startswith('pending') or data == wavelet.waveId:
        return data

def set_preferencesWaveId(context, participant, wavelet):
    pp = get_pp(participant)
    preferencesWaveId = get_preferencesWaveId(context)
    if pp and pp.preferencesWaveId == preferencesWaveId:
        wavelet.SetDataDocument(PREFERENCES_WAVEID_DATA_DOC, wavelet.waveId)
        pp.preferencesWaveId = wavelet.waveId;
        pp.put()


def get_type(event, context):
    blip = get_blip(event, context)
    if bool(get_preferencesWaveId(context)):
        logging.debug('preferences wavelet')
        return WAVELET_TYPE.PREFERENCES
    else:
        logging.debug('normal wavelet')
        return WAVELET_TYPE.NORMAL


def participant_notifications_enabled(wavelet, participant):
    notify = False
    # TODO use wavelet.GetDataDocument(PARTICIPANT_DATA_DOC % participant)
    # if isinstance(notify, basestring): notify = notify == 'true'
    pwp = get_pwp(participant, wavelet.waveId)
    if pwp:
        notify = pwp.notify
    logging.debug('email %s [%s]? %s' % (participant, wavelet.waveId, notify))
    return notify


##########################################################
# Actions

def init_wave(event, context):
    wavelet = get_wavelet(context)
    # TODO ensure we get the root blip only
    blip = get_blip(event, context)
    gadget = blip.GetGadgetByUrl(GADGET_URL)
    if not gadget:
        doc = blip.GetDocument()
        gadget = document.Gadget(GADGET_URL)
        doc.InsertElement(0, gadget)
        doc.GadgetSubmitDelta(gadget, { "waveId": wavelet.waveId })


def notify_initial(context, wavelet, participants, modified_by, message):
    for participant in participants:
        if participant == ROBOT_ADDRESS: continue
        pwp = get_pwp(participant, wavelet.waveId)
        if not pwp:
            pp = get_pp(participant, create=True, context=context)
            send_notification(context, wavelet, participant, modified_by, message)


def notify(event, context, wavelet, modified_by, message):
    for participant in wavelet.participants:
        if participant == ROBOT_ADDRESS: continue
        if participant == modified_by: continue
        if participant_notifications_enabled(wavelet, participant):
            pp = get_pp(participant, create=True, context=context)
            send_notification(context, wavelet, participant, modified_by, message)


def send_notification(context, wavelet, participant, mail_from, message):
    if not message.strip(): return

    pp = get_pp(participant)
    if not pp.notify or not mail.is_email_valid(pp.email): return

    url = get_url(participant, wavelet.waveId)
    prefs_url = get_url(participant, pp.preferencesWaveId)
    subject = '[wave] %s' % wavelet.title
    body = MESSAGE_TEMPLATE % (message, url, prefs_url, wavelet.waveId, wavelet.waveletId)
    mail_from = '%s <%s>' % (mail_from.replace('@', ' at '), ROBOT_EMAIL)
    mail_to = pp.email

    logging.debug('adding task to send_email queue for %s => %s'
                  % (wavelet.waveId, mail_to))

    taskqueue.Task(url='/send_email',
                   params={ 'mail_from': mail_from,
                            'mail_to': mail_to,
                            'subject': subject,
                            'body': body }).add(queue_name='send-email')


##########################################################
# Preferences

def get_pp(participant, create=False, context=None):
    query = model.ParticipantPreferences.all()
    query.filter('participant =', participant)
    pp = query.get()

    if create and context and not pp:
        pp = create_pp(context, participant)
    elif context and create:
        create_pp_wave(context, pp)

    return pp


def get_pwp(participant, waveId, create=False):
    query = model.ParticipantWavePreferences.all()
    query.filter('participant =', participant)
    query.filter('waveId =', waveId)
    pwp = query.get()

    if not pwp and create:
        pwp = model.ParticipantWavePreferences(participant=participant,
                                               waveId=waveId)
        pwp.put()

    return pwp


def create_pp(context, participant):
    logging.debug('creating pp for %s' % participant)

    pp = model.ParticipantPreferences(participant=participant)

    if participant.endswith('appspot.com'):
        pp.notify = False;
        pp.email = None
    else:
        # FIXME This should be more generic
        pp.email = participant.replace('@googlewave.com', '@gmail.com')

    pp.put()
    create_pp_wave(context, pp)

    return pp


def create_pp_wave(context, pp):
    if pp.preferencesWaveId: return
    logging.debug('creating pp form for %s' % pp.participant)

    pp.preferencesWaveId = 'pending:%s' % uuid.uuid1()
    pp.put()

    wavelet = robot_abstract.NewWave(context, [ pp.participant, SETTIE_ROBOT ])
    update_pp_form(context, wavelet, pp)


def update_pp_form(context, wavelet, pp):
    if not wavelet.GetDataDocument(PREFERENCES_VERSION_DATA_DOC):
        wavelet.AddParticipant(SETTIE_ROBOT)

    if wavelet.GetDataDocument(PREFERENCES_VERSION_DATA_DOC) == PREFERENCES_VERSION: return

    rootblip = context.GetBlipById(wavelet.GetRootBlipId())

    doc = rootblip.GetDocument()
    doc.Clear()

    wavelet.SetTitle('Notifiy global preferences')
    wavelet.SetDataDocument(PREFERENCES_WAVEID_DATA_DOC, pp.preferencesWaveId)
    wavelet.SetDataDocument(PREFERENCES_VERSION_DATA_DOC, PREFERENCES_VERSION)

    doc.AppendText('\n')

    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'notify', pp.notify, pp.notify))
    doc.AppendText(' Notify me to this email:\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.INPUT, 'email', pp.email, pp.email))

    doc.AppendText('\n')

    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'notify_initial', True, True))
    doc.AppendText(' Send initial notifications [not yet modifiable]\n')

    doc.AppendText('\nNotification frequency [not yet modifiable]:\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.RADIO_BUTTON, 'frequency', True, True))
    doc.AppendText(' Send notifications for every change\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.RADIO_BUTTON, 'frequency', False, False))
    doc.AppendText(' Send 1 notification until I visit the wave\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.RADIO_BUTTON, 'frequency', False, False))
    doc.AppendText(' Do not send notifications\n')

    doc.AppendText('\n')

    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'save_pp', 'save', 'save'))

    doc.AppendText('\n\nExecute global commands:')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.INPUT, 'command', '', ''))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'exec_pp', 'exec', 'exec', 'exec'))
