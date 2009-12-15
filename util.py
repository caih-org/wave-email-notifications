import base64
import logging
import md5
import random
import re
import urllib
import urllib2
import uuid

from google.appengine.api import mail
from google.appengine.api.labs import taskqueue

from waveapi import document
from waveapi import robot_abstract
from waveapi import util

import model

ME = 'cesar.izurieta@googlewave.com'

ROBOT_NAME = 'notifiy'
ROBOT_ID = 'wave-email-notifications'
ROBOT_ADDRESS = '%s@appspot.com' % ROBOT_ID
ROBOT_BASE_URL = 'http://%s.appspot.com' % ROBOT_ID
ROBOT_EMAIL = '%s@ecuarock.net' % ROBOT_ID
ROBOT_HOME_PAGE = 'http://%s.googlecode.com/' % ROBOT_ID

GADGET_URL = '%s/%s.xml' % (ROBOT_BASE_URL, ROBOT_ID)

INITIAL_MESSAGE = u'To receive email notifications visit this wave and activate them.'
ADDED_MESSAGE = u'%s added you as a participant to this wave.'
CHANGES_MESSAGE = u'There are updates to this wave.'
MESSAGE_TEMPLATE = u'''\
%s

---
Visit this wave: %s
Change global notification preferences: %s
To unsubscribe please visit your preferences or send an email to: %s
'''
CONTENT_DELETED = u'*** Some content was deleted from the wave ***'
CONTENT_SUPRESSED = u'%s... [some content was supressed from this email]'
COMMANDS_HELP = u'''
help: Show this help
refresh: Recreate the preferences wave
reset: Reset your specific wave preferenes (for all waves) and refresh this form.
'''
COMMAND_SUCCESSFUL = u'Command %s ran successfully'
COMMAND_UNKNOWN = u'Command %s not found'
PREFERENCES_SAVED = u'Preferences saved'
ERROR_TRY_AGAIN = u'There was an error, please try again in a few moments'
UNSUBSCRIBED_SUBJECT = u'Unsubscribed'
UNSUBSCRIBED = u'Your email has been unsubscribed from the Notifiy robot. To receive notifications again please visit google wae and update your preferences. Your email may still show there, just click the refresh button.'

WAVELET_TYPE = util.StringEnum('NORMAL', 'PREFERENCES')
SETTIE_ROBOT = 'settie@a.gwave.com'

PREFERENCES_WAVEID_DATA_DOC = '%s/preferencesWaveId' % ROBOT_ADDRESS
PREFERENCES_VERSION_DATA_DOC = '%s/preferencesVersion' % ROBOT_ADDRESS
PREFERENCES_VERSION = '10'
PARTICIPANT_DATA_DOC = '%s/%s/notify' % (ROBOT_ADDRESS, '%s')


##########################################################
# General utils

def modified_b64encode(s):
    return base64.urlsafe_b64encode(s).replace('=', '')

def modified_b64decode(s):
    while len(s) % 4 != 0:
        s = s + '='
    return base64.urlsafe_b64decode(s)


##########################################################
# Wave utils

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
                form[e].value = form[e].name
                form[e].name = form[e].label
            if isinstance(form[e].value, basestring):
                form[e].value = form[e].value == 'true'
        if form[e].name == element:
            return form[e]


def get_url(participant, waveId):
    domain = participant.split('@')[1]
    encodedWaveId = urllib.quote(urllib.quote(waveId))
    if waveId and waveId.startswith('pending'):
        return 'Please search for it at Google Wave\'s settings section.'
    elif waveId and domain == 'googlewave.com':
        return 'https://wave.google.com/wave/#restored:wave:%s' % encodedWaveId
    elif waveId:
        return 'https://wave.google.com/a/%s/#restored:wave:%s' % (encodedWaveId, domain)
    else:
        return ''

def get_remove_url(email):
    return 'remove-%s@%s.appspotmail.com' % (modified_b64encode(email), ROBOT_ID)


def reply_wavelet(wavelet, message):
    doc = wavelet.CreateBlip().GetDocument()
    doc.SetText(message)


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
            wavelet.SetDataDocument(ROBOT_ADDRESS, None)
            wavelet.SetDataDocument(PREFERENCES_WAVEID_DATA_DOC, data)
    # END TEMPORAL

    logging.debug('filtering %s == %s' % (wavelet.waveId, data))
    if data and data.startswith('pending') or data == wavelet.waveId:
        return data


def set_preferencesWaveId(context, participant, wavelet):
    pp = get_pp(participant, create=True, context=context)
    preferencesWaveId = get_preferencesWaveId(context)
    if preferencesWaveId:
        wavelet.SetDataDocument(PREFERENCES_WAVEID_DATA_DOC, wavelet.waveId)
        pp.preferencesWaveId = wavelet.waveId
        pp.put()


def get_type(event, context):
    blip = get_blip(event, context)
    if bool(get_preferencesWaveId(context)):
        logging.debug('preferences wavelet')
        return WAVELET_TYPE.PREFERENCES
    else:
        logging.debug('normal wavelet')
        return WAVELET_TYPE.NORMAL


