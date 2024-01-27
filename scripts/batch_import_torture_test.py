#!/usr/bin/env python

"""
Torture-test Afterglow batch import jobs
"""

import sys
import argparse
import requests
import base64
import json
import time
from multiprocessing import Event, Lock, Process
from typing import Dict, List, Union
import warnings


warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made')


def api_request(method: str, resource: str, args: argparse.Namespace, token: str | None = None, **data) \
        -> Union[Dict[str, dict], List[Dict[str, dict]]]:
    headers = {}

    if not token:
        token = args.token

    if token:
        headers['Authorization'] = 'Bearer {}'.format(args.token)

        if method != 'GET':
            # Extract CSRF token from access/refresh token
            # noinspection PyBroadException
            try:
                s = args.token[:args.token.rfind('.')]
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

        auth = None

    else:
        auth = args.user, args.password

    root = args.root
    if not root and args.host not in ('localhost', '127.0.0.1'):
        root = '/core'
    elif root and not root.startswith('/'):
        root = '/' + root
    url = 'http{}://{}:{:d}{}/'.format('s' if args.https else '', args.host, args.port, root)
    if not resource.startswith('oauth2') and not resource.startswith('ajax'):
        url += 'api/v{}/'.format(args.api_version)
    url += resource

    if method in ('GET', 'HEAD', 'OPTIONS'):
        params = data
        json_data = None
    else:
        # For requests other than GET, we must pass parameters as JSON
        params = None
        json_data = data

    r = requests.request(method, url, verify=False, params=params, headers=headers, json=json_data, auth=auth)

    try:
        content_type = r.headers['Content-Type'].split(';')[0].strip()
    except KeyError:
        pass
    else:
        if content_type.split('/')[-1].lower() == 'json':
            res = r.json()
            if res.get('error'):
                raise RuntimeError(res['error']['detail'])
            return res.get('data')
        if content_type.split('/')[0].lower() == 'text':
            raise RuntimeError(f'Unexpected response:\n{r.text}')
        raise RuntimeError(f'Unexpected response:\n{r.content}')


