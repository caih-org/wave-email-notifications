#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app


class Index(webapp.RequestHandler):

    def get(self):
        self.redirect('%s/index.html' % self.request.path)


if __name__ == "__main__":
    run_wsgi_app(webapp.WSGIApplication([ ('.*', Index), ]))

