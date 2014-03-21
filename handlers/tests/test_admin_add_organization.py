import decimal

import unittest2

from forms import error_messages
from library import constants, testing
from models.organization import Organization
from models.profile import Profile
from models.staff import Staff


class TestAdminAddOrganization(testing.TestCase, unittest2.TestCase):

  def test_get_add_organization_page_not_logged_in(self):
    response = self.app.get(self.uri_for('admin.add_organization'))
    login_url = self.uri_for(
        'login', redirect=self.uri_for('admin.add_organization'))
    self.assertRedirects(response, login_url)

  @testing.logged_in
  def test_get_add_organization_page_not_admin(self):
    self.assertFalse(self.get_current_profile().is_admin)
    response = self.app.get(self.uri_for('admin.add_organization'))
    self.assertRedirects(response, self.uri_for('home'))
    self.assertFlashMessage(level='error')

  @testing.login_as(is_admin=True)
  def test_get_add_organization_page_admin(self):
    current_profile = self.get_current_profile()
    self.assertTrue(current_profile.is_admin)
    response = self.app.get(self.uri_for('admin.add_organization'))
    self.assertOk(response)
    self.assertTemplateUsed('admin/add_organization.haml')
    self.assertLength(1, response.pyquery('form#add-organization'))

  def test_post_add_organization_page_not_logged_in(self):
    params = {'owner': self.DEFAULT_EMAIL,
              'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 4, 'logo_url': 'test.com/image.png',
              'identifier': self.DEFAULT_ORGANIZATION_IDENTIFIER}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    login_url = self.uri_for(
        'login', redirect=self.uri_for('admin.add_organization'))
    self.assertRedirects(response, login_url)

    # Ensure no organizations were created.
    self.assertLength(0, Organization.all())

  @testing.logged_in
  def test_post_add_organization_page_not_admin(self):
    params = {'owner': self.DEFAULT_EMAIL,
              'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 2, 'logo_url': 'test.com/image.png',
              'identifier': self.DEFAULT_ORGANIZATION_IDENTIFIER}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertRedirects(response, self.uri_for('home'))

    # Ensure no organizations were created.
    self.assertLength(0, Organization.all())

  @testing.login_as(is_admin=True)
  def test_post_add_organization_page_admin(self):
    current_profile = self.get_current_profile()
    self.assertTrue(current_profile.is_admin)
    owner = self.create_profile(email='owner@example.com')

    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 2, 'logo_url': 'test.com/image.png',
              'identifier': self.DEFAULT_ORGANIZATION_IDENTIFIER}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertRedirects(response, self.uri_for('admin.add_organization'))

    # Check that an organization was created.
    self.assertLength(1, Organization.all())
    organization = Organization.all().get()
    self.assertEqual(organization.owner.key(),
                     Profile.get_by_email(owner.email).key())
    self.assertTrue(organization.is_verified)
    self.assertEqual(decimal.Decimal('0.02'),
                     organization.get_fee_percentage())

    # Ensure an Admin Staff account has been created.
    username = organization.owner.get_short_name().lower()
    self.assertLength(1, Staff.all())
    staff = Staff.all().get()
    password = '%s@%s' % (staff.username, organization.identifier)
    self.assertEqual(organization.key(), staff.get_organization().key())
    self.assertEqual(Staff.Role.Admin, staff.role)
    self.assertTrue(staff.is_active)
    self.assertEqual(username, staff.username)
    self.assertEqual(organization.owner.name, staff.name)
    self.assertTrue(staff.check_password(password))

  @testing.login_as(is_admin=True)
  def test_add_organization_admin_flow(self):
    owner = self.create_profile()
    response = self.app.get(self.uri_for('admin.add_organization'))
    self.assertOk(response)
    self.assertTemplateUsed('admin/add_organization.haml')
    self.assertLength(1, response.pyquery('form#add-organization'))

    form = response.forms['add-organization']
    form['owner'] = owner.email
    form['name'] = self.DEFAULT_ORGANIZATION_NAME
    form['identifier'] = self.DEFAULT_ORGANIZATION_IDENTIFIER
    form['fee_percentage'] = 3
    form['logo_url'] = 'test.com/image.png'
    response = form.submit()
    self.assertRedirects(response, self.uri_for('admin.add_organization'))

    # Ensure an organization has been created with the correct details.
    self.assertLength(1, Organization.all())
    organization = Organization.all().get()
    self.assertEqual(form['owner'].value, organization.owner.email)
    self.assertEqual(form['name'].value, organization.name)
    self.assertEqual(form['identifier'].value, organization.identifier)
    self.assertEqual(form['logo_url'].value, organization.logo_url)
    fee_percentage = decimal.Decimal(form['fee_percentage'].value) / 100
    self.assertEqual(fee_percentage, organization.get_fee_percentage())

    # Ensure an Admin Staff account has been created.
    username = organization.owner.get_short_name().lower()
    self.assertLength(1, Staff.all())
    staff = Staff.all().get()
    password = '%s@%s' % (staff.username, organization.identifier)
    self.assertEqual(organization.key(), staff.get_organization().key())
    self.assertEqual(Staff.Role.Admin, staff.role)
    self.assertTrue(staff.is_active)
    self.assertEqual(username, staff.username)
    self.assertEqual(organization.owner.name, staff.name)
    self.assertTrue(staff.check_password(password))

  @testing.login_as(is_admin=True)
  def test_organization_owner_must_be_registered(self):
    params = {'owner': 'invalid@example.com',
              'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 2, 'logo_url': 'test.com/image.png'}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertFlashMessage(level='error', response=response)

    # Ensure no organizations were created.
    self.assertLength(0, Organization.all())

  @testing.login_as(is_admin=True)
  def test_fee_field_accepts_decimal_values(self):
    owner = self.create_profile()
    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 1.5, 'logo_url': 'test.com/image.png',
              'identifier': self.DEFAULT_ORGANIZATION_IDENTIFIER}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertRedirects(response, self.uri_for('admin.add_organization'))

    # Ensure an organization was created with the correct rate.
    self.assertLength(1, Organization.all())
    organization = Organization.all().get()
    self.assertEqual(decimal.Decimal('0.015'),
                     organization.get_fee_percentage())

  @testing.login_as(is_admin=True)
  def test_empty_fee_percentage_sets_default(self):
    owner = self.create_profile()
    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'identifier': self.DEFAULT_ORGANIZATION_IDENTIFIER,
              'logo_url': 'test.com/image.png'}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertRedirects(response, self.uri_for('admin.add_organization'))
    self.assertLength(1, Organization.all())
    organization = Organization.all().get()
    self.assertEqual(constants.DEFAULT_FEE_PERCENTAGE,
                     organization.fee_percentage)

  @testing.login_as(is_admin=True)
  def test_empty_logo_url_field_flashes_error(self):
    owner = self.create_profile()
    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 1.5}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertFlashMessage(message=error_messages.ADMIN_LOGO_REQUIRED,
                            level='error', response=response)

  @testing.login_as(is_admin=True)
  def test_gif_logo_url_upload(self):
    owner = self.create_profile()
    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 1.5, 'logo_url': 'test.com/image.gif',
              'identifier': self.DEFAULT_ORGANIZATION_IDENTIFIER}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertRedirects(response, self.uri_for('admin.add_organization'))

    # Ensure an organization has been created with the correct logo url.
    self.assertLength(1, Organization.all())
    organization = Organization.all().get()
    self.assertEqual('test.com/image.gif', organization.logo_url)

  @testing.login_as(is_admin=True)
  def test_jpg_logo_url_upload(self):
    owner = self.create_profile()
    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 1.5, 'logo_url': 'test.com/image.jpg',
              'identifier': self.DEFAULT_ORGANIZATION_IDENTIFIER}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertRedirects(response, self.uri_for('admin.add_organization'))

    # Ensure an organization has been created with the correct logo url.
    self.assertLength(1, Organization.all())
    organization = Organization.all().get()
    self.assertEqual('test.com/image.jpg', organization.logo_url)

  @testing.login_as(is_admin=True)
  def test_jpeg_logo_url_upload(self):
    owner = self.create_profile()
    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 1.5, 'logo_url': 'test.com/image.jpeg',
              'identifier': self.DEFAULT_ORGANIZATION_IDENTIFIER}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertRedirects(response, self.uri_for('admin.add_organization'))

    # Ensure an organization has been created with the correct logo url.
    self.assertLength(1, Organization.all())
    organization = Organization.all().get()
    self.assertEqual('test.com/image.jpeg', organization.logo_url)

  @testing.login_as(is_admin=True)
  def test_png_logo_url_upload(self):
    owner = self.create_profile()
    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 1.5, 'logo_url': 'test.com/image.png',
              'identifier': self.DEFAULT_ORGANIZATION_IDENTIFIER}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertRedirects(response, self.uri_for('admin.add_organization'))

    # Ensure an organization has been created with the correct logo url.
    self.assertLength(1, Organization.all())
    organization = Organization.all().get()
    self.assertEqual('test.com/image.png', organization.logo_url)

  @testing.login_as(is_admin=True)
  def test_invalid_logo_url_type_flashes_error(self):
    owner = self.create_profile()
    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 1.5, 'logo_url': 'test.com/image.lol'}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertFlashMessage(message=error_messages.ADMIN_LOGO_INVALID,
                            level='error', response=response)

  @testing.login_as(is_admin=True)
  def test_add_organization_existing_identifier(self):
    self.create_organization()
    current_profile = self.get_current_profile()
    self.assertTrue(current_profile.is_admin)
    owner = self.create_profile(email='owner@example.com')

    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 2, 'logo_url': 'test.com/image.png',
              'identifier': self.DEFAULT_ORGANIZATION_IDENTIFIER}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertOk(response)
    self.assertFlashMessage(message=error_messages.ADMIN_IDENTIFIER_IN_USE,
                            level='error', response=response)

    # Check that no new organization was created.
    self.assertLength(1, Organization.all())

  @testing.login_as(is_admin=True)
  def test_add_organization_identifier_missing(self):
    owner = self.create_profile()
    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 2,  'logo_url': 'test.com/image.png'}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertOk(response)
    self.assertFlashMessage(message=error_messages.ADMIN_IDENTIFIER_REQUIRED,
                            level='error', response=response)

    # Check that no organization was created.
    self.assertLength(0, Organization.all())

  @testing.login_as(is_admin=True)
  def test_add_organization_identifier_too_long(self):
    owner = self.create_profile()
    long_identifier = 'a' * 101
    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 2,  'logo_url': 'test.com/image.png',
              'identifier': long_identifier}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertOk(response)
    self.assertFlashMessage(message=error_messages.ADMIN_IDENTIFIER_TOO_LONG,
                            level='error', response=response)

    # Check that no organization was created.
    self.assertLength(0, Organization.all())

  @testing.login_as(is_admin=True)
  def test_add_organization_identifier_in_caps(self):
    owner = self.create_profile()
    caps_identifier = self.DEFAULT_ORGANIZATION_IDENTIFIER.upper()
    params = {'owner': owner.email, 'name': self.DEFAULT_ORGANIZATION_NAME,
              'fee_percentage': 2,  'logo_url': 'test.com/image.png',
              'identifier': caps_identifier}
    response = self.app.post(self.uri_for('admin.add_organization'), params)
    self.assertRedirects(response, self.uri_for('admin.add_organization'))

    # Check that an organization was created and the identifier stored in lower
    # case.
    self.assertLength(1, Organization.all())
    self.assertEqual(owner.get_organization().identifier,
                     self.DEFAULT_ORGANIZATION_IDENTIFIER)