def test_process(args: argparse.Namespace, username: str, api_key: str, skynet: str, obs_ids: List[int],
                 terminate_event: Event, console_lock: Lock) -> None:
    """
    Test process body for the given user

    :param args: parsed command-line arguments
    :param username: impersonate the given user for API calls
    :param api_key: user's personal Afterglow API token
    :param skynet: Skynet data provider ID
    :param obs_ids: list of observation IDs
    """
    try:
        warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made')

        while not terminate_event.is_set():
            for obs_id in obs_ids:
                if terminate_event.is_set():
                    break

                # Submit batch import job
                prefix = f'{username}, obs {obs_id}:'
                job_id = None
                t0 = time.time()
                try:
                    job = api_request(
                        'POST', 'jobs', args, api_key, type='batch_import',
                        settings=[dict(provider_id=skynet, path=f'User Observations/{obs_id}/reduced')])
                    if job.get('detail'):
                        raise RuntimeError(job['detail'])
                    job_id = job['id']
                except Exception as e:
                    with console_lock:
                        print(f'{prefix} error submitting job [{e}]')
                else:
                    # Wait for job completion
                    while not terminate_event.is_set():
                        try:
                            state = api_request('GET', f'jobs/{job_id}/state', args, api_key)
                        except Exception as e:
                            with console_lock:
                                print(f'{prefix} error requesting job state [{e}]')
                        else:
                            if state['status'] == 'completed':
                                with console_lock:
                                    print(f'{prefix} finished in {time.time() - t0:.1f} s')
                                break
                finally:
                    # Clean up the user's Workbench from the imported images
                    if job_id is not None:
                        try:
                            result = api_request('GET', f'jobs/{job_id}/result', args, api_key)
                        except Exception as e:
                            with console_lock:
                                print(f'{prefix} error requesting file IDs [{e}]')
                        else:
                            if result['errors']:
                                with console_lock:
                                    print(f'{prefix} {"; ".join(result["errors"])}')
                            for file_id in result.get('file_ids', []):
                                # noinspection PyBroadException
                                try:
                                    api_request('DELETE', f'data-files/{file_id}', args, api_key)
                                except Exception:
                                    pass
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        with console_lock:
            print(f'{username}: error in test process [{e}]')


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        '--host', metavar='HOSTNAME', default='localhost', help='Afterglow API server hostname or IP address')
    # noinspection PyTypeChecker
    parser.add_argument('-o', '--port', metavar='PORT', type=int, default=5000, help='Afterglow API server port')
    parser.add_argument('-s', '--https', action='store_true', help='use HTTPS instead of HTTP')
    parser.add_argument('-r', '--root', default='', help='API root')
    parser.add_argument('-v', '--api-version', default='1', help='server API version')
    parser.add_argument('-u', '--user', help='authenticate with this username')
    parser.add_argument('-p', '--password', help='authenticate with this password')
    parser.add_argument('-t', '--token', help='authenticate with this personal token')
    parser.add_argument(
        'users', metavar='@USERFILE|-|USERNAME,USERNAME,...',
        help='usernames, comma-separated, list file, or read from console ("-")')
    parser.add_argument(
        'obs_ids', metavar='@OBSFILE|ID,ID,...', help='Skynet observation IDs, comma-separated or list file')

    args = parser.parse_args()

    # Read usernames and obs IDs from command line or file
    if args.users.startswith('@'):
        with open(args.users[1:], encoding='utf8') as f:
            usernames = ','.join(f.read().splitlines())
    elif args.users == '-':
        usernames = ','.join(sys.stdin.read().splitlines())
    else:
        usernames = args.users
    usernames = [s.strip() for s in usernames.split(',') if s.strip()]
    if not usernames:
        print('No usernames provided', file=sys.stderr)
        sys.exit(-1)
    if args.obs_ids.startswith('@'):
        with open(args.obs_ids[1:], encoding='utf8') as f:
            obs_ids = ','.join(f.read().splitlines())
    else:
        obs_ids = args.obs_ids
    obs_ids = [int(s) for s in obs_ids.split(',') if s.strip()]
    if not obs_ids:
        print('No observation IDs provided', file=sys.stderr)
        sys.exit(-2)

    # Retrieve user API tokens
    users = api_request('GET', 'users', args)
    unknown_users = [username for username in usernames if not any(u['username'] == username for u in users)]
    if unknown_users:
        print(f'Unknown username{"s" if len(unknown_users) > 1 else ""}: {", ".join(unknown_users)}')
    api_keys = {}
    for u in users:
        if u['username'] in usernames:
            keys = api_request('GET', f'users/{u["id"]}/tokens', args)
            if not keys:
                # User has no API token, create one
                keys = api_request(
                    'POST', f'users/{u["id"]}/tokens', args, note=f'Personal API token for {u["username"]}')
            if keys:
                api_keys[u['username']] = keys[0]

    print(f'Users: {", ".join(usernames)}')
    print(f'Observation IDs: {", ".join(str(obs_id) for obs_id in obs_ids)}')

    # Get Skynet data provider ID
    skynet = [p['id'] for p in api_request('GET', 'data-providers', args) if p['name'] == 'skynet_local'][0]

    # Run test in a separate process for each user
    terminate_event = Event()
    console_lock = Lock()
    processes = [
        Process(
            target=test_process,
            args=(args, username, api_keys[username], skynet, obs_ids, terminate_event, console_lock))
        for username in usernames
    ]
    try:
        print('Press Enter to terminate\n')
        for p in processes:
            p.start()
        try:
            input()
        except (KeyboardInterrupt, SystemExit):
            pass
        terminate_event.set()
    finally:
        for p in processes:
            p.join()


if __name__ == '__main__':
    main()
