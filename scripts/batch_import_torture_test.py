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
import warnings


warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made')


def api_request(method: str, resource: str, args: argparse.Namespace, token: str | None = None, **data) \
        -> dict[str, dict] | list[dict[str, dict]] | str | bytes:
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
            return r.text
        return r.content


def test_process(args: argparse.Namespace, username: str, api_key: str, obs_paths: list[str, str],
                 terminate_event: Event, console_lock: Lock) -> None:
    """
    Test process body for the given user

    :param args: parsed command-line arguments
    :param username: impersonate the given user for API calls
    :param api_key: user's personal Afterglow API token
    :param obs_paths: list of pairs (provider_id, path)
    :param terminate_event: event set when
    """
    try:
        warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made')

        ts = args.tile_size
        cycle = 0
        while cycle < args.num_cycles and not terminate_event.is_set():
            cycle += 1
            for job_no, (provider_id, obs_path) in enumerate(obs_paths):
                prefix = (
                    f'{username}, cycle {cycle}{f"/{args.num_cycles}" if args.num_cycles else ""}, '
                    f'job {job_no + 1}/{len(obs_paths)}:'
                )

                if terminate_event.is_set():
                    break

                # Submit batch import job
                time.sleep(1)
                result = {}
                t0 = time.time()
                try:
                    job = api_request(
                        'POST', 'jobs', args, api_key, type='batch_import',
                        settings=[dict(provider_id=provider_id, path=obs_path, duplicates='append')])
                    if job.get('detail'):
                        raise RuntimeError(job['detail'])
                    job_id = job['id']
                except Exception as e:
                    with console_lock:
                        print(f'{datetime.now().isoformat(" ")} {prefix} error submitting job [{e}]')
                else:
                    # Wait for job completion
                    msg = ''
                    while not terminate_event.is_set():
                        try:
                            state = api_request('GET', f'jobs/{job_id}/state', args, api_key)
                        except Exception as e:
                            msg = f'error requesting job state [{e}]'
                        else:
                            if state['status'] == 'completed':
                                # Report job result
                                try:
                                    result = api_request('GET', f'jobs/{job_id}/result', args, api_key)
                                except Exception as e:
                                    msg = f'error requesting job result [{e}]'
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
                                        msg = f'job pick-up {int(round((t2 - t1).total_seconds()))} s, '
                                    except Exception:
                                        msg = ''

                                    msg += f'completion {time.time() - t0:.1f} s'
                                    if result.get('errors'):
                                        msg += '; ' + '; '.join(e['detail'] for e in result['errors'])
                                break
                        time.sleep(1)

                    if ts and result.get('file_ids'):
                        # Retrieve pixel data
                        if msg:
                            msg += '; '
                        t0 = time.time()
                        for file_id in result['file_ids']:
                            try:
                                # Get image size
                                df = api_request('GET', f'data-files/{file_id}', args, api_key)
                            except Exception as e:
                                msg += f'error requesting data file info [{e}]; '
                            else:
                                w, h = df.get('width') or 0, df.get('height') or 0
                                if w <= 0 or h <= 0:
                                    msg += 'empty data file; '
                                else:
                                    for y in range(0, h, ts):
                                        for x in range(0, w, ts):
                                            try:
                                                api_request(
                                                    'GET', f'data-files/{file_id}/pixels', args, api_key,
                                                    x=x + 1, y=y + 1, width=min(ts, w - x), height=min(ts, h - y))
                                            except Exception as e:
                                                msg += f'error retrieving pixel data [{e}]; '
                        msg += f'pixels {time.time() - t0:.1f} s'
                    with console_lock:
                        print(f'{datetime.now().isoformat(" ")} {prefix} {msg}')
                finally:
                    # Remove the newly imported images
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
            print(f'{datetime.now().isoformat(" ")} {username}: error in test process [{e}]')
            traceback.print_exc()


