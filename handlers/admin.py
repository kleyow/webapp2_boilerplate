from google.appengine.api import taskqueue

from forms.add_organization import AddOrganizationForm
from forms import error_messages
from forms.transfer import TransferForm
from handlers import base
from library import constants
from models.organization import Organization
from models.staff import Staff
from models.transaction import Transaction


class AdminHandler(base.BaseAdminHandler):

  def add_organization(self):
    if self.request.method == 'POST':
      form = AddOrganizationForm(self.request.POST)

      if form.validate():
        organization = Organization()
        form.populate_obj(organization)
        organization.identifier = form.data['identifier'].lower()

        if not organization.fee_percentage:
          organization.fee_percentage = constants.DEFAULT_FEE_PERCENTAGE

        # TODO: This implementation is vulnerable to race conditions, but
        # fixing them would require using the task queue.
        # Since we're not yet at the scale where a race condition of this
        # nature is likely, this is fine for now, but this should be modified
        # to use the task queue in the future.
        if Organization.get_by_identifier(organization.identifier):
          self.session.add_flash(value=error_messages.ADMIN_IDENTIFIER_IN_USE,
                                 level='error')
          return self.render_to_response('admin/add_organization.haml')

        organization.is_verified = True
        organization.put()

        # Add an Admin models.staff.Staff to the organization.
        admin_username = organization.owner.get_short_name().lower()
        password = '%s@%s' % (admin_username, organization.identifier)
        admin = Staff(parent=organization, name=organization.owner.name,
                      username=admin_username, role=Staff.Role.Admin,
                      is_active=True)

        # TODO: Send them a welcome email.
        admin.set_password(password, put=True)

        self.session.add_flash('Organization, {organization.name} added to '
                               '{organization.owner.email}.'
                               .format(organization=organization))
        return self.redirect_to('admin.add_organization')

      else:
        last_error = form.errors.values().pop()
        self.session.add_flash(last_error[0], level='error')

    return self.render_to_response('admin/add_organization.haml')

  def deposit(self):
    if self.request.method == 'POST':
      form = TransferForm(self.request.POST)

      if form.validate():
        current_profile = self.get_current_profile()
        if current_profile.key() == form.data['recipient'].key():
          error = error_messages.SENDER_IS_RECIPIENT
        else:
          error = None

        if error:
          self.session.add_flash(value=error, level='error')
          return self.redirect_to('admin.deposit')

        transaction = Transaction()
        form.populate_obj(transaction)
        transaction.transaction_type = Transaction.Type.Deposit
        transaction.sender = self.get_current_profile()
        transaction.put()

        # Add the transaction to the queue for processing later.
        taskqueue.add(url=self.uri_for('transaction.process'),
                      queue_name='payment', target='transactions',
                      params={'transaction_key': str(transaction.key())})

        message = '%s successfully topped up!' % transaction.recipient.email
        self.session.add_flash(value=message, level='success')
        return self.redirect_to('admin.deposit')

      last_error = form.errors.values().pop()
      self.session.add_flash(value=last_error[0], level='error')

    return self.render_to_response('admin/deposit.haml')

  def history(self):
    # Get a history of all cash deposits originating from the current profile.
    current_profile = self.get_current_profile()
    cash_deposits = current_profile.get_admin_deposits()
    usd_total = 0
    jmd_total = 0

    # Get the total amount of cash (USD and JMD) deposited by the current
    # profile.
    for cash_deposit in cash_deposits:
      if cash_deposit.currency == constants.JMD_CURRENCY:
        jmd_total += cash_deposit.amount

      else:
        usd_total += cash_deposit.amount

    return self.render_to_response(
        'admin/history.haml',
        {'transactions': cash_deposits, 'usd_total': usd_total,
         'jmd_total': jmd_total})
