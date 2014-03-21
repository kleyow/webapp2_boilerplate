# General form error messages.
NAME_REQUIRED = 'You didn\'t enter your name.'
EMAIL_REQUIRED = 'You didn\'t enter your email address.'
INVALID_EMAIL = 'That isn\'t a valid email address.'

# Organization error messages.
ORG_NAME_REQUIRED = 'You didn\'t enter a name for your organization.'
ORG_ADDRESS_REQUIRED = 'You didn\'t enter your organization\'s address.'
ORG_ACCESS_DENIED = 'You are not permitted to view this organization!'
STAFF_NAME_REQUIRED = 'A name of the staff member is required.'
STAFF_NAME_TOO_LONG = 'The staff name you entered is too long.'
STAFF_USERNAME_REQUIRED = 'A username of the staff member required.'
STAFF_USERNAME_TOO_LONG = 'The staff username you entered is too long.'
STAFF_LOGIN_EXISTS = 'There is already a staff member with that login.'
STAFF_ALPHANUMERIC_ONLY = 'Staff login can only be letters and numbers.'
INADEQUATE_ORG_BALANCE = ('Sorry, your organization has reached it\'s deposit '
                          'quota.'
                          'Please contact an administrator of your '
                          'organization.')

# Staff error messages.
STAFF_LOGIN_FAILED = 'Sorry, we couldn\'t find a user with those details.'

# Contact and error reporting error messages.
TOPIC_REQUIRED = 'You didn\'t enter a topic.'
MESSAGE_REQUIRED = 'You didn\'t enter a message.'

# Profile error messages.
PASSWORD_REQUIRED = 'You didn\'t enter a password.'
EMAIL_INVALID_OR_USED = 'That email is currently in use or invalid!'
NAME_TOO_LONG = 'The name you entered is too long.'
PIN_INVALID = 'The PIN you\'ve entered is invalid.'
PASSWORD_INVALID = 'You seem to have mistyped your password. Try again.'
PASSWORD_REQUIRED_UPDATE = 'You need to enter your old password to do that.'

# Transaction error messages.
AMOUNT_REQUIRED = 'You need to enter an amount.'
POSITIVE_AMOUNT_REQUIRED = 'You can\'t enter amounts less than $0.00.'
DECIMAL_PLACES = 'You can\'t have more than 2 decimal places in your amount.'
PIN_REQUIRED = 'You need to enter a PIN.'
RECIPIENT_REQUIRED = 'You didn\'t specify a recipient.'
RECIPIENT_NOT_FOUND = ('Sorry, that recipient doesn\'t seem to be a Blaze '
                       'user.')
RECIPIENT_NOT_ACTIVATED = ('Sorry, that user has not activated their '
                           'account.')
RECIPIENT_NOT_BETA_TESTER = 'Sorry, that user is not a beta tester.'
CURRENCY_REQUIRED = 'You didn\'t specify a currency.'
INVALID_CURRENCY = 'That currency isn\'t supported.'
FUNDING_SOURCE_REQUIRED = 'You didn\'t select a funding source.'
FUNDING_SOURCE_NOT_FOUND = 'That funding source doesn\'t exist.'

# Prevent malicious user from discovering valid funding source keys.
UNAUTHORIZED_FUNDING_SOURCE = FUNDING_SOURCE_NOT_FOUND
INADEQUATE_BALANCE = 'You don\'t have enough Blaze credit.'
SENDER_IS_RECIPIENT = 'You can\'t send money to yourself.'
TRANSACTION_REQUIRED = 'You didn\'t specify a purchase to refund.'
TRANSACTION_NOT_FOUND = 'Sorry, that transaction doesn\'t seem to exist.'
REFUND_PURCHASE_ONLY = 'Sorry, only purchases can be refunded.'
REFUND_COMPLETED_ONLY = 'Sorry, only completed transactions can be refunded.'
REFUND_UNAUTHORIZED = 'Sorry, you are not authorized to trigger a refund.'
ORGANIZATION_INADEQUATE_BALANCE = ('Sorry, the organization\'s balance is too '
                                   'low to make this refund')
UNAUTHORIZED_VERIFICATION = 'You aren\'t allowed to verify transactions.'
ALREADY_VERIFIED = 'Sorry, this transaction has already been verified.'
PURCHASES_ONLY_VERIFIABLE = 'Sorry, only purchases are veriable.'

# Admin error messages.
ADMIN_ORG_NAME_REQUIRED = 'You didn\'t enter a name for the organization.'
ADMIN_ORG_EMAIL_REQUIRED = 'You didn\'t enter an email address for the owner.'
ADMIN_ORG_OWNER_NOT_FOUND = 'That email isn\'t registered.'
ADMIN_INVALID_FEE = 'The fee percentage must be a value between 0 and 100%.'
ADMIN_FEE_REQUIRED = 'You didn\'t specify a fee percentage.'
ADMIN_IDENTIFIER_REQUIRED = 'You didn\'t specify an identifier.'
ADMIN_IDENTIFIER_TOO_LONG = 'That identifier is too long.'
ADMIN_IDENTIFIER_IN_USE = 'Sorry, that identifier is already in use.'
ADMIN_LOGO_REQUIRED = 'You didn\'t enter a logo url.'
ADMIN_LOGO_INVALID = 'Url for logo must be of type gif, jpg, jpeg or png.'

# Signup error messages.
EMAIL_IN_USE = 'Sorry, that email is already in use.'

# Login error messages.
INVALID_LOGIN = 'The email address or password you entered is incorrect.'
NOT_BETA_TESTER = ('Sorry, you\'re not a beta tester. We\'ll email you when '
                   'we\'ve fixed all the bugs.')

# Authorization error messages
ACCESS_DENIED = 'Sorry, you are not authorized to view that page.'
