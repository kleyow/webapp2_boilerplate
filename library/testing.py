from contextlib import contextmanager
import datetime
from functools import wraps
import logging
import os

from google.appengine.datastore import datastore_stub_util
from google.appengine.ext import testbed
import mock
import webapp2
import webapp2_extras
import webtest

from library import constants, csrf
import main
from main import app
from models.event import Event
from models.funding_source import FundingSource
from models.organization import Organization
from models.profile import Profile
from models.staff import Staff
from models.ticket import Ticket
from models.transaction import Transaction


__all__ = ['logged_in', 'login_as', 'login_as_staff', 'staff_logged_in',
           'TestCase']


ROOT_PATH = os.path.dirname(main.__file__)
HR_LOW_CONSISTENCY_POLICY = (datastore_stub_util
                             .PseudoRandomHRConsistencyPolicy(probability=0))
HR_HIGH_CONSISTENCY_POLICY = (datastore_stub_util
                              .PseudoRandomHRConsistencyPolicy(probability=1))


class TestCase(object):
  # Default values
  # ==============
  DEFAULT_ADDRESS = '13 Some Street'
  DEFAULT_EMAIL = 'test@example.org'
  DEFAULT_PASSWORD = 'passwr0d'
  DEFAULT_ORGANIZATION_NAME = 'Test Organization'
  DEFAULT_ORGANIZATION_IDENTIFIER = 'testorg'
  DEFAULT_USERNAME = 'staffmember'
  DEFAULT_STAFF_LOGIN = '%s@%s' % (DEFAULT_USERNAME,
                                   DEFAULT_ORGANIZATION_IDENTIFIER)
  DEFAULT_STAFF_NAME = 'Althea'
  DEFAULT_PROFILE_NAME = 'Test Profile'
  DEFAULT_UNHASHED_PIN = '1234'
  DEFAULT_EVENT_NAME = 'Dash Out Thursdays'
  DEFAULT_LOCATION = 'Tivoli Gardens'
  DEFAULT_STRIPE_CUSTOMER_ID = 'stripe123'

  # Custom headers for requests
  # ===========================
  CRON_HEADERS = {'X-Appengine-Cron': 'true'}
  TASKQUEUE_HEADERS = {'X-AppEngine-QueueName': 'default'}

  # Standard TestCase setUp and tearDown
  # ====================================

  def setUp(self):
    if hasattr(super(TestCase, self), 'setUp'):
      super(TestCase, self).setUp()
    self.configure_appengine()
    self.configure_app()
    self.configure_csrf()
    self.configure_jinja2()
    self.configure_timezone()

    # HTTP_HOST is required for any handlers that hit the task queue
    if 'HTTP_HOST' not in os.environ:
      os.environ['HTTP_HOST'] = 'localhost:80'

  def tearDown(self):
    self.testbed.deactivate()

  # Configuration helpers
  # =====================

  def configure_appengine(self):
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_mail_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_taskqueue_stub(root_path=ROOT_PATH)

    self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)
    self.taskqueue_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
    self.datastore_stub = self.testbed.get_stub(testbed.DATASTORE_SERVICE_NAME)
    self.datastore_stub._consistency_policy = HR_HIGH_CONSISTENCY_POLICY

  @contextmanager
  def datastore_consistency_policy(self, policy):
    """A context manager that allows us to modify the consistency policy for
    certain tests, so we can simulate the behaviour of the High Replication
    Datastore.

    Example:

      with self.datastore_consistency_policy(POLICY):
        do_something_that_uses_transactions()

    """
    prev_policy = self.datastore_stub._consistency_policy
    self.datastore_stub._consistency_policy = policy
    yield
    self.datastore_stub._consistency_policy = prev_policy

  def configure_app(self):
    app.set_globals(app=app, request=self.get_request())

    if not hasattr(self, 'app'):
      self.app = webtest.TestApp(app)

  def configure_csrf(self, enabled=False):
    if not hasattr(csrf.CSRF, '_original_token_required'):
      csrf.CSRF._original_token_required = csrf.CSRF.token_required

    if enabled:
      token_required = csrf.CSRF._original_token_required
    else:
      token_required = mock.Mock(return_value=False)

    csrf.CSRF.token_required = token_required

  def configure_jinja2(self):
    """Hook into Jinja2's template loader to track which templates are used."""
    # Make sure the app is configured:
    self.configure_app()

    # Keep track of a few things (this test case, the template loader, the
    # original get_source method)
    test_case = self
    environment = self.get_jinja2().environment
    original_get_source = environment.loader.get_source
    original_do_request = self.app.do_request

    # These *could* be defined elsewhere, but we don't want them if we don't
    # call configure_jinja2, so we assign these instance methods and vars here
    test_case._templates_used = []

    def get_templates_used():
      return test_case._templates_used

    def assertTemplateUsed(*templates):
      for template in templates:
        test_case.assertIn(template, test_case.get_templates_used())

    def assertTemplateNotUsed(*templates):
      for template in templates:
        test_case.assertNotIn(template, test_case.get_templates_used())

    test_case.get_templates_used = get_templates_used
    test_case.assertTemplateUsed = assertTemplateUsed
    test_case.assertTemplateNotUsed = assertTemplateNotUsed

    # Ensure that we are never pulling from the cache (otherwise, get_source
    # will never get called).
    environment.cache = None

    # Inject our own version of get_source (rather than an entire Loader)
    def get_source(environment, template):
      test_case._templates_used.append(template)
      return original_get_source(environment, template)

    environment.loader.get_source = get_source

    # Inject into WebTest's do_request method so that we clear the templates
    # on each request
    def do_request(*args, **kwargs):
      test_case._templates_used = []
      return original_do_request(*args, **kwargs)

    self.app.do_request = do_request

  def configure_timezone(self):
    os.environ['TZ'] = 'UTC'

  # Special getters
  # ===============

  @classmethod
  def get_request(cls):
    request = webapp2.Request.blank('/')
    request.app = app
    return request

  @classmethod
  def get_auth(cls):
    return webapp2_extras.auth.get_auth(request=cls.get_request())

  @classmethod
  def get_jinja2(cls):
    return webapp2_extras.jinja2.get_jinja2(app=app)

  @classmethod
  def uri_for(cls, name, *args, **kwargs):
    return webapp2.uri_for(name, cls.get_request(), *args, **kwargs)

  # Authentication-related methods
  # ==============================

  @classmethod
  def create_profile(cls, email=None, password=None, name=None,
                     is_admin=False, beta_tester=True, activated=True,
                     usd_balance=0, jmd_balance=0, pin=None):
    # TODO: Move this into a top level function (testing.create_profile)
    # Use defaults if anything here is missing.
    UserModel = cls.get_auth().store.user_model

    if not email:
      # Generate an e-mail that should be unique...
      email = '%s-%s' % (UserModel.query().count(), cls.DEFAULT_EMAIL)
    password = password or cls.DEFAULT_PASSWORD

    # Create the auth.user_model.
    ok, user = UserModel.create_user(email, password_raw=password)

    if not ok:
      raise Exception('Error creating auth.User: %s' % email)

    # Create the profile.
    profile = Profile(name=(name or cls.DEFAULT_PROFILE_NAME), email=email,
                      is_admin=is_admin, beta_tester=beta_tester,
                      activated=activated, auth_user_id=user.key.id(),
                      timezone='UTC', usd_balance=usd_balance,
                      jmd_balance=jmd_balance)

    profile.set_pin(cls.DEFAULT_UNHASHED_PIN)
    profile.put()

    # Return the profile (we can get everything else with that)
    return profile

  def create_organization(self, verified=True, owner=None, staff=None,
                          address=None, name=None, fee_percentage=None,
                          usd_balance=0, jmd_balance=0, identifier=None,
                          usd_fees=0, jmd_fees=0):
    # Set the defaults for the organization we want to create.
    owner = owner or self.create_profile()
    staff = staff or []
    address = address or self.DEFAULT_ADDRESS
    name = name or self.DEFAULT_ORGANIZATION_NAME
    fee_percentage = fee_percentage or constants.DEFAULT_FEE_PERCENTAGE
    identifier = identifier or self.DEFAULT_ORGANIZATION_IDENTIFIER

    organization = Organization(verified=verified, owner=owner, staff=staff,
                                address=address, name=name,
                                fee_percentage=fee_percentage,
                                jmd_balance=jmd_balance,
                                usd_balance=usd_balance, identifier=identifier,
                                usd_fees=usd_fees, jmd_fees=jmd_fees)
    organization.put()

    return organization

  def create_funding_source(self, parent=None, is_verified=True, status=None,
                            customer_id=None):
    status = status or FundingSource.Status.Pending
    parent = parent or self.create_profile()
    customer_id = customer_id or self.DEFAULT_STRIPE_CUSTOMER_ID

    funding_source = FundingSource(parent=parent, status=status,
                                   is_verified=is_verified,
                                   customer_id=customer_id)
    funding_source.put()

    return funding_source

  # For now currency defaults to USD as to not break everything while JMD
  # is implemented into the system.
  def create_transaction(self, transaction_type=None, funding_source=None,
                         amount=0, status=Transaction.Status.Pending,
                         sender=None, recipient=None, verifier=None,
                         uuid=None, currency=constants.USD_CURRENCY,
                         tip_amount=0, fees=0, is_cash_deposit=False):

    # Ensure that sender and recipient are configured correctly for the
    # transaction type.
    if transaction_type == Transaction.Type.Transfer:
      # Transfers have a sender and recipient, which must both be Profile
      # objects, and do not have a funding source.
      sender = sender or self.create_profile()
      recipient = recipient or self.create_profile()

    elif transaction_type == Transaction.Type.Purchase:
      # Purchases and refunds have a sender and recipient.
      # The sender must be a Profile object, and the recipient must be an
      # Organization.
      # Like transfers, purchases have no funding source.
      sender = sender or self.create_profile()
      recipient = recipient or self.create_organization()

    elif transaction_type == Transaction.Type.Deposit and not is_cash_deposit:
      # Deposits have a recipient, a Profile object, and a funding source.
      recipient = recipient or self.create_profile()
      funding_source = funding_source or self.create_funding_source()

    elif transaction_type == Transaction.Type.Deposit and is_cash_deposit:
      recipient = recipient or self.create_profile()
      sender = sender or self.create_profile(is_admin=True)

    else:
      raise ValueError('%s is not a valid transaction type.' %
                       transaction_type)

    transaction = Transaction(
        transaction_type=transaction_type, funding_source=funding_source,
        amount=amount, status=status, sender=sender, recipient=recipient,
        verifier=verifier, uuid=uuid, currency=currency, tip_amount=tip_amount,
        fees=fees)
    transaction.put()
    return transaction

  def create_staff(self, name=None, username=None, password=None,
                   organization=None, pin=None, usd_tip_balance=0,
                   jmd_tip_balance=0,  is_active=False, role=None):
    name = name or self.DEFAULT_PROFILE_NAME
    username = username or self.DEFAULT_USERNAME
    password = password or self.DEFAULT_PASSWORD
    pin = pin or self.DEFAULT_UNHASHED_PIN
    organization = organization or self.create_organization()
    name = name or self.DEFAULT_STAFF_NAME
    role = role or Staff.Role.Staff

    staff = Staff(name=name, username=username, parent=organization,
                  usd_tip_balance=usd_tip_balance,
                  jmd_tip_balance=jmd_tip_balance, is_active=is_active,
                  role=role)
    staff.set_password(password)
    staff.set_pin(pin)
    staff.put()

    return staff

  def create_event(self, name=None, date=None, location=None, max_tickets=0,
                   organization=None, usd_price=0, jmd_price=0):
    name = name or self.DEFAULT_EVENT_NAME
    date = date or datetime.datetime.now()
    location = location or self.DEFAULT_LOCATION
    organization = organization or self.create_organization()

    event = Event(name=name, date=date, location=location,
                  max_tickets=max_tickets, parent=organization,
                  usd_price=usd_price, jmd_price=jmd_price)
    event.put()

    return event

  def create_ticket(self, transaction=None, event=None, usd_price=0,
                    jmd_price=0):
    transaction = transaction or self.create_transaction(
        transaction_type=Transaction.Type.Purchase)
    event = event or self.create_event()

    ticket = Ticket(transaction=transaction, parent=event, usd_price=usd_price,
                    jmd_price=jmd_price)
    ticket.put()

    return ticket

  def login(self, email=None, password=None):
    login_data = {'email': email or self.DEFAULT_EMAIL,
                  'password': password or self.DEFAULT_PASSWORD}
    return self.app.post(self.uri_for('login'), login_data)

  def logout(self):
    return self.app.get(self.uri_for('logout'))

  def staff_login(self, login=None, password=None):
    login_data = {'username': login or self.DEFAULT_STAFF_LOGIN,
                  'password': password or self.DEFAULT_PASSWORD}
    return self.app.post(self.uri_for('staff.login'), login_data)

  def staff_logout(self):
    return self.app.get(self.uri_for('staff.logout'))

  # Custom assert methods
  # =====================

  def assertOk(self, response, message=None):
    self.assertEqual(200, response.status_int, message)

  def assertRedirects(self, response, uri=None):
    self.assertTrue(str(response.status_int).startswith('30'),
                    'Expected 30X, got %s' % response.status_int)
    if not uri:
      self.assertTrue(response.location)
    else:
      if not uri.startswith('http'):
        uri = 'http://localhost' + uri

      self.assertEqual(uri, response.location)

  def assertNotFound(self, response):
    self.assertEqual(404, response.status_int)

  def assertLoggedIn(self):
    response = self.app.get(self.uri_for('profile.view'))
    self.assertOk(response)

  def assertNotLoggedIn(self):
    response = self.app.get(self.uri_for('profile.view'))
    self.assertRedirects(response)

  def assertLength(self, expected_length, collection):
    try:
      actual_length = collection.count()
    except:
      actual_length = len(collection)

    self.assertEqual(expected_length, actual_length)

  def assertFlashMessage(self, message=None, level=None, response=None):
    response = response or self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertLength(1, response.pyquery('#notification-bar'))

    if message:
      self.assertEqual(
          message, response.pyquery('#notification-bar .alert div').text())

    if level:
      self.assertTrue(response.pyquery('#notification-bar .alert').hasClass(
                      'alert-%s' % level))

  def assertStaffLoggedIn(self):
    response = self.app.get(self.uri_for('staff.login'))
    self.assertRedirects(response)

  def assertNotStaffLoggedIn(self):
    response = self.app.get(self.uri_for('staff.login'))
    self.assertOk(response)


