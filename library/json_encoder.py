import datetime
import time

from google.appengine.ext import db


def serialize_model(obj):
  """Acts as an adapter for serializing db.Model objects into JSON.
  Python's JSON serializer can't handle datetime.datetime objects, which
  causes a problem when serializing google.appengine.ext.db.DateTimeProperty
  fields correctly.
  To remedy this, we simply store it as a UNIX timestamp.
  The JSON serializer is also unable to serialize
  google.appengine.ext.db.ReferenceProperty fields, as they are stored as a
  google.appengine.ext.db.Key.
  To make the ReferenceProperty fields JSON serializable, we simply convert
  them into a string.
  """

  if isinstance(obj, datetime.datetime):
    return int(time.mktime(obj.timetuple()))

  elif isinstance(obj, db.Key):
    return str(obj)

  else:
    raise TypeError(
        'Object of type %s with value %s is not JSON serializeable' %
        (type(obj), repr(obj)))
