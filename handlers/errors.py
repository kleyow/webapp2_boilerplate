import logging

from google.appengine.api import mail
from google.appengine.ext import deferred
import webapp2

from forms.error_report import ErrorReportForm
from handlers import base
from library import constants
from library.auth import login_not_required


class Webapp2HandlerAdapter(webapp2.BaseHandlerAdapter):
  """Ovewrites the call method in the BaseHandlerAdapter.

  Make the call method in the BaseHandlerAdapter look here
  for instructions on how to deal with exceptions."""

  def __call__(self, request, response, exception):
    request.route = webapp2.Route('.+', self.handler, handler_method='get')
    request.route_args = ()
    request.route_kwargs = {'exception': exception}
    return self.handler(request, response).dispatch()


class Handle404(base.BaseHandler):

  @login_not_required
  def get(self, exception):
    self.response.status_int = 404
    return self.render_to_response('404.haml', use_cache=True)


class Handle500(base.BaseHandler):

  @login_not_required
  def get(self, exception):
    # Prevent data from bad POST requests from being passed to the
    # form.
    if (self.request.method == 'POST' and
            self.request.referrer == self.uri_for('error.report')):
      form = ErrorReportForm(self.request.POST)

      if form.validate():
        deferred.defer(send_error_report, **form.data)
        self.session.add_flash('Thank you. Your report has been received.',
                               level='success')
        return self.redirect_to('home')

      else:
        logging.error('Error sending error report: %s' % self.request.POST)
        last_error = form.errors.values().pop()
        self.session.add_flash(last_error[0], level='error')

    # Log the exception that caused this 500 error.
    if exception:
      logging.exception(exception)

    self.response.status_int = 500
    return self.render_to_response('500.haml', use_cache=True)


def send_error_report(name, email, message):
  subject = 'Error report from %s' % name
  body = ('Error report from {name} ({email}).\n'
          '{message}'.format(name=name, email=email, message=message))
  mail.send_mail(sender=constants.NO_REPLY_EMAIL, subject=subject,
                 to=constants.SUPPORT_EMAIL, body=body)
