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
import traceback
from datetime import datetime
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
        headers['Authorization'] = 'Bearer {}'.format(token)

        if method != 'GET':
            # Extract CSRF token from access/refresh token
            # noinspection PyBroadException
            try:
                s = token[:token.rfind('.')].encode('ascii')
                s = base64.decodebytes(s + b'='*((4 - len(s) % 4) % 4))
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

    r = requests.request(
        method, url, verify=False, params=params, headers=headers, json=json_data, auth=auth, timeout=(120, 120))

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


def test_process(args: argparse.Namespace, username: str, api_key: str, skynet: str, obs_paths: Dict[int, str],
                 terminate_event: Event, console_lock: Lock) -> None:
    """
    Test process body for the given user

    :param args: parsed command-line arguments
    :param username: impersonate the given user for API calls
    :param api_key: user's personal Afterglow API token
    :param skynet: Skynet data provider ID
    :param obs_paths: Skynet data provider asset paths for the observations indexed by obs IDs
    """
    try:
        warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made')

        while not terminate_event.is_set():
            for obs_id, obs_path in obs_paths.items():
                if terminate_event.is_set():
                    break

                # Submit batch import job
                time.sleep(1)
                prefix = f'{username}, obs {obs_id}:'
                t0 = time.time()
                try:
                    job = api_request(
                        'POST', 'jobs', args, api_key, type='batch_import',
                        settings=[dict(provider_id=skynet, path=obs_path)])
                    if job.get('detail'):
                        raise RuntimeError(job['detail'])
                    job_id = job['id']
                except Exception as e:
                    with console_lock:
                        print(f'{datetime.now().isoformat(" ")} {prefix} error submitting job [{e}]')
                else:
                    # Wait for job completion
                    while not terminate_event.is_set():
                        try:
                            state = api_request('GET', f'jobs/{job_id}/state', args, api_key)
                        except Exception as e:
                            with console_lock:
                                print(f'{datetime.now().isoformat(" ")} {prefix} error requesting job state [{e}]')
                        else:
                            if state['status'] == 'completed':
                                # Report job result
                                try:
                                    result = api_request('GET', f'jobs/{job_id}/result', args, api_key)
                                except Exception as e:
                                    with console_lock:
                                        print(f'{datetime.now().isoformat(" ")} {prefix} error requesting job result '
                                              f'[{e}]')
                                else:
                                    # Calculate job pickup time
                                    # noinspection PyBroadException
                                    try:
                                        try:
                                            t1 = datetime.strptime(state['created_on'], '%Y-%m-%d %H:%M:%S.%f')
                                        except ValueError:
                                            t1 = datetime.strptime(state['created_on'], '%Y-%m-%d %H:%M:%S')
                                        try:
                                            t2 = datetime.strptime(state['started_on'], '%Y-%m-%d %H:%M:%S.%f')
                                        except ValueError:
                                            t2 = datetime.strptime(state['started_on'], '%Y-%m-%d %H:%M:%S')
                                        pickup_time = f'; picked up in {(t2 - t1).total_seconds():.3f} s'
                                    except Exception:
                                        pickup_time = ''

                                    duration = f'Finished in {time.time() - t0:.1f} s{pickup_time}'
                                    with console_lock:
                                        if result.get('errors'):
                                            print(f'{datetime.now().isoformat(" ")} {prefix} '
                                                  f'{"; ".join(e["detail"] for e in result["errors"])}. {duration}')
                                        else:
                                            print(f'{datetime.now().isoformat(" ")} {prefix} {duration}')
                                break
                        time.sleep(1)
                finally:
                    # Clean up the user's Workbench
                    try:
                        result = api_request('GET', f'data-files', args, api_key)
                    except Exception as e:
                        with console_lock:
                            print(f'{datetime.now().isoformat(" ")} {prefix} error requesting data file IDs [{e}]')
                    else:
                        for df in result:
                            # noinspection PyBroadException
                            try:
                                api_request('DELETE', f'data-files/{df["id"]}', args, api_key)
                            except Exception:
                                pass
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        with console_lock:
            print(f'{datetime.now().isoformat(" ")} {username}: error in test process [{e}]')
            traceback.print_exc()


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
    parser.add_argument('-k', '--skynet-token', help='Skynet API access token')
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
    user_cache_filename = 'users@' + args.host
    # noinspection PyBroadException
    try:
        # Get user info from cache
        with open(user_cache_filename, encoding='utf8') as f:
            users = json.load(f)
    except Exception:
        users = {}
    if any(username not in users for username in usernames):
        try:
            all_users = api_request('GET', 'users', args)
        except Exception as e:
            print(f'Cannot retrieve user info from server [{e}]')
            sys.exit(-3)
        else:
            for u in all_users:
                if u['username'] in usernames and not u.get('api_token'):
                    # noinspection PyBroadException
                    try:
                        keys = api_request('GET', f'users/{u["id"]}/tokens', args)
                    except Exception:
                        keys = []
                    if not keys:
                        # User has no API token, create one
                        try:
                            keys = api_request(
                                'POST', f'users/{u["id"]}/tokens', args,
                                note=f'Personal API token for {u["username"]}')
                        except Exception as e:
                            print(f'Cannot obtain API token for user {u["username"]} [{e}]')
                    if keys:
                        u['api_token'] = keys[0]['access_token']
                    else:
                        print(f'Cannot obtain API token for user {u["username"]}')
                if u.get('api_token'):
                    users[u['username']] = u
            if users:
                with open(user_cache_filename, 'w', encoding='utf8') as f:
                    json.dump(users, f)
    unknown_users = [username for username in usernames if username not in users]
    if unknown_users:
        print(f'Unknown username{"s" if len(unknown_users) > 1 else ""}: {", ".join(unknown_users)}')
        sys.exit(-5)
    api_keys = {username: users[username]['api_token'] for username in usernames}

    print(f'User{"s" if len(usernames) > 1 else ""}: {", ".join(usernames)}')
    print(f'Observation ID{"s" if len(obs_ids) > 1 else ""}: {", ".join(str(obs_id) for obs_id in obs_ids)}')

    # Get obs groups/usernames via Skynet API
    obs_paths = {}
    headers = {'Authentication-Token': args.skynet_token}
    for obs_id in obs_ids:
        try:
            r = requests.get(f'https://api.skynet.unc.edu/2.0/obs/{obs_id}', headers=headers, verify=False)
            if r.status_code != 200:
                raise RuntimeError(r.text)
            obs = r.json()
        except Exception as e:
            print(f'Cannot retrieve observation {obs_id} [{e}]')
            sys.exit(-6)

        if obs.get('group'):
            path = f'Group Observations/{obs["group"]["name"]}/{obs["user"]["username"]}/{obs_id}/reduced'
        else:
            path = f'User Observations/{obs_id}/reduced'
        obs_paths[obs_id] = path

    # Get Skynet data provider ID
    skynet = [p['id'] for p in api_request('GET', 'data-providers', args) if p['name'] == 'skynet_local'][0]

    # Run test in a separate process for each user
    terminate_event = Event()
    console_lock = Lock()
    processes = [
        Process(
            target=test_process,
            args=(args, username, api_keys[username], skynet, obs_paths, terminate_event, console_lock))
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

        # Clean up all users' Workbenches
        for api_key in api_keys:
            # noinspection PyBroadException
            try:
                result = api_request('GET', f'data-files', args, api_key)
            except Exception:
                pass
            else:
                for df in result:
                    # noinspection PyBroadException
                    try:
                        api_request('DELETE', f'data-files/{df["id"]}', args, api_key)
                    except Exception:
                        pass


if __name__ == '__main__':
    main()
