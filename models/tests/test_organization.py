import datetime
import decimal
import unittest2

from library import constants, testing

from models.organization import Organization
from models.staff import Staff


class TestOrganization(testing.TestCase, unittest2.TestCase):

  def test_organization_defaults(self):
    organization = Organization()
    self.assertIsNone(organization.name)
    self.assertIsNone(organization.owner)
    self.assertIsNone(organization.address)
    self.assertIsNone(organization.logo_url)
    self.assertAlmostEqual(datetime.datetime.now(), organization.created,
                           delta=datetime.timedelta(seconds=5))
    self.assertEqual(0, organization.jmd_balance)
    self.assertEqual(0, organization.usd_balance)
    self.assertEqual(0, organization.jmd_fees)
    self.assertEqual(0, organization.usd_fees)
    self.assertFalse(organization.is_verified)
    self.assertEqual(constants.DEFAULT_FEE_PERCENTAGE,
                     organization.fee_percentage)
    self.assertIsNone(organization.identifier)

  def test_get_by_identifier(self):
    organization = self.create_organization(identifier='test')
    self.assertIsNotNone(Organization.get_by_identifier('test'))
    self.assertEqual(
        organization.key(), Organization.get_by_identifier('test').key())

  def test_get_by_identifier_not_found(self):
    self.assertIsNone(Organization.get_by_identifier('test'))

  def test_is_editable_by_profile(self):
    owner_profile = self.create_profile('admin@example.com')
    unauthorized_profile = self.create_profile('test@example.com')
    organization = Organization()
    organization.owner = owner_profile

    self.assertTrue(organization.is_editable_by(owner_profile))
    self.assertFalse(organization.is_editable_by(unauthorized_profile))

  def test_is_editable_by_staff(self):
    """Ensure Organizations are editable by their admins and managers only."""

    organization = self.create_organization()
    staff1 = self.create_staff(role=Staff.Role.Admin,
                               organization=organization)
    staff2 = self.create_staff(role=Staff.Role.Manager,
                               organization=organization)
    staff3 = self.create_staff(organization=organization)
    staff4 = self.create_staff(role=Staff.Role.Admin)
    staff5 = self.create_staff(role=Staff.Role.Manager)
    staff6 = self.create_staff()

    self.assertTrue(organization.is_editable_by(staff1))
    self.assertTrue(organization.is_editable_by(staff2))
    self.assertFalse(organization.is_editable_by(staff3))
    self.assertFalse(organization.is_editable_by(staff4))
    self.assertFalse(organization.is_editable_by(staff5))
    self.assertFalse(organization.is_editable_by(staff6))

  def test_is_viewable_by_staff(self):
    """Ensure Organizations are editable by their admins and managers only."""

    organization = self.create_organization()
    staff1 = self.create_staff(role=Staff.Role.Admin,
                               organization=organization)
    staff2 = self.create_staff(role=Staff.Role.Manager,
                               organization=organization)
    staff3 = self.create_staff(organization=organization)
    staff4 = self.create_staff(role=Staff.Role.Admin)
    staff5 = self.create_staff(role=Staff.Role.Manager)
    staff6 = self.create_staff()

    self.assertTrue(organization.is_viewable_by(staff1))
    self.assertTrue(organization.is_viewable_by(staff2))
    self.assertTrue(organization.is_viewable_by(staff3))
    self.assertFalse(organization.is_viewable_by(staff4))
    self.assertFalse(organization.is_viewable_by(staff5))
    self.assertFalse(organization.is_viewable_by(staff6))

  def test_get_fee_percentage(self):
    organization = Organization(fee_percentage='0.04')
    fee_percentage = organization.get_fee_percentage()
    self.assertIsInstance(fee_percentage, decimal.Decimal)
    self.assertEqual(decimal.Decimal('0.04'), fee_percentage)

  def test_get_fee_percentage_default(self):
    organization = Organization()
    fee_percentage = organization.get_fee_percentage()
    default_fee = constants.DEFAULT_FEE_PERCENTAGE
    self.assertIsInstance(fee_percentage, decimal.Decimal)
    self.assertEqual(decimal.Decimal(default_fee), fee_percentage)

  def test_get_staff(self):
    organization = self.create_organization()
    self.assertLength(0, organization.get_staff())
    staff = self.create_staff(organization=organization)
    self.assertLength(1, organization.get_staff())
    self.assertEqual(staff.key(), Staff.all().get().key())

  def test_get_staff_only_retrieves_relevant_staff(self):
    organization = self.create_organization()
    third_party_organization = self.create_organization()

    staff = Staff(name='test', parent=third_party_organization,
                  username='test@blaze')
    staff.put()

    staff_profile = organization.get_staff()
    self.assertLength(0, staff_profile)

  def test_get_balance(self):
    organization = self.create_organization(usd_balance=3000, jmd_balance=4000)
    self.assertEqual(3000, organization.get_balance(constants.USD_CURRENCY))
    self.assertEqual(4000, organization.get_balance(constants.JMD_CURRENCY))

  def test_get_balance_edge_cases(self):
    organization = self.create_organization()
    self.assertRaises(ValueError, organization.get_balance, 'jimmy')

  def test_get_fees(self):
    organization = self.create_organization(usd_fees=3000, jmd_fees=4000)
    self.assertEqual(3000, organization.get_fees(constants.USD_CURRENCY))
    self.assertEqual(4000, organization.get_fees(constants.JMD_CURRENCY))

  def test_get_fees_edge_cases(self):
    organization = self.create_organization()
    self.assertRaises(ValueError, organization.get_fees, 'jimmy')

  def test_increment_balance_usd_no_put(self):
    organization = self.create_organization()
    self.assertEqual(0, organization.usd_balance)
    organization.increment_balance(constants.USD_CURRENCY, 2000)
    self.assertEqual(2000, organization.usd_balance)
    self.assertEqual(0, organization.jmd_balance)

    # Ensure nothing has been written to the datastore.
    organization = Organization.get(organization.key())
    self.assertEqual(0, organization.jmd_balance)
    self.assertEqual(0, organization.usd_balance)

  def test_increment_balance_jmd_no_put(self):
    organization = self.create_organization()
    self.assertEqual(0, organization.jmd_balance)
    organization.increment_balance(constants.JMD_CURRENCY, 2000)
    self.assertEqual(2000, organization.jmd_balance)
    self.assertEqual(0, organization.usd_balance)

    # Ensure nothing has been written to the datastore.
    organization = Organization.get(organization.key())
    self.assertEqual(0, organization.jmd_balance)
    self.assertEqual(0, organization.usd_balance)

  def test_increment_balance_put(self):
    organization = self.create_organization()
    self.assertEqual(0, organization.jmd_balance)
    organization.increment_balance(constants.JMD_CURRENCY, 2000, put=True)

    # Ensure the datastore representation has been updated.
    organization = Organization.get(organization.key())
    self.assertEqual(2000, organization.jmd_balance)
    self.assertEqual(0, organization.usd_balance)

  def test_increment_balance_edge_cases(self):
    organization = self.create_organization()
    self.assertEqual(0, organization.jmd_balance)
    self.assertEqual(0, organization.usd_balance)
    self.assertRaises(
        ValueError, organization.increment_balance, 'jimmy', 2000)

    # Ensure both balances are unchanged.
    self.assertEqual(0, organization.jmd_balance)
    self.assertEqual(0, organization.usd_balance)

  def test_increment_fees_usd_no_put(self):
    organization = self.create_organization()
    self.assertEqual(0, organization.usd_fees)
    organization.increment_fees(constants.USD_CURRENCY, 2000)
    self.assertEqual(2000, organization.usd_fees)
    self.assertEqual(0, organization.jmd_fees)

    # Ensure nothing has been written to the datastore.
    organization = Organization.get(organization.key())
    self.assertEqual(0, organization.jmd_fees)
    self.assertEqual(0, organization.usd_fees)

  def test_increment_fees_jmd_no_put(self):
    organization = self.create_organization()
    self.assertEqual(0, organization.jmd_fees)
    organization.increment_fees(constants.JMD_CURRENCY, 2000)
    self.assertEqual(2000, organization.jmd_fees)
    self.assertEqual(0, organization.usd_fees)

    # Ensure nothing has been written to the datastore.
    organization = Organization.get(organization.key())
    self.assertEqual(0, organization.jmd_fees)
    self.assertEqual(0, organization.usd_fees)

  def test_increment_fees_edge_cases(self):
    organization = self.create_organization()
    self.assertEqual(0, organization.jmd_fees)
    self.assertEqual(0, organization.usd_fees)
    self.assertRaises(
        ValueError, organization.increment_fees, 'jimmy', 2000)

    # Ensure both currency fees are unchanged.
    self.assertEqual(0, organization.jmd_fees)
    self.assertEqual(0, organization.usd_fees)

  def test_increment_fees_put(self):
    organization = self.create_organization()
    self.assertEqual(0, organization.jmd_fees)
    organization.increment_fees(constants.JMD_CURRENCY, 2000, put=True)

    # Ensure datastore writes have occured.
    organization = Organization.get(organization.key())
    self.assertEqual(2000, organization.jmd_fees)
    self.assertEqual(0, organization.usd_fees)
