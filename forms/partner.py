import wtforms
from wtforms import validators

from forms import error_messages


class PartnerForm(wtforms.Form):

  owner_name = wtforms.TextField(
      validators=[validators.Required(error_messages.NAME_REQUIRED)])

  organization_name = wtforms.TextField(
      validators=[validators.Required(error_messages.ORG_NAME_REQUIRED)])

  address = wtforms.TextField(
      validators=[validators.Required(error_messages.ORG_ADDRESS_REQUIRED)])

  email = wtforms.TextField(
      validators=[
          validators.Required(error_messages.EMAIL_REQUIRED),
          validators.Email(error_messages.INVALID_EMAIL)])

  phone_number = wtforms.TextField(validators=[validators.Optional()])