def get_notify_type(wavelet, participant):
    notify_type = model.NOTIFY_NONE
    pwp = get_pwp(participant, wavelet.waveId)

    if pwp:
        notify_type = pwp.notify_type
        if pwp.notify_type == model.NOTIFY_ONCE:
            if pwp.visited:
                pwp.visited = False
                pwp.put()
            else:
                notify_type = model.NOTIFY_NONE

    return notify_type


def get_notify_initial(context, participants):
    return (not 'public@a.gwave.com' in participants
             and (not 'proxyingFor' in context.extradata
                  or context.extradata['proxyingFor'] != 'no-initial'))

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


def notify_initial(context, wavelet, participants, modified_by, message):
    for participant in participants:
        if participant == ROBOT_ADDRESS: continue
        pwp = get_pwp(participant, wavelet.waveId)
        if not pwp:
            pp = get_pp(participant, create=True, context=context)
            if pp.notify_initial:
                send_notification(context, wavelet, participant, modified_by, message)


def notify(event, context, wavelet, modified_by, message):
    for participant in wavelet.participants:
        if participant == ROBOT_ADDRESS: continue
        if participant == modified_by: continue
        notify_type = get_notify_type(wavelet, participant)
        if notify_type == model.NOTIFY_ONCE:
            send_notification(context, wavelet, participant, modified_by, CHANGES_MESSAGE)
        elif notify_type == model.NOTIFY_ALL:
            send_notification(context, wavelet, participant, modified_by, message)


def send_notification(context, wavelet, participant, mail_from, message):
    if not message.strip(): return

    pp = get_pp(participant, create=True, context=context)

    if pp.phone_uid:
        try:
            url = model.ApplicationSettings.get('remote-server') % (
                urllib.quote(pp.phone_uid),
                urllib.quote(pp.phone_token),
                urllib.quote(wavelet.title),
                urllib.quote(mail_from))
            logging.warn(url);
            urllib2.urlopen(url)
            logging.info('success calling remote notification server')
        except urllib2.URLError, e:
            logging.warn('error calling remote notification server: %s' % e)

    if not pp.notify or not mail.is_email_valid(pp.email): return

    url = get_url(participant, wavelet.waveId)
    prefs_url = get_url(participant, pp.preferencesWaveId)
    remove_url = get_remove_url(pp.email)
    subject = '[wave] %s' % wavelet.title
    body = MESSAGE_TEMPLATE % (message, url, prefs_url, remove_url)
    mail_from = '%s <%s>' % (mail_from.replace('@', ' at '), ROBOT_EMAIL)
    mail_to = pp.email
    m = md5.new()
    m.update(subject.encode("UTF-8"))
    m.update(message.encode("UTF-8"))
    text_hash = m.hexdigest()
    name = '%s-%s-%s' % (wavelet.waveId, mail_to, text_hash)
    name =  re.compile('[^a-zA-Z0-9-]').sub('X', name)

    if len(body) > 9000:
        body = CONTENT_SUPRESSED % body[0:9000]

    logging.debug('adding task to send_email queue for %s => %s' % (name, mail_to))

    try:
        taskqueue.Task(url='/send_email', name=name,
                       params={ 'mail_from': mail_from,
                                'mail_to': mail_to,
                                'subject': subject,
                                'waveId': wavelet.waveId,
                                'waveletId': wavelet.waveletId,
                                'body': body }).add(queue_name='send-email')
    except taskqueue.TombstonedTaskError, e:
        logging.warn("Task with same name already added, droping duplicated message")
    except taskqueue.TaskAlreadyExistsError, e:
        logging.warn("Task with same name already added, droping duplicated message")


##########################################################
# Preferences

def get_pp(participant, create=False, context=None):
    query = model.ParticipantPreferences.all()
    query.filter('participant =', participant)
    pp = query.get()

    if create and context:
        if not pp:
            pp = create_pp(context, participant)
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
        pp.notify = False
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


def update_pp_form(context, wavelet, pp, ignore=False):
    if not wavelet.GetDataDocument(PREFERENCES_VERSION_DATA_DOC):
        wavelet.AddParticipant(SETTIE_ROBOT)

    if not ignore and wavelet.GetDataDocument(PREFERENCES_VERSION_DATA_DOC) == PREFERENCES_VERSION: return

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

    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.CHECK, 'notify_initial', pp.notify_initial, pp.notify_initial))
    doc.AppendText(' Send initial notifications\n')
    doc.AppendText('\n')

    doc.AppendText('iPhone activation code: %s\n' % pp.activation)
    doc.AppendText('\n')

    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'save_pp', 'save', 'save'))
    doc.AppendText(' ')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'refresh_pp', 'refresh', 'refresh'))

    doc.AppendText('\n\nExecute global commands: (try "help")')
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.INPUT, 'command', '', ''))
    doc.AppendElement(document.FormElement(document.ELEMENT_TYPE.BUTTON, 'exec_pp', 'exec', 'exec', 'exec'))

