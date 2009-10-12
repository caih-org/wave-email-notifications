from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app


class Home(webapp.RequestHandler):
    def get(self):
        self.redirect("http://wave-email-notifications.googlecode.com/")


if __name__ == "__main__":
  run_wsgi_app(webapp.WSGIApplication([('/', Home)]))
