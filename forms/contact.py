import wtforms
from wtforms import validators

from forms import error_messages


class ContactForm(wtforms.Form):

  name = wtforms.TextField(
      validators=[validators.Required(error_messages.NAME_REQUIRED)])

  email = wtforms.TextField(
      validators=[
          validators.Required(error_messages.EMAIL_REQUIRED),
          validators.Email(error_messages.INVALID_EMAIL)])

  topic = wtforms.TextField(
      validators=[validators.Required(error_messages.TOPIC_REQUIRED)])

  message = wtforms.TextAreaField(
      validators=[validators.Required(error_messages.MESSAGE_REQUIRED)])
