#!/usr/bin/env python

"""
Afterglow Core administration
"""

from __future__ import absolute_import, division, print_function
import sys
import argparse
import requests
from pprint import PrettyPrinter


if __name__ == '__main__':
    pp = PrettyPrinter()
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:

{0} -n add username=admin@localhost password=python roles=admin
  - add Afterglow admin on initial setup (no login required); don't use HTTPS;
    new user gets ID = 1

{0} -u admin@localhost -p python add username=superuser@localhost password=ruby
 roles=admin,user
  - first admin adds one more admin (ID = 2) who can also access the rest
    of Afterglow

{0} -u superuser@localhost -p ruby update password=julia
  - second admin changes their password

{0} -u superuser@localhost -p julia -i 1 update active=0
  - second admin deactivates first admin

{0} -u superuser@localhost -p julia add username=user@localhost password=eiffel
 roles=user
  - second admin adds a normal user (ID = 3)

{0} -u superuser@localhost -p julia add username=user1@localhost password=r
 roles=user active=0
  - create one more (inactive) user (ID = 4)

{0} -u superuser@localhost -p julia list active=1 username=%@localhost
  - list all active user accounts with usernames ending with "@localhost"

{0} -u superuser@localhost -p julia -i 2 delete
  - this will fail because at least one active admin must remain in the system

{0} -u user@localhost -p eiffel get
  - user gets their account info, including ID and access token
'''.format(sys.argv[0]))

    parser.add_argument(
        '--host', metavar='HOSTNAME', default='localhost',
        help='Afterglow API server hostname or IP address')
    parser.add_argument(
        '-o', '--port', metavar='PORT', type=int, default=5000,
        help='Afterglow API server port')
    parser.add_argument(
        '-n', '--no-https', action='store_true', help='disable HTTPS')
    parser.add_argument(
        '-v', '--api-version', default='1.0', help='server API version')
    parser.add_argument(
        'command', metavar='CMD',
        choices=['list', 'get', 'add', 'update', 'delete'],
        help='admin command (list, get, add, update, or delete')
    parser.add_argument(
        '-u', '--user', help='authenticate with this username')
    parser.add_argument(
        '-p', '--password', help='authenticate with this password')
    parser.add_argument(
        '-t', '--auth-token', help='authenticate with this token')
    parser.add_argument(
        '-i', '--uid', type=int, default=0,
        help='get/update/delete this user ID (0 - get/update your own account)')
    parser.add_argument(
        'params', metavar='param=value', nargs='*',
        help='request-specific parameters: "username", "password", "active", '
        '"roles"')

    args = parser.parse_args()

    headers = {}
    if args.auth_token:
        headers['Authentication-Token'] = args.auth_token
    if args.user is not None:
        auth = args.user, args.password
    else:
        auth = None

    resource = 'admin/users'
    if args.command in ('get', 'update', 'delete'):
        if args.uid is None:
            print('Missing user ID', file=sys.stderr)
            sys.exit(1)
        resource += '/{:d}'.format(args.uid)

    method = {
        'list': 'GET', 'get': 'GET', 'add': 'POST', 'update': 'PUT',
        'delete': 'DELETE'}[args.command]
    params = dict([item.split('=') for item in args.params])
    url = '://{}:{:d}/api/v{}/{}'.format(
        args.host, args.port, args.api_version, resource)

    r = requests.request(
        method, 'http' + ('s' if not args.no_https else '') + url,
        params=params, headers=headers, auth=auth)

    success = r.status_code//100 == 2
    if success:
        if args.command == 'delete':
            print('Deleted user ID {:d}'.format(args.uid))
    else:
        print(
            'Error {:d} - {}'.format(
                r.status_code,
                getattr(requests.status_codes, '_codes').get(
                    r.status_code, '')[0].upper().replace('_', ' ')),
            file=sys.stderr)

    try:
        content_type = r.headers['Content-Type'].split(';')[0].strip()
    except KeyError:
        pass
    else:
        if content_type.split('/')[-1].lower() == 'json':
            j = r.json()
            if success:
                if args.command in ('list', 'get'):
                    if args.command == 'list':
                        users = j
                    else:
                        users = [j]
                    for i, user in enumerate(users):
                        print(('\n' if i else '') + '''User {0[username]}{1}:
  ID:       {0[id]:d}
  Created:  {2}
  Modified: {3}
  Roles:    {4}
  Token:    {0[token]}'''.format(
                            user, '' if user['active'] else ' (inactive)',
                            ' '.join(user['created_at'].split('T')),
                            ' '.join(user['modified_at'].split('T')),
                            ', '.join(role['name'] for role in user['roles'])
                            if user['roles'] else 'none'))
                elif args.command == 'add':
                    print('Added user {0[username]} (ID = {0[id]:d})'.format(j))
                elif args.command == 'update':
                    print('Updated user {0[username]} '
                          '(ID = {0[id]:d})'.format(j))
            else:
                try:
                    s = j.pop('exception') + ': '
                except (TypeError, IndexError, KeyError, AttributeError):
                    s = ''
                try:
                    s += '[{:d}] '.format(j.pop('subcode'))
                except (TypeError, IndexError, KeyError, AttributeError):
                    pass
                try:
                    s += j.pop('message')
                except (TypeError, IndexError, KeyError, AttributeError):
                    pass
                else:
                    print(s, file=sys.stderr)
                tb = j.pop('traceback', None)
                if tb:
                    print('\n' + tb, file=sys.stderr)
                if j:
                    PrettyPrinter(stream=sys.stderr).pprint(j)
        elif content_type.split('/')[0].lower() == 'text':
            print(r.text, file=sys.stdout if success else sys.stderr)
