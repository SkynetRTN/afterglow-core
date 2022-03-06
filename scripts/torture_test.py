#!/usr/bin/env python

"""
Torture-test Afterglow Core API
"""

import argparse
import base64
import json
import requests
import time
import traceback
import warnings
from multiprocessing import Process
from typing import Dict, Optional, Union


def api_call(host, port, https, root, api_version, token, method, resource,
             params=None) -> Optional[Union[Dict[str, dict], str, bytes]]:
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
        return r.json()
    if content_type.split('/')[0].lower() == 'text':
        return r.text
    return r.content


def run_job(host, port, https, root, api_version, token, job_type, params):
    job_params = {'type': job_type}
    job_params.update(params)
    job_id = api_call(
        host, port, https, root, api_version, token, 'POST', 'jobs',
        job_params)['data']['id']
    while True:
        time.sleep(1)
        if api_call(
                host, port, https, root, api_version, token, 'GET',
                'jobs/{}/state'.format(job_id))['data']['status'] == \
                'completed':
            break
    res = api_call(
        host, port, https, root, api_version, token, 'GET',
        'jobs/{}/result'.format(job_id))['data']
    if res['errors']:
        raise RuntimeError(str(res['errors']))
    return res


def test_process(
        proc_id, host, port, https, root, api_version, token, obs_id, cycles):
    # noinspection PyBroadException
    try:
        for cycle in range(cycles):
            # Import observation
            file_ids = run_job(
                host, port, https, root, api_version, token, 'batch_import',
                {'settings': [{
                    'provider_id': '1',
                    'path': 'User Observations/{}/reduced'.format(obs_id)
                }]})['file_ids']
            try:
                # Retrieve pixel data
                for i in file_ids:
                    api_call(
                        host, port, https, root, api_version, token,
                        'GET', 'data-files/{}/pixels'.format(i))

                # Stack images
                file_ids.append(run_job(
                    host, port, https, root, api_version, token, 'stacking',
                    {'file_ids': file_ids})['file_id'])

                # Extract sources from the first image
                sources = run_job(
                    host, port, https, root, api_version, token,
                    'source_extraction', {'file_ids': [file_ids[0]]})['data']

                # Photometer sources in all images
                run_job(
                    host, port, https, root, api_version, token, 'photometry',
                    {'file_ids': file_ids, 'sources': sources, 'settings': {
                        'a': 10, 'a_in': 15, 'a_out': 20}})
            finally:
                # Cleanup
                for i in file_ids:
                    # noinspection PyBroadException
                    try:
                        api_call(
                            host, port, https, root, api_version, token,
                            'DELETE', 'data-files/{}'.format(i))
                    except Exception:
                        pass
                print('{}: {}'.format(proc_id + 1, cycle + 1))
    except Exception:
        traceback.print_exc()


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
    for p in processes:
        p.join()
