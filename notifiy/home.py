#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

from google.appengine.ext import webapp


class Home(webapp.RequestHandler):
    def get(self):
        self.redirect("http://wave-email-notifications.googlecode.com/")
