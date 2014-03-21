import datetime

import unittest2

from library import testing
from models.funding_source import FundingSource


class FundingSourceTestCase(testing.TestCase, unittest2.TestCase):

  def test_default_values(self):
    funding_source = FundingSource()
    self.assertEqual(None, funding_source.card_token)
    self.assertEqual(None, funding_source.customer_id)
    self.assertEqual(None, funding_source.nickname)
    self.assertEqual(None, funding_source.last_four_digits)
    self.assertEqual(None, funding_source.exp_month)
    self.assertEqual(None, funding_source.exp_year)
    self.assertEqual(False, funding_source.is_expired)
    self.assertEqual(False, funding_source.is_verified)
    self.assertEqual(FundingSource.Status.Pending, funding_source.status)

  def test_get_by_customer_id(self):
    funding_source = FundingSource(parent=self.create_profile(),
                                   customer_id='test-customer-id')
    funding_source.put()

    retrieved = FundingSource.get_by_customer_id('test-customer-id')
    self.assertEqual(funding_source.key(), retrieved.key())

  def test_get_by_customer_id_edge_cases(self):
    FundingSource(parent=self.create_profile(),
                  customer_id='test-customer-id').put()

    edge_values = [None, '', '  ', 'invalid']
    for edge_value in edge_values:
      self.assertEqual(
          None, FundingSource.get_by_customer_id(edge_value),
          'Expected None for FundingSource.get_by_customer_id(%r).' %
          edge_value)

  def test_get_expiration_date(self):
    funding_source = FundingSource(parent=self.create_profile(),
                                   exp_year='2015', exp_month='05')
    funding_source.put()
    self.assertEqual(datetime.date(year=2015, month=5, day=31),
                     funding_source.get_expiration_date())

  def test_get_expiration_date_edge_cases(self):
    funding_source = FundingSource(parent=self.create_profile())
    funding_source.put()

    edge_values = [(None, '2015'), ('1', None), (None, None)]
    for exp_month, exp_year in edge_values:
      funding_source.exp_month = exp_month
      funding_source.exp_year = exp_year
      self.assertEqual(
          None, funding_source.get_expiration_date(),
          'Expected None for get_expiration_date with month %r and year %r' % (
              exp_month, exp_year))

  def test_is_editable_by(self):
    profile = self.create_profile()
    funding_source = FundingSource(parent=profile)
    funding_source.put()
    self.assertTrue(funding_source.is_editable_by(profile))

    admin = self.create_profile(is_admin=True)
    self.assertTrue(funding_source.is_editable_by(admin))

    peer = self.create_profile()
    self.assertFalse(funding_source.is_editable_by(peer))

    self.assertFalse(funding_source.is_editable_by(None))

  def test_compute_derived_fields_updates_is_expired(self):
    funding_source = FundingSource(parent=self.create_profile())
    funding_source.put()

    self.assertFalse(funding_source.is_expired)
    funding_source.exp_month = '5'
    funding_source.exp_year = str(datetime.date.today().year - 1)
    funding_source.compute_derived_fields()
    self.assertTrue(funding_source.is_expired)

    funding_source.exp_year = str(datetime.date.today().year + 1)
    funding_source.compute_derived_fields()
    self.assertFalse(funding_source.is_expired)

  def test_put_without_parent_raises_error(self):
    funding_source = FundingSource()
    with self.assertRaises(RuntimeError):
      funding_source.put()

    self.assertLength(0, FundingSource.all())

    funding_source = FundingSource(parent=self.create_profile())
    funding_source.put()
    self.assertLength(1, FundingSource.all())

  def test_get_profile(self):
    profile = self.create_profile()
    funding_source = FundingSource(parent=profile)
    funding_source.put()
    self.assertEqual(profile.key(), funding_source.get_profile().key())
