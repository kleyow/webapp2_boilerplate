import wtforms
from wtforms import validators


class FundingSourceForm(wtforms.Form):

  nickname = wtforms.TextField(validators=[validators.Optional()])
  card_token = wtforms.TextField(validators=[validators.Required()])
  card_last_four_digits = wtforms.TextField(
      validators=[validators.Length(min=4, max=4)])
  card_exp_month = wtforms.TextField(validators=[validators.Required()])
  card_exp_year = wtforms.TextField(validators=[validators.Required()])
