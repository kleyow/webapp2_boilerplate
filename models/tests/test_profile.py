import unittest2

import pytz
from webapp2_extras import security

from library import constants, testing
from models.funding_source import FundingSource
from models.profile import Profile
from models.transaction import Transaction


class TestProfile(testing.TestCase, unittest2.TestCase):

  def test_profile_defaults(self):
    profile = Profile()
    profile.put()
    self.assertEqual(None, profile.auth_user_id)
    self.assertEqual(None, profile.timezone)
    self.assertEqual(False, profile.is_admin)
    self.assertEqual(0, profile.jmd_balance)
    self.assertEqual(0, profile.usd_balance)
    self.assertLength(0, profile.transactions_sent)
    self.assertLength(0, profile.transactions_received)
    self.assertLength(0, profile.organizations)
    self.assertEqual(False, profile.beta_tester)
    self.assertEqual(None, profile.pin)

  def test_default_timezone(self):
    profile = self.create_profile()

    # Ensure DEFAULT_TIMEZONE is returned if no timezone provided.
    profile.timezone = None
    profile.put()
    self.assertIsNotNone(profile.get_timezone())
    self.assertEqual(Profile.DEFAULT_TIMEZONE, str(profile.get_timezone()))

  def test_get_by_email(self):
    profile = self.create_profile(email='test@example.org')
    self.assertEqual(profile.key(),
                     Profile.get_by_email('test@example.org').key())

    self.create_profile(email='test2@example.org')
    self.assertEqual(profile.key(),
                     Profile.get_by_email('test@example.org').key())

  def test_get_by_email_doesnt_exist(self):
    self.assertEqual(None, Profile.get_by_email('not_exist@example.org'))

  def test_set_pin_changes_password_when_put_is_true(self):
    profile = self.create_profile()
    profile.set_pin('2345', put=True)
    self.assertNotEqual('2345', profile.pin)

  def test_set_pin_only_accepts_strings(self):
    profile = self.create_profile()
    self.assertRaises(TypeError, profile.set_pin, object())
    self.assertRaises(TypeError, profile.set_pin, 1234)

  def test_set_pin_dosent_change_password_when_put_is_false(self):
    profile = self.create_profile(pin='1234')
    profile.set_pin('2345', put=False)

    # Check to see if the pin has changed.
    self.assertTrue(security.check_password_hash('2345', profile.pin))

    # Reload the profile to see if the changed pin was saved.
    profile = Profile.get(profile.key())
    self.assertFalse(security.check_password_hash('2345', profile.pin))
    self.assertTrue(profile.check_pin('1234'))
    self.assertFalse(profile.check_pin('2222'))

  def test_check_pin(self):
    profile = self.create_profile(pin='1234')
    self.assertTrue(security.check_password_hash('1234', profile.pin))

  def test_get_by_auth_user_id(self):
    profile = self.create_profile()
    id = profile.auth_user_id
    self.assertEqual(profile.key(), Profile.get_by_auth_user_id(id).key())

  def test_get_by_auth_user_id_doesnt_exist(self):
    self.assertEqual(None, Profile.get_by_auth_user_id(44))

  def test_get_auth_user(self):
    profile = self.create_profile()
    self.assertEqual(profile.auth_user_id, profile.get_auth_user().key.id())

  def test_get_timezone_is_timezone_object(self):
    profile = self.create_profile()
    profile.timezone = None
    profile.put()
    self.assertNotIsInstance(profile.get_timezone(), basestring)
    self.assertIsInstance(profile.get_timezone(), pytz.tzinfo.BaseTzInfo)

  def test_get_current_time_is_localized(self):
    profile = self.create_profile()
    now = profile.get_current_time()
    self.assertIsNotNone(now.tzinfo)

  def test_get_short_name(self):
    profile = self.create_profile(name='First Last')
    self.assertEqual('First', profile.get_short_name())

    profile.name = None
    self.assertIsNone(profile.get_short_name())

    profile.name = ''
    self.assertIsNone(profile.get_short_name())

    profile.name = 'Single'
    self.assertEqual('Single', profile.get_short_name())

    profile.name = 'Extra-Long Name With Hyphens'
    self.assertEqual('Extra-Long', profile.get_short_name())

    profile.name = 'J.P. Morgan'
    self.assertEqual('J.P.', profile.get_short_name())

  def test_is_editable_by(self):
    profile = self.create_profile()

    # Can edit your own profile
    self.assertTrue(profile.is_editable_by(profile))

    admin = self.create_profile(is_admin=True)
    self.assertTrue(profile.is_editable_by(admin))

    peer = self.create_profile(is_admin=False)
    self.assertFalse(profile.is_editable_by(peer))

  def test_get_organization(self):
    profile = self.create_profile()
    self.assertIsNone(profile.get_organization())
    organization = self.create_organization(owner=profile)
    profile = Profile.get(profile.key())
    self.assertIsNotNone(profile.get_organization())
    self.assertEqual(organization.key(), profile.get_organization().key())

  def test_get_funding_sources(self):
    profile = self.create_profile()
    funding_source = self.create_funding_source(
        parent=profile, status=FundingSource.Status.Accepted)
    self.create_funding_source(
        parent=profile, status=FundingSource.Status.Rejected)
    self.assertLength(2, profile.get_funding_sources())
    self.assertLength(
        1, profile.get_funding_sources(status=FundingSource.Status.Accepted))
    self.assertLength(
        1, profile.get_funding_sources(status=FundingSource.Status.Rejected))
    self.assertLength(
        0, profile.get_funding_sources(status=FundingSource.Status.Pending))

    # Ensure all the funding sources belong to the profile.
    for funding_source in profile.get_funding_sources():
      self.assertEqual(profile.key(), funding_source.get_profile().key())

  def test_get_balance(self):
    profile = self.create_profile(usd_balance=3000, jmd_balance=4000)
    self.assertEqual(3000, profile.get_balance(constants.USD_CURRENCY))
    self.assertEqual(4000, profile.get_balance(constants.JMD_CURRENCY))

  def test_balance_edge_cases(self):
    profile = self.create_profile()
    self.assertRaises(ValueError, profile.get_balance, 'jimmy')

  def test_increment_balance_usd_no_put(self):
    profile = self.create_profile()
    self.assertEqual(0, profile.usd_balance)
    profile.increment_balance(constants.USD_CURRENCY, 2000)
    self.assertEqual(2000, profile.usd_balance)

    profile = Profile.get(profile.key())
    self.assertEqual(0, profile.jmd_balance)
    self.assertEqual(0, profile.usd_balance)

  def test_increment_balance_jmd_no_put(self):
    profile = self.create_profile()
    self.assertEqual(0, profile.jmd_balance)
    profile.increment_balance(constants.USD_CURRENCY, 2000)
    self.assertEqual(2000, profile.usd_balance)

    profile = Profile.get(profile.key())
    self.assertEqual(0, profile.jmd_balance)
    self.assertEqual(0, profile.usd_balance)

  def test_increment_balance_put(self):
    profile = self.create_profile()
    self.assertEqual(0, profile.jmd_balance)
    self.assertEqual(0, profile.usd_balance)
    profile.increment_balance(constants.JMD_CURRENCY, 2000, put=True)

    profile = Profile.get(profile.key())
    self.assertEqual(2000, profile.jmd_balance)
    self.assertEqual(0, profile.usd_balance)

  def test_increment_balance_edge_cases(self):
    profile = self.create_profile()
    self.assertEqual(0, profile.jmd_balance)
    self.assertEqual(0, profile.usd_balance)
    self.assertRaises(ValueError, profile.increment_balance, 'jimmy', 2000)

    # Ensure both balances are unchanged.
    self.assertEqual(0, profile.jmd_balance)
    self.assertEqual(0, profile.usd_balance)

  def test_get_admin_deposits(self):
    admin_profile = self.create_profile(is_admin=True)
    self.assertLength(0, admin_profile.get_admin_deposits())
    profile = self.create_profile()
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit, sender=admin_profile)
    self.assertIsNone(profile.get_admin_deposits())
    self.assertLength(1, admin_profile.get_admin_deposits())
    self.assertEqual(transaction.key(),
                     admin_profile.get_admin_deposits().get().key())
