import unittest2

from library import testing
from models.funding_source import FundingSource


class TestProfileView(testing.TestCase, unittest2.TestCase):

  def test_profile_view_not_logged_in(self):
    response = self.app.get(self.uri_for('profile.view'))
    self.assertRedirects(response)

  @testing.logged_in
  def test_profile_view_logged_in(self):
    response = self.app.get(self.uri_for('profile.view'))
    self.assertOk(response)

  @testing.logged_in
  def test_correct_heading(self):
    response = self.app.get(self.uri_for('profile.view'))
    self.assertEqual('My account', response.pyquery('h2').text())

  @testing.logged_in
  def test_correct_email_in_heading(self):
    profile = self.get_current_profile()
    response = self.app.get(self.uri_for('profile.view'))
    self.assertEqual(profile.email,
                     response.pyquery('.profile-detail-heading').text())

  @testing.logged_in
  def test_correct_templates_are_used(self):
    response = self.app.get(self.uri_for('profile.view'))
    self.assertOk(response)
    self.assertTemplateUsed(
        'private_base.haml',
        'profile_view.haml',
        'components/basic_info_section.haml',
        'components/funding_source_table.haml',
        'modals/funding_source_create.haml')

  @testing.logged_in
  def test_stripe_api_javascript_on_page(self):
    response = self.app.get(self.uri_for('profile.view'))
    stripe_tags = [tag for tag in response.pyquery('script')
                   if 'js.stripe.com' in tag.get('src')]
    self.assertLength(1, stripe_tags)

  @testing.logged_in
  def test_user_info_shows_in_component(self):
    profile = self.get_current_profile()
    response = self.app.get(self.uri_for('profile.view'))
    self.assertOk(response)
    self.assertTemplateUsed('components/basic_info_section.haml')
    basic_info = response.pyquery('.basic-info-section').text()
    self.assertIn(profile.name, basic_info)
    self.assertIn(profile.email, basic_info)
    self.assertIn(str(profile.usd_balance), basic_info)
    self.assertIn(str(profile.jmd_balance), basic_info)

  @testing.logged_in
  def test_funding_sources_displayed_in_table(self):
    profile = self.get_current_profile()
    funding_source = self.create_funding_source(
        parent=profile, status=FundingSource.Status.Accepted)
    response = self.app.get(self.uri_for('profile.view'))
    self.assertOk(response)
    self.assertLength(1, response.pyquery('tr.funding_source'))
    funding_source_key = response.pyquery(
        'input[name="funding_source"]').attr('value')
    self.assertEqual(str(funding_source.key()), funding_source_key)
