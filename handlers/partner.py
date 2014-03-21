import logging

from google.appengine.api import mail
from google.appengine.ext import deferred

from forms.partner import PartnerForm
from handlers import base
from library import constants
from library.auth import login_not_required


class PartnerHandler(base.BaseHandler):

  @login_not_required
  def send_partner_request(self):
    if self.request.method == 'POST':
      form = PartnerForm(self.request.POST)
      if form.validate():
        deferred.defer(send_contact_message,
                       owner_name=form.owner_name.data,
                       organization_name=form.organization_name.data,
                       address=form.address.data,
                       email=form.email.data,
                       phone_number=form.phone_number.data)
        self.session.add_flash(value='Thanks! Your message has been sent!')
      else:
        self.session.add_flash(value='Your message was unable to be sent!')
        logging.error('Error sending partner request: {request}.'
                      .format(request=self.request.POST))

      return self.redirect_to('partner')
    else:
      return self.render_to_response('partner.haml')


def send_contact_message(owner_name, organization_name, address, email,
                         phone_number):
  subject = 'Partner request from %s' % owner_name

  body = ('Partner request from %(owner_name)s (%(email)s)\n'
          'Organization Name: %(organization_name)s\n'
          'Address: %(address)s\n'
          'Email: %(email)s\n'
          'Contact Number: %(phone_number)s\n') % locals()

  mail.send_mail(sender=constants.NO_REPLY_EMAIL, subject=subject,
                 to=constants.CONTACT_EMAIL, body=body)
