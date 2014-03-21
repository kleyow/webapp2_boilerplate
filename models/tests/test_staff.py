import datetime

import unittest2
from webapp2_extras import security

from library import constants, testing
from models.staff import Staff


class TestStaff(testing.TestCase, unittest2.TestCase):

  def test_defaults(self):
    staff = Staff()
    self.assertIsNone(staff.name)
    self.assertIsNone(staff.username)
    self.assertIsNone(staff.password_hash)
    self.assertIsNone(staff.pin)
    self.assertFalse(staff.is_active)
    self.assertAlmostEqual(datetime.datetime.now(), staff.created,
                           delta=datetime.timedelta(seconds=5))
    self.assertEqual(0, staff.jmd_tip_balance)
    self.assertEqual(0, staff.usd_tip_balance)
    self.assertEqual(Staff.Role.Staff, staff.role)

  def test_set_pin_changes_pin_when_put_is_true(self):
    staff = Staff(parent=self.create_organization())
    staff.set_pin('2345', put=True)
    self.assertNotEqual('2345', staff.pin)

  def test_set_pin_only_accepts_strings(self):
    staff = Staff()
    self.assertRaises(TypeError, staff.set_pin, object())
    self.assertRaises(TypeError, staff.set_pin, 1234)

  def test_get_short_name(self):
    staff = self.create_staff(name='First Last')
    self.assertEqual('First', staff.get_short_name())

    staff.name = None
    self.assertIsNone(staff.get_short_name())

    staff.name = ''
    self.assertIsNone(staff.get_short_name())

    staff.name = 'Single'
    self.assertEqual('Single', staff.get_short_name())

    staff.name = 'Extra-Long Name With Hyphens'
    self.assertEqual('Extra-Long', staff.get_short_name())

    staff.name = 'J.P. Morgan'
    self.assertEqual('J.P.', staff.get_short_name())

  def test_set_pin_dosent_change_pin_when_put_is_false(self):
    staff = Staff(parent=self.create_organization())
    staff.set_pin('1234', put=True)
    staff.put()
    staff.set_pin('2345', put=False)

    # Check to see if the pin has changed.
    self.assertTrue(security.check_password_hash('2345', staff.pin))
    staff = Staff.get(staff.key())
    self.assertFalse(security.check_password_hash('2345', staff.pin))
    self.assertTrue(staff.check_pin('1234'))
    self.assertFalse(staff.check_pin('2222'))

  def test_check_pin(self):
    staff = Staff()
    staff.set_pin('1234')
    self.assertTrue(security.check_password_hash('1234', staff.pin))
    self.assertFalse(security.check_password_hash('2345', staff.pin))

  def test_is_activated_no_pin(self):
    staff = Staff(parent=self.create_organization())
    self.assertFalse(staff.is_activated())

  def test_is_activated_with_pin(self):
    staff = Staff(parent=self.create_organization())
    staff.set_pin('1234', put=True)
    self.assertTrue(staff.is_activated())

  def test_get_organization(self):
    organization = self.create_organization()
    staff = Staff(parent=organization)
    self.assertIsNotNone(staff.get_organization)
    self.assertEqual(organization.key(), staff.get_organization().key())

  def test_put(self):
    organization = self.create_organization()
    staff = Staff(parent=organization)
    staff.put()

    # Ensure staff member is persisted to the datastore.
    self.assertLength(1, Staff.all())
    self.assertIsNotNone(staff.get_organization())
    self.assertEqual(organization.key(), staff.get_organization().key())

  def test_put_without_parent(self):
    staff = Staff()
    self.assertRaises(RuntimeError, staff.put)

  def test_get_by_login(self):
    organization = self.create_organization()
    password_hash = security.generate_password_hash(self.DEFAULT_PASSWORD)
    staff = Staff(username='test',
                  parent=organization, password_hash=password_hash)
    staff.put()
    login = '%s@%s' % (staff.username, organization.identifier)
    self.assertIsNotNone(Staff.get_by_login(login))
    self.assertEqual(
        staff.key(), Staff.get_by_login(login).key())

  def test_get_by_login_invalid_login(self):
    self.assertIsNone(Staff.get_by_login('test@example'))

  def test_get_by_login_nonexistent_username(self):
    organization = self.create_organization()
    login = 'invalid@%s' % organization.identifier
    self.assertIsNone(Staff.get_by_login(login))

  def test_set_password_changes_password_when_put_is_true(self):
    staff = Staff(parent=self.create_organization())
    staff.set_password(self.DEFAULT_PASSWORD, put=True)
    self.assertNotEqual(self.DEFAULT_PASSWORD, staff.password_hash)

  def test_set_password_only_accepts_strings(self):
    staff = Staff()
    self.assertRaises(TypeError, staff.set_password, object())
    self.assertRaises(TypeError, staff.set_password, 1234)

  def test_set_password_dosent_change_password_when_put_is_false(self):
    staff = Staff(parent=self.create_organization())
    staff.set_password(self.DEFAULT_PASSWORD, put=True)
    staff.put()
    staff.set_password('test', put=False)

    # Check to see if the password has changed.
    self.assertTrue(security.check_password_hash('test', staff.password_hash))
    staff = Staff.get(staff.key())
    self.assertFalse(security.check_password_hash('test', staff.password_hash))
    self.assertTrue(staff.check_password(self.DEFAULT_PASSWORD))
    self.assertFalse(staff.check_password('test'))

  def test_check_password(self):
    staff = Staff()
    staff.set_pin('1234')
    self.assertTrue(security.check_password_hash('1234', staff.pin))
    self.assertFalse(security.check_password_hash('2345', staff.pin))

  def test_get_tip_balance_jmd(self):
    staff = self.create_staff(jmd_tip_balance=2000)
    self.assertEqual(2000, staff.get_tip_balance(constants.JMD_CURRENCY))

  def test_get_tip_balance_usd(self):
    staff = self.create_staff(usd_tip_balance=2000)
    self.assertEqual(2000, staff.get_tip_balance(constants.USD_CURRENCY))

  def test_get_tip_balance_edge_case(self):
    staff = self.create_staff()
    self.assertRaises(ValueError, staff.get_tip_balance, 'jimmy')

  def test_increment_tip_balance_jmd(self):
    staff = self.create_staff()
    self.assertEqual(0, staff.jmd_tip_balance)
    staff.increment_tip_balance(constants.JMD_CURRENCY, 1000)
    self.assertEqual(1000, staff.jmd_tip_balance)
    self.assertEqual(0, staff.usd_tip_balance)

  def test_increment_tip_balance_usd(self):
    staff = self.create_staff()
    self.assertEqual(0, staff.usd_tip_balance)
    staff.increment_tip_balance(constants.USD_CURRENCY, 1000)
    self.assertEqual(1000, staff.usd_tip_balance)
    self.assertEqual(0, staff.jmd_tip_balance)

  def test_increment_tip_balance_put(self):
    staff = Staff(parent=self.create_organization())
    self.assertEqual(0, staff.usd_tip_balance)
    staff.increment_tip_balance(constants.USD_CURRENCY, 1000, put=True)
    self.assertEqual(1000, staff.usd_tip_balance)
    self.assertEqual(0, staff.jmd_tip_balance)
    self.assertLength(1, Staff.all())

  def test_increment_tip_balance_put_false(self):
    staff = Staff(parent=self.create_organization())
    self.assertEqual(0, staff.usd_tip_balance)
    staff.increment_tip_balance(constants.USD_CURRENCY, 1000, put=False)
    self.assertEqual(1000, staff.usd_tip_balance)
    self.assertEqual(0, staff.jmd_tip_balance)
    self.assertLength(0, Staff.all())

  def test_increment_tip_balances_edge_cases(self):
    staff = self.create_staff()
    self.assertEqual(0, staff.usd_tip_balance)
    self.assertRaises(ValueError, staff.increment_tip_balance, 'jimmy', 1000)
    self.assertEqual(0, staff.usd_tip_balance)
    self.assertEqual(0, staff.jmd_tip_balance)

  def test_is_editable_by_admin(self):
    """Ensure admins are editable by themselves only."""

    organization = self.create_organization()
    staff1 = self.create_staff(role=Staff.Role.Admin,
                               organization=organization)
    staff2 = self.create_staff(role=Staff.Role.Admin,
                               organization=organization)
    staff3 = self.create_staff(role=Staff.Role.Manager,
                               organization=organization)
    staff4 = self.create_staff(organization=organization)
    staff5 = self.create_staff(role=Staff.Role.Admin)
    staff6 = self.create_staff(role=Staff.Role.Manager)
    staff7 = self.create_staff()

    self.assertTrue(staff1.is_editable_by(staff1))
    self.assertFalse(staff1.is_editable_by(staff2))
    self.assertFalse(staff1.is_editable_by(staff3))
    self.assertFalse(staff1.is_editable_by(staff4))
    self.assertFalse(staff1.is_editable_by(staff5))
    self.assertFalse(staff1.is_editable_by(staff6))
    self.assertFalse(staff1.is_editable_by(staff7))

  def test_is_editable_by_manager(self):
    """Ensure managers are editable by themselves, managers and admins."""

    organization = self.create_organization()
    staff1 = self.create_staff(role=Staff.Role.Admin,
                               organization=organization)
    staff2 = self.create_staff(role=Staff.Role.Manager,
                               organization=organization)
    staff3 = self.create_staff(role=Staff.Role.Manager,
                               organization=organization)
    staff4 = self.create_staff(organization=organization)
    staff5 = self.create_staff(role=Staff.Role.Admin)
    staff6 = self.create_staff(role=Staff.Role.Manager)
    staff7 = self.create_staff()

    self.assertTrue(staff2.is_editable_by(staff1))
    self.assertTrue(staff2.is_editable_by(staff2))
    self.assertTrue(staff2.is_editable_by(staff3))
    self.assertFalse(staff2.is_editable_by(staff4))
    self.assertFalse(staff2.is_editable_by(staff5))
    self.assertFalse(staff2.is_editable_by(staff6))
    self.assertFalse(staff2.is_editable_by(staff7))

  def test_is_editable_by_staff(self):
    """Ensure staff are editable by themselves, managers and admins."""

    organization = self.create_organization()
    staff1 = self.create_staff(role=Staff.Role.Admin,
                               organization=organization)
    staff2 = self.create_staff(role=Staff.Role.Manager,
                               organization=organization)
    staff3 = self.create_staff(organization=organization)
    staff4 = self.create_staff(organization=organization)
    staff5 = self.create_staff(role=Staff.Role.Admin)
    staff6 = self.create_staff(role=Staff.Role.Manager)
    staff7 = self.create_staff()

    self.assertTrue(staff3.is_editable_by(staff1))
    self.assertTrue(staff3.is_editable_by(staff2))
    self.assertTrue(staff3.is_editable_by(staff3))
    self.assertFalse(staff3.is_editable_by(staff4))
    self.assertFalse(staff3.is_editable_by(staff5))
    self.assertFalse(staff3.is_editable_by(staff6))
    self.assertFalse(staff3.is_editable_by(staff7))