class login_as(object):

  def __init__(self, email=None, password=None, is_admin=False):
    self.email = email or TestCase.DEFAULT_EMAIL
    self.password = password or TestCase.DEFAULT_PASSWORD
    self.is_admin = is_admin

  def __call__(self, test):
    @wraps(test)
    def wrapped_test(test_case, *args, **kwargs):
      profile = test_case.create_profile(
          email=self.email, password=self.password, is_admin=self.is_admin)
      test_case.login(self.email, self.password)
      test_case.current_profile = profile
      test_case.get_current_profile = lambda: profile
      return test(test_case, *args, **kwargs)
    return wrapped_test


class login_as_staff(object):

  def __init__(self, login=None, password=None, role=None):
    self.login = login or TestCase.DEFAULT_STAFF_LOGIN
    self.password = password or TestCase.DEFAULT_PASSWORD
    self.role = role or Staff.Role.Staff

  def __call__(self, test):
    @wraps(test)
    def wrapped_test(test_case, *args, **kwargs):
      username, identifier = self.login.split('@', 2)
      organization = test_case.create_organization(identifier=identifier)
      staff = test_case.create_staff(
          username=username, organization=organization, role=self.role)
      staff.set_password(self.password, put=True)
      test_case.staff_login(self.login, self.password)
      test_case.current_staff = staff
      test_case.get_current_staff = lambda: staff
      return test(test_case, *args, **kwargs)
    return wrapped_test


logged_in = login_as()
staff_logged_in = login_as_staff()


@contextmanager
def silence_logging():
  """A context manager that allows us to silence logging.

  Example:

    with silence_logging():
      call_method_that_logs_something()

  """
  log = logging.getLogger()
  log.setLevel(99)
  yield
  log.setLevel(30)
