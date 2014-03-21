import re

import wtforms
from wtforms import validators

from forms import error_messages


class StaffForm(wtforms.Form):

  password = wtforms.PasswordField(
      validators=[validators.Required(error_messages.PASSWORD_REQUIRED)])

  pin = wtforms.TextField(
      validators=[validators.Required(error_messages.PIN_INVALID),
                  validators.Regexp('\d{4}',
                                    message=error_messages.PIN_INVALID)])


class AddStaffForm(wtforms.Form):

  name = wtforms.TextField(
      validators=[
          validators.Required(error_messages.STAFF_NAME_REQUIRED),
          validators.Length(message=error_messages.STAFF_NAME_TOO_LONG,
                            max=30)])

  username = wtforms.TextField(
      validators=[
          validators.Required(error_messages.STAFF_USERNAME_REQUIRED),
          validators.Length(message=error_messages.STAFF_USERNAME_TOO_LONG,
                            max=20),
          validators.Regexp(re.compile('^[a-zA-Z0-9]+$'),
                            message=error_messages.STAFF_ALPHANUMERIC_ONLY)])
