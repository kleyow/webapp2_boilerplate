import decimal
import re

import wtforms
from wtforms import validators, ValidationError

from forms import error_messages
from models.profile import Profile


class AddOrganizationForm(wtforms.Form):

  name = wtforms.TextField(
      validators=[
          validators.Required(error_messages.ADMIN_ORG_NAME_REQUIRED)])

  owner = wtforms.TextField(
      validators=[
          validators.Required(error_messages.ADMIN_ORG_EMAIL_REQUIRED),
          validators.Email(error_messages.INVALID_EMAIL)])

  fee_percentage = wtforms.DecimalField(
      validators=[
          validators.Optional(),
          validators.NumberRange(
              message=error_messages.ADMIN_INVALID_FEE,
              min=0, max=100)])

  identifier = wtforms.TextField(
      validators=[
          validators.Required(error_messages.ADMIN_IDENTIFIER_REQUIRED),
          validators.Length(
              max=100, message=error_messages.ADMIN_IDENTIFIER_TOO_LONG)])

  logo_url = wtforms.TextField(
      validators=[
          validators.Required(error_messages.ADMIN_LOGO_REQUIRED),
          validators.Regexp(re.compile('^.+\.(gif|jpg|jpeg|png)$'),
                            message=error_messages.ADMIN_LOGO_INVALID)])

  def validate_owner(self, field):
    owner = Profile.get_by_email(field.data)
    if not owner:
      raise ValidationError(error_messages.ADMIN_ORG_OWNER_NOT_FOUND)

    field.data = owner

  def validate_fee_percentage(self, field):
    percentage = decimal.Decimal(field.data) / 100
    field.data = str(percentage)
