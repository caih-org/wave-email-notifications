import logging
import urllib
import uuid

from google.appengine.api import mail
from google.appengine.api.labs import taskqueue

from waveapi import document
from waveapi import robot_abstract

import model

ROBOT_NAME = 'notifiy'
ROBOT_ID = 'wave-email-notifications'
ROBOT_ADDRESS = "%s@appspot.com" % ROBOT_ID
ROBOT_BASE_URL = 'http://%s.appspot.com' % (ROBOT_ID)
ROBOT_EMAIL = "wave-email-notifications@ecuarock.net"
ROBOT_HOME_PAGE = "http://wave-email-notifications.googlecode.com/"
GADGET_URL = '%s/%s.xml' % (ROBOT_BASE_URL, ROBOT_ID)

INITIAL_MESSAGE = 'To receive email notifications for this wave visit the '\
'following link and activate them.'

MESSAGE_TEMPLATE = '''\
%s

======
Visit this wave: %s
Change notification preferences: %s
[%s:%s]
'''


def get_blip(context, event):
    return context.GetBlipById(event.properties["blipId"])


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
    if waveId and domain == 'wavesandbox.com':
        return 'https://wave.google.com/a/wavesandbox.com/#restored:wave:%s' % urllib.quote(waveId)
    else:
        return 'invalid domain!!!'


def get_preferences_url(context, participant):
    return get_url(participant, get_preferencesWaveId(context))


def get_preferencesWaveId(context):
    wavelet = context.GetRootWavelet()
    if not wavelet: return
    data = wavelet.GetDataDocument(ROBOT_ADDRESS)
    logging.debug('filtering %s == "%s"' % (wavelet.waveId, data))
    if data and data.startswith('pending') or data == wavelet.waveId:
        return data


def is_preferences_wave(context):
    return bool(get_preferencesWaveId(context))


def init_wave(context, event):
    wavelet = context.GetRootWavelet()
    blip = get_blip(context, event)
    gadget = blip.GetGadgetByUrl(GADGET_URL)
    if not gadget:
        doc = blip.GetDocument()
        doc.InsertElement(0, document.Gadget(GADGET_URL))


def participant_notifications_enabled(context, event, participant):
    blip = get_blip(context, event)
    if blip:
        gadget = blip.GetGadgetByUrl(GADGET_URL)
        return gadget and gadget.get(participant + "_notify") == "true"


def notify_initial(context, wavelet, participants, modified_by, message):
    for participant in participants:
        if participant == ROBOT_ADDRESS: continue
        pp = get_pp(participant, create=True, context=context)
        send_notification(context, wavelet, participant, modified_by, message)


def notify(context, event, wavelet, modified_by, message):
    for participant in wavelet.participants:
        if participant == ROBOT_ADDRESS: continue
        if participant == modified_by: continue
        if participant_notifications_enabled(context, event, participant):
            pp = get_pp(participant, create=True, context=context)
            send_notification(context, wavelet, participant, modified_by, message)


def send_notification(context, wavelet, participant, mail_from, message):
    if not message.strip(): return

    pp = get_pp(participant)
    if not pp.notify or not mail.is_email_valid(pp.email): return

    url = get_url(participant, wavelet.waveId)
    prefs_url = get_preferences_url(context, participant)
    subject = '[wave] %s' % wavelet.title
    body = MESSAGE_TEMPLATE % (message, url, prefs_url, wavelet.waveId, wavelet.waveletId)
    mail_from = '%s <%s>' % (mail_from.replace('@', ' at '), ROBOT_EMAIL)
    mail_to = pp.email

    logging.debug('adding task to send_email queue for %s => %s'
                  % (wavelet.waveId, participant))

    taskqueue.Task(url='/send_email',
                   params={ 'mail_from': mail_from,
                            'mail_to': mail_to,
                            'subject': subject,
                            'body': body }).add(queue_name='send-email-send')


def get_pp(participant, create=False, context=None):
    query = model.ParticipantPreferences.all()
    query.filter('participant =', participant)
    pp = query.get()

    if create and not pp:
        pp = create_pp(context, participant)

    return pp


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

    wavelet = robot_abstract.NewWave(context, [ pp.participant ])
    wavelet.SetTitle('Notifiy global preferences')
    wavelet.SetDataDocument(ROBOT_ADDRESS, pp.preferencesWaveId)
    rootblip = context.GetBlipById(wavelet.GetRootBlipId())

    doc = rootblip.GetDocument()
    doc.AppendText('\n')

    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'notify', pp.notify, pp.notify))
    doc.AppendText(' Notify me to this email:\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.INPUT, 'email', pp.email, pp.email))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'save_pp', 'save', 'save'))

    doc.AppendText('\n\nExecute global commands:')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.INPUT, 'command', '', ''))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'exec_pp', 'exec', 'exec', 'exec'))
