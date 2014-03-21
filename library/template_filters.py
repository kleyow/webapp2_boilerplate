from datetime import date
import re
from urllib import quote
from webapp2_extras import jinja2

from library import constants, time_helpers


evalcontextfilter = jinja2.jinja2.evalcontextfilter
Markup = jinja2.jinja2.Markup
escape = jinja2.jinja2.escape

__all__ = ['nl2br', 'qr_code', 'striphtmlentities', 'timestamp_to_datetime',
           'time_format', 'urlquote']


@evalcontextfilter
def nl2br(eval_ctx, value):
  """Turn text newline characters into HTML line breaks."""
  result = u'<br />\n'.join(escape(value).split('\n'))
  if eval_ctx.autoescape:
    result = Markup(result)
  return result


@evalcontextfilter
def qr_code(eval_ctx, value):
  # Use Google Charts API to generate a QR code to be displayed to
  # sender.
  result = ('https://chart.googleapis.com/chart'
            '?chs=350x350&cht=qr&chl=%s%s' %
            (constants.PUBLIC_HOST, value))

  if eval_ctx.autoescape:
    result = Markup(result)
  return result


@evalcontextfilter
def striphtmlentities(eval_ctx, value):
  result = re.sub('&.+?;', '', escape(value))
  if eval_ctx.autoescape:
    result = Markup(result)
  return result


@evalcontextfilter
def time_format(eval_ctx, value):
  result = time_helpers.format_time(value) or ''
  if eval_ctx.autoescape:
    result = Markup(result)
  return result


@evalcontextfilter
def timestamp_to_datetime(eval_ctx, value):
  try:
    result = date.fromtimestamp(value)
  except:
    result = None
  # Don't auto-escape this. We want the datetime object which is
  # guaranteed to be "safe" by definition.
  return result


@evalcontextfilter
def urlquote(eval_ctx, value):
  result = escape(quote(value))
  if eval_ctx.autoescape:
    result = Markup(result)
  return result
