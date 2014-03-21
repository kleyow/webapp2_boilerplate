import wtforms
from wtforms import validators

from forms import error_messages


class OrganizationEditForm(wtforms.Form):

  name = wtforms.TextField(
      validators=[validators.Required(error_messages.ORG_NAME_REQUIRED)])
