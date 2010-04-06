#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from google.appengine.ext import webapp

from notifiy import constants


class Home(webapp.RequestHandler):
    def get(self):
        self.redirect(constants.ROBOT_HOME_PAGE)
