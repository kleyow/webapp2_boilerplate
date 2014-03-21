import unittest2

from library import constants
from library import testing


class TestLibraryConstants(testing.TestCase, unittest2.TestCase):

  def test_public_domain(self):
    self.assertEqual('blaze-pay.com', constants.PUBLIC_DOMAIN)

  def test_public_host(self):
    self.assertEqual('http://www.blaze-pay.com', constants.PUBLIC_HOST)

  def test_support_email(self):
    self.assertEqual('support@blaze-pay.com', constants.SUPPORT_EMAIL)

  def test_full_support(self):
    self.assertEqual('"Blaze Support" <support@blaze-pay.com>',
                     constants.FULL_SUPPORT_EMAIL)

  def test_no_reply_email(self):
    self.assertEqual('noreply@blaze-pay.com', constants.NO_REPLY_EMAIL)

  def test_full_noreply(self):
    self.assertEqual('"Blaze" <noreply@blaze-pay.com>',
                     constants.FULL_NO_REPLY_EMAIL)

  def test_contact_email(self):
    self.assertEqual('contact@blaze-pay.com', constants.CONTACT_EMAIL)

  def test_logs_email(self):
    self.assertEqual('"Blaze Logs" <blaze-logs@jgxlabs.com>',
                     constants.FULL_LOGS_EMAIL)

  def test_default_fee_percentage(self):
    self.assertEqual('0.02', constants.DEFAULT_FEE_PERCENTAGE)

  def test_jmd_currency(self):
    self.assertEqual('jmd', constants.JMD_CURRENCY)

  def test_usd_currency(self):
    self.assertEqual('usd', constants.USD_CURRENCY)

  def test_currencies(self):
    self.assertEqual((constants.JMD_CURRENCY, constants.USD_CURRENCY),
                     constants.CURRENCIES)
