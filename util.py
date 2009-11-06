import logging
import urllib
import uuid

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

INITIAL_MESSAGE = 'To receive email notifications for this wave visit the \
preferences at the following link and activate them.'

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


def get_preferences_url(participant, waveId, action=''):
    return '%s/prefs/%s/%s/%s' % (ROBOT_BASE_URL, urllib.quote(participant),
                                  waveId, action)


def get_pp(participant, create=False, context=None):
    query = model.ParticipantPreferences.all()
    query.filter('participant =', participant)
    pp = query.get()

    if create and not pp:
        pp = create_pp(context, participant)

    if context and pp:
        create_pp_form(context, pp)

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
    create_pp_form(context, pp)

    return pp


def create_pp_form(context, pp):
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


def get_pwp(participant, waveId, create=False, context=None, wavelet=None,
            modified_by=None, message=None):
    query = model.ParticipantWavePreferences.all()
    query.filter('participant =', participant)
    query.filter('waveId =', waveId)
    pwp = query.get()

    if create and not pwp:
        create_pwp(context, participant, waveId, modified_by=modified_by,
                   message=message)

    return pwp


def create_pwp(context, participant, waveId, modified_by=None, message=None):
    logging.debug('creating pwp for %s' % participant)

    wavelet = context.GetRootWavelet()

    pwp = model.ParticipantWavePreferences(participant=participant, waveId=waveId)
    pwp.put()

    if message:
        send_notification(wavelet, participant, modified_by, message, ignore=True)

    if participant != 'cesar.izurieta@googlewave.com': return
    create_pwp_form(context, pwp);

    return pwp


def create_pwp_form(context, pwp):
    logging.debug('creating pwp form for %s at ' % (pwp.participant, pwp.waveId))

    new_wavelet = context.GetWaveById(pwp.waveId).CreateWavelet([ pwp.participant ])
    new_wavelet.SetTitle('Notifiy preferences')
    rootblip = context.GetBlipById(new_wavelet.GetRootBlipId())

    doc = rootblip.GetDocument()
    doc.AppendText('\n')

    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'notify', pwp.notify, pwp.notify))
    doc.AppendText(' Notify me about updates to this wave\n')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'save_pwp', 'save', 'save', 'save'))

    doc.AppendText('\n\nExecute commands:')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.INPUT, 'command', '', ''))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'exec_pwp', 'exec', 'exec', 'exec'))


def notify_initial(context, wavelet, participants, modified_by, message):
    for participant in participants:
        if participant == ROBOT_ADDRESS: continue

        url = get_preferences_url(participant, wavelet.waveId, 'enable')
        m = '%s\n\n%s' % (message, url)

        pp = get_pp(participant, create=True, context=context)
        pwp = get_pwp(participant, wavelet.waveId, create=True, context=context,
                      wavelet=wavelet, modified_by=modified_by, message=m)


def notify(context, wavelet, modified_by, message):
    for participant in wavelet.participants:
        if participant != ROBOT_ADDRESS and participant != modified_by:
            pp = get_pp(participant, create=True, context=context)
            pwp = get_pwp(participant, wavelet.waveId, create=True, context=context,
                          wavelet=wavelet, modified_by=modified_by, message=None)
            send_notification(wavelet, participant, modified_by, message)


def send_notification(wavelet, participant, mail_from, message, ignore=False):
    if not message.strip(): return

    logging.debug('adding task to send_email_prepare queue for %s => %s'
                  % (wavelet.waveId, participant))

    taskqueue.Task(url='/send_email/prepare',
                   params={ 'title': wavelet.title,
                            'waveId': wavelet.waveId,
                            'waveletId': wavelet.waveletId,
                            'participant': participant,
                            'mail_from': mail_from,
                            'message': message,
                            'ignore': ignore }).add(queue_name='send-email-prepare')
