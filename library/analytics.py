class Analytics(object):

  FLASH_KEY = 'analytics'

  def __init__(self, request_handler):
    self.request_handler = request_handler
    self.session = self.request_handler.session

  def track_event(self, category, action):
    self.session.add_flash(key=self.FLASH_KEY, value=(category, action))

  def get_events(self):
    for (category, action), _ in self.session.get_flashes(key=self.FLASH_KEY):
      yield (category, action)