def cleanup_workbenches(args: argparse.Namespace, api_keys) -> None:
    """
    Clean up the given users' Workbenches
    """
    print('Cleaning up Workbenches')
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
        '-n', '--num-cycles', metavar='N', type=int, default=0, help='number of test cycles; 0 = infinite')
    parser.add_argument(
        '-z', '--tile-size', metavar='PIXELS', type=int, default=1024,
        help='image tile size; 0 = don\'t download pixel data after import')
    parser.add_argument(
        '-c', '--cleanup-only', action='store_true', help='don\'t run tests, only clean up users\' data files')
    parser.add_argument(
        'users', metavar='@USERFILE|-|USERNAME[*n],USERNAME[*n],...',
        help='usernames with optional repeats, comma-separated, list file, or read from console ("-")')
    parser.add_argument(
        'obs', metavar='@OBSFILE|{ID|PROVIDER:PATH,...}', nargs='?', default='',
        help='Skynet observation IDs or provider:path pairs, comma-separated or list file')

    args = parser.parse_args()

    # Read usernames from command line or file
    if args.users.startswith('@'):
        with open(args.users[1:], encoding='utf8') as f:
            usernames = ','.join(f.read().splitlines())
    elif args.users == '-':
        usernames = ','.join(sys.stdin.read().splitlines())
    else:
        usernames = args.users
    initial_usernames = usernames.split(',')
    usernames = {}
    for s in initial_usernames:
        s = s.strip()
        if not s:
            continue
        if '*' in s:
            # Handle repeats
            s, repeats = s.rsplit('*')
            repeats = int(repeats)
        else:
            repeats = 1
        try:
            usernames[s] += repeats
        except KeyError:
            usernames[s] = repeats
    if not usernames:
        print('No usernames provided', file=sys.stderr)
        sys.exit(-1)
    test_usernames = []
    for username, repeats in usernames.items():
        if repeats == 1:
            test_usernames.append(username)
        else:
            for i in range(1, repeats + 1):
                test_usernames.append(f'{username}#{i}')

    # Read job parameters from command line or file
    if args.cleanup_only:
        obs_paths = []
    else:
        if args.obs.startswith('@'):
            with open(args.obs[1:], encoding='utf8') as f:
                obs_specs = ','.join(f.read().splitlines())
        else:
            obs_specs = args.obs
        obs_paths = []
        for spec in obs_specs.split(','):
            spec = spec.strip()
            if not spec:
                continue
            if ':' in spec:
                provider, path = spec.split(':')
            else:
                provider, path = 'skynet_local', spec
            obs_paths.append((provider, path))
        if not obs_paths and not args.cleanup_only:
            print('No observation IDs/paths provided', file=sys.stderr)
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

    print(
        f'User{"s" if len(usernames) > 1 else ""}:',
        ', '.join(username if repeats == 1 else f'{username}*{repeats}' for username, repeats in usernames.items()))
    if args.cleanup_only:
        cleanup_workbenches(args, api_keys.values())
        return

    # Translate Skynet obs IDs to full asset paths
    obs_cache_filename = 'obs.cache'
    # noinspection PyBroadException
    try:
        # Get user info from cache
        with open(obs_cache_filename, encoding='utf8') as f:
            obs_cache = json.load(f)
    except Exception:
        obs_cache = {}
    headers = {'Authentication-Token': args.skynet_token}
    paths_added = False
    for i, (provider, path) in enumerate(obs_paths):
        if provider != 'skynet_local':
            continue

        try:
            obs_id = int(path)
        except ValueError:
            continue

        try:
            path = obs_cache[str(obs_id)]
        except KeyError:
            try:
                r = requests.get(f'https://api.skynet.unc.edu/2.0/obs/{obs_id}', headers=headers, verify=False)
                if r.status_code != 200:
                    raise RuntimeError(r.text)
                obs = r.json()
            except Exception as e:
                print(f'Cannot retrieve observation {obs_id} [{e}]')
                sys.exit(-6)

            if obs.get('group'):
                if obs.get('collab'):
                    path = f'Collaboration Observations/{obs["collab"]["name"]}/{obs["group"]["name"]}/' \
                        f'{obs["user"]["username"]}/{obs_id}/reduced'
                else:
                    path = f'Group Observations/{obs["group"]["name"]}/{obs["user"]["username"]}/{obs_id}/reduced'
            else:
                path = f'User Observations/{obs_id}/reduced'
            obs_cache[str(obs_id)] = path
            paths_added = True

        obs_paths[i] = (provider, path)

    if paths_added:
        with open(obs_cache_filename, 'w', encoding='utf8') as f:
            json.dump(obs_cache, f)

    # Get data provider IDs
    provider_ids = {}
    for p in api_request('GET', 'data-providers', args):
        # Allow referencing data providers by name or ID if ambiguous
        provider_ids[p['name']] = provider_ids[str(p['id'])] = p['id']
    for i, (provider, path) in enumerate(obs_paths):
        obs_paths[i] = (provider_ids[provider], path)

    # Run test in a separate process for each user
    terminate_event = Event()
    console_lock = Lock()
    processes = [
        Process(
            target=test_process,
            args=(args, username, api_keys[username if '#' not in username else username[:username.index('#')]],
                  obs_paths, terminate_event, console_lock)
        )
        for username in test_usernames
    ]
    print('Press Ctrl-C to terminate\n')
    for p in processes:
        p.start()
    try:
        while processes:
            time.sleep(0.1)
            i = 0
            while i < len(processes):
                p = processes[i]
                if p.is_alive():
                    i += 1
                else:
                    p.join()
                    del processes[i]
        print('All test processes finished')
    except (KeyboardInterrupt, SystemExit):
        print('Terminating')
        terminate_event.set()
    finally:
        for p in processes:
            p.join()

        cleanup_workbenches(args, api_keys.values())


if __name__ == '__main__':
    main()
