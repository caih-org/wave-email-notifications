#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

import logging
import urllib

from google.appengine.ext import webapp

from . import model


class IPhone(webapp.RequestHandler):

    def get(self):
        self.response.contentType = 'text/plain'

        path = [urllib.unquote(a) for a in self.request.path.split('/')[2:]]

        if len(path) == 4:
            participant = path[0]
            activation = path[1]
            phone_uid = path[2]
            phone_token = path[3].replace('+', ' ')

            logging.debug("ACTIVATING");
            logging.debug("participant: %s" % participant)
            logging.debug("activation: %s" % activation)
            logging.debug("iPhone uid: %s" % phone_uid)
            logging.debug("iPhone token: %s" % phone_token)

            query = model.ParticipantPreferences.all()
            query.filter("participant =", participant);
            query.filter("activation =", activation);
            pp = query.get()

            if pp:
                pp.phone_uid = phone_uid
                pp.phone_token = phone_token
                pp.put()
                self.response.out.write('OK')
            else:
                self.response.out.write('INVALID')

        else:
            phone_uid = path[0]
            phone_token = path[1].replace('+', ' ')
            action = path[2]

            logging.debug("ACTION: %s" % action);
            logging.debug("iPhone uid: %s" % phone_uid)
            logging.debug("iPhone token: %s" % phone_token)

            query = model.ParticipantPreferences.all()
            query.filter("phone_uid =", phone_uid);
            query.filter("phone_token =", phone_token);

            for pp in query:
                pp.phone_uid = None
                pp.phone_token = None
                pp.put()

            self.response.out.write('OK')
