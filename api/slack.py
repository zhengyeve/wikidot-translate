#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import logging
import json
import os
import time
import traceback

from functools import wraps

LOG = logging.getLogger(__name__)


class SlackWebHook(object):

    WEBHOOK_URL = 'INSERT_YOUR_SLACK_WEBHOOK_URL_HERE'

    @staticmethod
    def post_message(data, channel=None, username=None, icon_emoji=None, data_fallback={}):

        if channel:
            data['channel'] = channel
        if username:
            data['username'] = username
        if icon_emoji:
            data['icon_emoji'] = icon_emoji

        try:
            json_payload = json.dumps(data)
        except Exception as e:
            LOG.exception('{} - Can not dump data: {}'.format(e, data))
            data.update(data_fallback)
            json_payload = json.dumps(data)

        try:
            r = requests.post(url=SlackWebHook.WEBHOOK_URL, data={"payload": json_payload})
            r.raise_for_status()
        except requests.HTTPError as e:
            LOG.exception("{} Error:{} Data: {}".format("Unable to make a connection with slack.", e, data))
        except Exception as e:
            LOG.exception("{} Error:{} Data: {}".format("Unable to send messages to slack.", e, data))

        # do not overwhelm channel
        time.sleep(0.2)


# notification wrapper
def notify_status(job_name='test-job-name', channel='_status_', icon_emoji=':loudspeaker:'):
    def decorator(func):

        def wrapper(*args, **kwargs):
            ts = time.time()
            # text_start = '{} started ..'.format(job_name)
            # SlackWebHook.post_message(data={'text': text_start},
            #                           username=job_name, channel=channel, icon_emoji=icon_emoji)
            result = {}
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                result['err'] = 'ERROR! {}\n{}\n'.format(e, traceback.format_exc())
            finally:
                t = time.time() - ts
                result_log = ''
                if result:
                    result_log = result.get('err', result.get('log', result.get('log_text', '')))
                    if result.get('log_text_lines', []):
                        result_log = '\n'.join(result['log_text_lines'])
                    print(result_log)

                text_end = '[{}] {}\n----\n{}\n----\nTook: {:.2f} secs\n'.format(
                    os.getenv('ENV', 'local'), job_name,
                    result_log,
                    t)
                SlackWebHook.post_message(data={'text': text_end},
                                          username=job_name, channel=channel, icon_emoji=icon_emoji)
            return result

        return wraps(func)(wrapper)

    return decorator