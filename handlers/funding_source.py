import logging

from google.appengine.api import taskqueue
from google.appengine.ext import db
import stripe

from forms.funding_source import FundingSourceForm
from handlers import base
from library import locking
from library.auth import login_not_required
from library.stripe_helpers import stripe_connection
from models.funding_source import FundingSource


class FundingSourceHandler(base.BaseHandler):

  def create(self):
    profile = self.get_current_profile()
    form = FundingSourceForm(self.request.POST)

    if form.validate():
      funding_source = FundingSource(parent=profile)
      funding_source.card_token = form.data['card_token']
      funding_source.last_four_digits = form.data['card_last_four_digits']
      funding_source.exp_month = form.data['card_exp_month']
      funding_source.exp_year = form.data['card_exp_year']
      funding_source.nickname = form.data['nickname']
      funding_source.put()

      # Kick off a task to create a stripe Customer for this funding source.
      taskqueue.add(url=self.uri_for('funding_source.create_stripe_customer'),
                    queue_name='payment', target='mail',
                    params={'funding_source': funding_source.key()})

    else:
      raise Exception(form.errors)

    return self.redirect_to('profile.view')

  def delete(self):
    profile = self.get_current_profile()
    funding_source_key = self.request.POST.get('funding_source')

    try:
      funding_source = FundingSource.get(funding_source_key)

    except db.BadKeyError:
      funding_source = None

    if not funding_source:
      error = ('Bad funding source key: "{funding_source_key} given '
               'by {profile.email} ({profile_key}).'
               .format(funding_source_key=funding_source_key,
                       profile=profile, profile_key=profile.key()))

    elif funding_source.get_profile().key() != profile.key():
      error = ('{profile.email} ({profile_key}) attempted to delete a funding '
               'source not belonging to them "{funding_source_key}".'
               .format(
                   profile=profile, profile_key=profile.key(),
                   funding_source_key=funding_source_key))

    else:
      error = None

    if error:
      logging.error(error)
      return self.abort(404)

    # Add a task to the queue to delete the funding source.
    taskqueue.add(url=self.uri_for('funding_source.delete_stripe_customer'),
                  queue_name='payment', target='mail',
                  params={'customer_id': funding_source.customer_id})

    # Delete the funding source and redirect the user.
    funding_source.delete()
    return self.redirect_back(default=self.uri_for('profile.view'))

  @login_not_required
  def create_stripe_customer(self):
    if not self.is_taskqueue_request():
      logging.error('Attempted to add funding source outside of task queue.')
      return

    funding_source_key = self.request.POST.get('funding_source')

    try:
      funding_source = FundingSource.get(funding_source_key)

    except db.BadKeyError:
      funding_source = None

    if not funding_source:
      logging.error('Invalid funding source {funding_source_key}.'
                    .format(funding_source_key=funding_source_key))
      return

    # Ensure that only pending funding sources can be processed.
    if funding_source.status != FundingSource.Status.Pending:
      logging.error('Attempt to re-process {funding_source.status} funding '
                    'source, {funding_source_key} detected.'
                    .format(funding_source=funding_source,
                            funding_source_key=funding_source_key))
      return

    profile = funding_source.get_profile()

    # Create the customer in Stripe.
    stripe.api_key = self.get_stripe_api_key()

    try:
      customer = stripe.Customer.create(
          email=profile.email,
          card=funding_source.card_token,
          description='%s: -%s' % (profile.email,
                                   funding_source.last_four_digits))

    except stripe.CardError:
      logging.exception('{profile.email} ({profile_key}) attempted to add an '
                        'invalid credit card.'
                        .format(profile=profile,
                                profile_key=str(profile.key())))
      funding_source.status = FundingSource.Status.Rejected
      funding_source.put()
      return

    funding_source.customer_id = customer.id
    funding_source.status = FundingSource.Status.Accepted
    funding_source.put()
    return

  @login_not_required
  def delete_stripe_customer(self):
    if not self.is_taskqueue_request():
      logging.error(
          'Attempted to delete stripe customer outside of task queue.')
      return

    customer_id = self.request.POST.get('customer_id', '')

    # Lock customer_id to prevent any race conditions.
    with locking.lock(customer_id):
      # Retrieve the stripe.Customer object associated with this funding source
      # and delete it, if it exists.
      with stripe_connection(
              stripe.Customer.retrieve, customer_id) as customer:
        if not customer:
          logging.error(
              'Customer with id: "{customer_id}" not found.'
              .format(customer_id=customer_id))
          return

        with stripe_connection(customer.delete) as customer:
          if customer:
            logging.debug('Successfully deleted stripe customer: '
                          '"{customer_id}"'
                          .format(customer_id=customer_id))

          else:
            logging.error('Error deleting stripe customer: "{customer_id}"'
                          .format(customer_id=customer_id))
