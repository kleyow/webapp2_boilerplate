#!/usr/bin/env python

# Need to import and fix the sys path before importing other things.
import remote_api_shell
remote_api_shell.fix_sys_path()

import time

from google.appengine.api import datastore_admin
from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.tools import appengine_rpc


def configure_remote_api():
  def auth_func():
    return ('jenkins@jgxlabs.com', 'pyluojtwiazmklmq')

  remote_api_stub.ConfigureRemoteApi(
      'blaze-pay', '/_ah/remote_api', auth_func,
      servername='blaze-pay.appspot.com',
      save_cookies=True, secure=False,
      rpc_server_factory=appengine_rpc.HttpRpcServer)
  remote_api_stub.MaybeInvokeAuthentication()


def main():
  print 'Checking indexes...'

  configure_remote_api()

  interval = 10  # seconds.
  building = True

  while building:
    # Start with a fresh run: maybe we're done building?
    building = False

    for index in datastore_admin.GetIndices('s~blaze-pay'):
      # If any single index is building, we're not done.
      # Sleep for a bit and then this cycle should repeat.
      if not index.has_state() or index.state() != index.READ_WRITE:
        building = True
        print 'Indexes are still building... Waiting %s seconds.' % interval
        time.sleep(interval)
        break

  print 'All indexes are up to date.'


if __name__ == '__main__':
  main()
