#!/usr/bin/env python

"""
Torture-test Afterglow Core API
"""

import argparse
import base64
import json
import random
import requests
import time
import traceback
import warnings
from multiprocessing import Process
from typing import Any, Dict, Optional, Union


def api_call(host, port, https, root, api_version, token, method, resource,
             params=None) -> Optional[Union[Dict[str, Any], str, bytes]]:
    method = method.upper()

    headers = {'Authorization': 'Bearer {}'.format(token)}

    if method != 'GET':
        # Extract CSRF token from access/refresh token
        # noinspection PyBroadException
        try:
            s = token[:token.rfind('.')]
            s = base64.decodebytes(s + '='*((4 - len(s) % 4) % 4))
            i = 1
            while i <= len(s):
                try:
                    json.loads(s[:i])
                except ValueError:
                    i += 1
                else:
                    break
            s = s[i:]
            i = 1
            while i <= len(s):
                try:
                    headers['X-CSRF-Token'] = json.loads(s[:i])['csrf']
                    break
                except ValueError:
                    i += 1
        except Exception:
            pass

    if not root and host not in ('localhost', '127.0.0.1'):
        root = '/core'
    elif root and not root.startswith('/'):
        root = '/' + root
    url = 'http{}://{}:{:d}{}/'.format('s' if https else '', host, port, root)
    if not resource.startswith('oauth2') and not resource.startswith('ajax'):
        url += 'api/v{}/'.format(api_version)
    url += resource

    json_data = None
    if method not in ('GET', 'HEAD', 'OPTIONS') and params:
        # For requests other than GET, we must pass parameters as JSON
        params, json_data = None, params

    warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made')
    r = requests.request(
        method, url, verify=False, params=params, headers=headers,
        json=json_data)

    try:
        content_type = r.headers['Content-Type'].split(';')[0].strip()
    except KeyError:
        return

    if content_type.split('/')[-1].lower() == 'json':
        res = r.json()
        if 'data' in res:
            return res['data']
        if 'error' in res:
            raise RuntimeError(str(res['error']))
        return res
    if content_type.split('/')[0].lower() == 'text':
        return r.text
    return r.content


def run_job(host, port, https, root, api_version, token, job_type, params):
    job_params = {'type': job_type}
    job_params.update(params)
    job_id = api_call(
        host, port, https, root, api_version, token, 'POST', 'jobs',
        job_params)['id']
    while True:
        time.sleep(1)
        if api_call(
                host, port, https, root, api_version, token, 'GET',
                'jobs/{}/state'.format(job_id))['status'] == 'completed':
            break
    res = api_call(
        host, port, https, root, api_version, token, 'GET',
        'jobs/{}/result'.format(job_id))
    if res['errors']:
        print(res['errors'])
    return res


def test_process(
        proc_id, host, port, https, root, api_version, token, obs_id, cycles):
    # Import observation
    while True:
        # noinspection PyBroadException
        try:
            file_ids = run_job(
                host, port, https, root, api_version, token, 'batch_import',
                {'settings': [{
                    'provider_id': '1', 'duplicates': 'append',
                    'path': 'User Observations/{}/reduced'.format(obs_id)
                }]})['file_ids']
        except Exception:
            time.sleep(5)
        else:
            if file_ids:
                break
            time.sleep(5)

    for cycle in range(cycles):
        # noinspection PyBroadException
        try:
            # Retrieve pixel data
            for i in file_ids:
                api_call(
                    host, port, https, root, api_version, token,
                    'GET', 'data-files/{}/pixels'.format(i))

            # Stack images
            time.sleep(random.uniform(0, 10))
            temp_file_id = run_job(
                host, port, https, root, api_version, token, 'stacking',
                {'file_ids': file_ids})['file_id']
            while True:
                # noinspection PyBroadException
                try:
                    api_call(
                        host, port, https, root, api_version, token,
                        'DELETE', 'data-files/{}'.format(temp_file_id))
                except Exception:
                    time.sleep(5)
                else:
                    break

            # Extract sources from the first image
            time.sleep(random.uniform(0, 10))
            sources = run_job(
                host, port, https, root, api_version, token,
                'source_extraction', {'file_ids': [file_ids[0]]})['data']

            # Photometer sources in all images
            time.sleep(random.uniform(0, 10))
            run_job(
                host, port, https, root, api_version, token, 'photometry',
                {'file_ids': file_ids, 'sources': sources, 'settings': {
                    'a': 10, 'a_in': 15, 'a_out': 20}})
        except Exception:
            traceback.print_exc()

        print('{}: {}'.format(proc_id + 1, cycle + 1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        '--host', metavar='HOSTNAME', default='localhost',
        help='Afterglow API server hostname or IP address')
    # noinspection PyTypeChecker
    parser.add_argument(
        '--port', metavar='PORT', type=int, default=5000,
        help='Afterglow API server port')
    parser.add_argument(
        '-s', '--https', action='store_true', help='use HTTPS instead of HTTP')
    parser.add_argument('-r', '--root', default='', help='API root')
    parser.add_argument(
        '-v', '--api-version', default='1', help='server API version')
    parser.add_argument(
        '-t', '--token', help='authenticate with this personal token')
    parser.add_argument(
        '-o', '--obs', metavar='N', help='test observation ID')
    parser.add_argument(
        '-w', '--workers', metavar='N', type=int, default=100,
        help='number of worker processes')
    parser.add_argument(
        '-c', '--cycles', metavar='N', type=int, default=100,
        help='number of test cycles')

    args = parser.parse_args()

    print('Starting {} processes with {} test cycles'
          .format(args.workers, args.cycles))
    processes = [Process(target=test_process, args=(
        i, args.host, args.port, args.https, args.root, args.api_version,
        args.token, args.obs, args.cycles)) for i in range(args.workers)]
    for p in processes:
        p.start()
    try:
        for p in processes:
            p.join()
    finally:
        # Cleanup
        data_files = api_call(
            args.host, args.port, args.https, args.root, args.api_version,
            args.token, 'GET', 'data-files')
        print('Deleting {} data files'.format(len(data_files)))
        for f in data_files:
            while True:
                # noinspection PyBroadException
                try:
                    # noinspection PyTypeChecker
                    api_call(
                        args.host, args.port, args.https, args.root,
                        args.api_version, args.token,
                        'DELETE', 'data-files/{}'.format(f['id']))
                except Exception:
                    time.sleep(1)
                else:
                    break
