import wtforms
from wtforms import validators

from forms import error_messages


class ErrorReportForm(wtforms.Form):

  name = wtforms.TextField(validators=[
      validators.Required(error_messages.NAME_REQUIRED)])

  email = wtforms.TextField(validators=[
      validators.Required(error_messages.EMAIL_REQUIRED),
      validators.Email(error_messages.INVALID_EMAIL)])

  message = wtforms.TextField(validators=[
      validators.Required(error_messages.MESSAGE_REQUIRED)])
