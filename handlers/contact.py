import logging

from google.appengine.api import mail
from google.appengine.ext import deferred

from forms.contact import ContactForm
from handlers import base
from library import constants
from library.auth import login_not_required


class ContactHandler(base.BaseHandler):

  @login_not_required
  def contact(self):

    if self.request.method == 'POST':
      form = ContactForm(self.request.POST)
      if form.validate():
        deferred.defer(send_contact_message,
                       name=form.name.data,
                       email=form.email.data,
                       topic=form.topic.data,
                       message=form.message.data)
        self.session.add_flash(value='Thanks! Your message has been sent!')
      else:
        self.session.add_flash(value='Your message was unable to be sent!')
        logging.error('Error sending contact request: ' +
                      str(self.request.POST))
      return self.redirect_to('contact')
    else:
      return self.render_to_response('contact.haml')


def send_contact_message(name, email, topic, message):
  subject = 'Question from %s' % name
  if topic:
    subject += ' about %s' % topic

  body = ('Question from %(name)s (%(email)s)\n'
          'Topic was: %(topic)s\n'
          'Message was:\n\n'
          '%(message)s\n') % locals()

  mail.send_mail(sender='%s' % constants.NO_REPLY_EMAIL, subject=subject,
                 to='%s' % constants.SUPPORT_EMAIL, body=body)
