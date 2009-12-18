#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from notifiy.home import Home
from notifiy.proc import Process
from notifiy.iphone import IPhone
from notifiy.send_email import SendEmail
from notifiy.receive_email import ReceiveEmail


if __name__ == "__main__":
  run_wsgi_app(webapp.WSGIApplication([('/', Home),
                                       ('/proc/.*', Process),
                                       ('/iphone/.*', IPhone),
                                       ('/send_email', SendEmail),
                                       ('/_ah/mail/.+', ReceiveEmail),]))
