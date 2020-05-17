#!/usr/bin/env python

"""
Run Afterglow Core API commands
"""

from __future__ import absolute_import, division, print_function
import sys
import argparse
import requests
import json
from io import BytesIO
from gzip import GzipFile
from pprint import PrettyPrinter
import warnings


if __name__ == '__main__':
    pp = PrettyPrinter()
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        '--host', metavar='HOSTNAME', default='localhost',
        help='Afterglow API server hostname or IP address')
    # noinspection PyTypeChecker
    parser.add_argument(
        '-o', '--port', metavar='PORT', type=int, default=5000,
        help='Afterglow API server port')
    parser.add_argument(
        '-s', '--https', action='store_true', help='use HTTPS instead of HTTP')
    parser.add_argument(
        '-v', '--api-version', default='1', help='server API version')
    parser.add_argument(
        'method', metavar='METHOD',
        help='request method (GET, POST, PUT, DELETE)')
    parser.add_argument(
        'resource', metavar='RESOURCE/NAME',
        help='resource name (not including the /api root), e.g. '
        'data-providers/0/assets')
    parser.add_argument(
        'params', metavar='param=value', nargs='*',
        help='request parameters')
    parser.add_argument('-a', '--accept', help='HTTP Accept header')
    parser.add_argument('-e', '--encoding', help='HTTP Accept-Encoding header')
    parser.add_argument(
        '-u', '--user', help='authenticate with this username')
    parser.add_argument(
        '-p', '--password', help='authenticate with this password')
    parser.add_argument(
        '-t', '--token', help='authenticate with this personal token')
    parser.add_argument(
        '-b', '--body', help='request body (- = get from stdin)')
    parser.add_argument(
        '-z', '--gzip', action='store_true', help='request body is gzipped')

    args = parser.parse_args()

    headers = {}
    if args.accept is not None:
        headers['Accept'] = args.accept
    if args.encoding is not None:
        headers['Accept-Encoding'] = args.encoding
    if args.gzip:
        headers['Content-Encoding'] = 'gzip'
    if args.token:
        headers['Authorization'] = 'Bearer {}'.format(args.token)

        if args.method != 'GET':
            # Extract CSRF token from access/refresh token
            # noinspection PyBroadException
            try:
                import base64
                import json
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
    if args.user is not None:
        auth = args.user, args.password
    else:
        auth = None

    data = args.body
    if data is not None:
        if data == '-':
            data = sys.stdin.read()

        try:
            json.loads(data)
        except ValueError:
            pass
        else:
            headers['Content-Type'] = 'application/json'

        if args.body != '-' and args.gzip:
            s = BytesIO()
            with GzipFile(fileobj=s, mode='wb') as f:
                f.write(data)
            data = s.getvalue()

    url = 'http{}://{}:{:d}/'.format(
        's' if args.https else '', args.host, args.port)
    if args.resource not in ('users/login', 'users/logout', 'users/tokens'):
        url += 'api/v{}/'.format(args.api_version)
    url += args.resource
    print('\n{} {}'.format(args.method, url), file=sys.stderr)
    if headers:
        print('\n'.join('{}: {}'.format(h, v) for h, v in headers.items()),
              file=sys.stderr)
    if data and headers.get('Content-Type') == 'application/json':
        print(data, file=sys.stderr)

    warnings.filterwarnings('ignore', 'Unverified HTTPS request is being made')
    r = requests.request(
        args.method, url, verify=False,
        params=dict([item.split('=', 1) for item in args.params]),
        headers=headers, data=data, auth=auth)

    print('\nHTTP {:d} - {}'.format(
        r.status_code,
        getattr(requests.status_codes, '_codes').get(
            r.status_code, '')[0].upper().replace('_', ' ')), file=sys.stderr)

    try:
        print('Content-Type: {}'.format(r.headers['Content-Type']),
              file=sys.stderr)
        content_type = r.headers['Content-Type'].split(';')[0].strip()
    except KeyError:
        pass
    else:
        if content_type.split('/')[-1].lower() == 'json':
            # Got a JSON, print structure with indents
            pp.pprint(r.json())
        elif content_type.split('/')[0].lower() == 'text':
            # text/*, print as is
            print(r.text)
        else:
            # Binary data, print as is as well, could be then redirected to
            # a file
            try:
                print('Content-Length: {}'.format(r.headers['Content-Length']),
                      file=sys.stderr)
            except KeyError:
                pass
            try:
                print('Content-Encoding: {}'.format(
                    r.headers['Content-Encoding']), file=sys.stderr)
            except KeyError:
                pass
            print(r.content)
