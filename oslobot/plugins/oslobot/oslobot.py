#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import absolute_import
from __future__ import unicode_literals

import collections
import copy
from datetime import date
import json
import re

from concurrent import futures
import six
from six.moves import http_client

from dateutil import parser
from dateutil.relativedelta import relativedelta

import feedparser
from oslo_utils import timeutils
import requests
from six.moves.urllib.parse import urlencode as compat_urlencode
from tabulate import tabulate

from errbot import botcmd
from errbot import BotPlugin

BAD_VALUE = '??'
NA_VALUE = "N/A"


def str_split(text):
    return text.split()


class GoogleShortener(object):
    """Shortener that uses google shortening service (requires api key).

    See: https://developers.google.com/url-shortener/v1/
    """

    base_request_url = 'https://www.googleapis.com/urlshortener/v1/url?'

    def __init__(self, log, api_key,
                 timeout=None, cache=None):
        self.log = log
        self.api_key = api_key
        self.timeout = timeout
        if cache is None:
            cache = {}
        self.cache = cache

    def safe_shorten(self, long_url):
        try:
            return self.shorten(long_url)
        except (IOError, ValueError, TypeError):
            self.log.exception("Failed shortening due to unexpected error, "
                               " providing back long url.")
            return long_url

    def shorten(self, long_url):
        if long_url in self.cache:
            return self.cache[long_url]
        post_data = json.dumps({
            'longUrl': long_url,
        })
        query_params = {
            'key': self.api_key,
        }
        req_url = self.base_request_url + compat_urlencode(query_params)
        try:
            req = requests.post(req_url, data=post_data,
                                headers={'content-type': 'application/json'},
                                timeout=self.timeout)
        except requests.Timeout:
            raise IOError("Unable to shorten '%s' url"
                          " due to http request timeout being"
                          " reached" % (long_url))
        else:
            if req.status_code != http_client.OK:
                raise IOError("Unable to shorten '%s' url due to http"
                              " error '%s' (%s)" % (long_url, req.reason,
                                                    req.status_code))
            try:
                small_url = req.json()['id']
                self.cache[long_url] = small_url
                return small_url
            except (KeyError, ValueError, TypeError) as e:
                raise IOError("Unable to shorten '%s' url due to request"
                              " extraction error: %s" % (long_url, e))


class OsloBotPlugin(BotPlugin):
    OS_START_YEAR = 2010
    DEF_FETCH_WORKERS = 3
    DEF_CONFIG = {
        # Check periodic jobs every 24 hours (by default); the jobs
        # currently run daily, so running it quicker isn't to useful...
        #
        # If it is negative or zero, then that means never do it...
        'periodic_check_frequency': -1,
        'periodic_python_versions': [(3, 4), (2, 7)],
        # TODO(harlowja): fetch this from the webpage itself?
        'periodic_project_names': [
            'ceilometer',
            'cinder',
            'cue',
            'glance',
            'heat',
            'ironic',
            'keystone',
            'murano',
            'neutron',
            'nova',
            'octavia',
            'trove',
        ],
        'periodic_shorten': False,
        'periodic_build_name_tpl': ('periodic-%(project_name)s-%(py_version)s'
                                    '-with-oslo-master'),
        # Fetch timeout for trying to get a projects health rss
        # url (seems like this needs to be somewhat high as the
        # infra system that gets this seems to not always be healthy).
        'periodic_fetch_timeout': 30.0,
        'periodic_connect_timeout': 1.0,
        'periodic_url_tpl': ("http://health.openstack.org/runs/key/"
                             "build_name/%(build_name)s/recent/rss"),
        # See: https://pypi.python.org/pypi/tabulate
        'tabulate_format': 'plain',
        'periodic_exclude_when': {
            # Exclude failure results that are more than X months old...
            #
            # See: https://dateutil.readthedocs.io/en/stable/relativedelta.html
            'months': -1,
        },
        'meeting_team': 'oslo',
        'meeting_url_tpl': ("http://eavesdrop.openstack.org"
                            "/meetings/%(team)s/%(year)s/"),
        'meeting_fetch_timeout': 10.0,
        # Required if shortening is enabled, see,
        # https://developers.google.com/url-shortener/v1/getting_started#APIKey
        'shortener_api_key': "",
        'shortener_fetch_timeout': 5.0,
        'shortener_connect_timeout': 1.0,
    }
    """
    The configuration mechanism for errbot is sorta unique so
    check over
    http://errbot.io/en/latest/user_guide/administration.html#configuration
    before diving to deep here.
    """

    def configure(self, configuration):
        if not configuration:
            configuration = {}
        configuration.update(copy.deepcopy(self.DEF_CONFIG))
        super(OsloBotPlugin, self).configure(configuration)
        self.log.debug("Bot configuration: %s", self.config)
        self.executor = None

    @botcmd(split_args_with=str_split, historize=False)
    def meeting_notes(self, msg, args):
        """Returns the latest project meeting notes url."""
        def extract_meeting_url(team, meeting_url, resp):
            if resp.status_code != http_client.OK:
                return None
            matches = []
            # Crappy html parsing...
            for m in re.findall("(%s.+?[.]html)" % team, resp.text):
                if m.endswith(".log.html"):
                    continue
                if m not in matches:
                    matches.append(m)
            if matches:
                return meeting_url + matches[-1]
            return None
        self.log.debug("Got request to fetch url"
                       " to last meeting notes from '%s'"
                       " with args %s'", msg.frm, args)
        now_year = date.today().year
        if args:
            meeting_url_data = {
                'team': args[0],
            }
        else:
            meeting_url_data = {
                'team': self.config['meeting_team'],
            }
        # No meeting should happen before openstack even existed...
        valid_meeting_url = None
        while now_year >= self.OS_START_YEAR:
            meeting_url_data['year'] = now_year
            meeting_url = self.config['meeting_url_tpl'] % meeting_url_data
            try:
                resp = requests.get(
                    meeting_url, timeout=self.config['meeting_fetch_timeout'])
            except requests.Timeout:
                # Bail immediately...
                break
            else:
                valid_meeting_url = extract_meeting_url(
                    meeting_url_data['team'], meeting_url, resp)
                if valid_meeting_url:
                    self.log.debug("Found valid last meeting url at %s for"
                                   " team %s", valid_meeting_url,
                                   meeting_url_data['team'])
                    break
                else:
                    now_year -= 1
        if valid_meeting_url:
            content = "Last meeting url is %s" % valid_meeting_url
        else:
            content = ("Could not find meeting"
                       " url for project %s" % meeting_url_data['team'])
        self.send_public_or_private(msg, content, 'meeting notes')

    def send_public_or_private(self, source_msg, content, kind):
        if hasattr(source_msg.frm, 'room') and source_msg.is_group:
            self.send(source_msg.frm.room, content)
        elif source_msg.is_direct:
            self.send(source_msg.frm, content)
        else:
            self.log.warn("No recipient targeted for %s request!", kind)

    @botcmd(split_args_with=str_split, historize=False)
    def check_periodics(self, msg, args):
        """Returns current periodic job(s) status."""
        self.log.debug("Got request to check periodic"
                       " jobs from '%s' with args %s'", msg.frm, args)
        self.send_public_or_private(
            msg, self.fetch_periodics_table(project_names=args), 'check')

    def report_on_feeds(self):
        msg = self.fetch_periodics_table()
        for room in self.rooms():
            self.send(room, msg)

    def fetch_periodics_table(self, project_names=None):
        if not project_names:
            project_names = list(self.config['periodic_project_names'])

        def process_feed(feed):
            cleaned_entries = []
            if self.config['periodic_exclude_when']:
                now = timeutils.utcnow(with_timezone=True)
                expire_after = now + relativedelta(
                    **self.config['periodic_exclude_when'])
                for e in feed.entries:
                    when_pub = parser.parse(e.published)
                    if when_pub <= expire_after:
                        continue
                    cleaned_entries.append(e)
            else:
                cleaned_entries.extend(feed.entries)
            if len(cleaned_entries) == 0:
                return {
                    'status': 'All OK (no recent failures)',
                    'discarded': len(feed.entries) - len(cleaned_entries),
                    'last_fail': NA_VALUE,
                    'last_fail_url': NA_VALUE,
                }
            else:
                fails = []
                for e in cleaned_entries:
                    fails.append((e, parser.parse(e.published)))
                lastest_entry, latest_fail = sorted(
                    fails, key=lambda e: e[1])[-1]
                if latest_fail.tzinfo is not None:
                    when = latest_fail.strftime(
                        "%A %b, %e, %Y at %k:%M:%S %Z")
                else:
                    when = latest_fail.strftime("%A %b, %e, %Y at %k:%M:%S")
                return {
                    'status': "%s failures" % len(fails),
                    'last_fail': when,
                    'last_fail_url': lastest_entry.get("link", BAD_VALUE),
                    'discarded': len(feed.entries) - len(cleaned_entries),
                }

        def process_req_completion(fut):
            self.log.debug("Processing completion of '%s'", fut.rss_url)
            try:
                r = fut.result()
            except requests.Timeout:
                return {
                    'status': 'Fetch timed out',
                    'last_fail': BAD_VALUE,
                    'last_fail_url': BAD_VALUE,
                }
            except futures.CancelledError:
                return {
                    'status': 'Fetch cancelled',
                    'last_fail': BAD_VALUE,
                    'last_fail_url': BAD_VALUE,
                }
            except Exception:
                self.log.exception("Failed fetching!")
                return {
                    'status': 'Unknown fetch error',
                    'last_fail': BAD_VALUE,
                    'last_fail_url': BAD_VALUE,
                }
            else:
                if (r.status_code == http_client.BAD_REQUEST
                        and 'No Failed Runs' in r.text):
                    return {
                        'status': 'All OK (no recent failures)',
                        'last_fail': NA_VALUE,
                        'last_fail_url': NA_VALUE,
                    }
                elif r.status_code != http_client.OK:
                    return {
                        'status': 'Fetch failure (%s)' % r.reason,
                        'last_fail': BAD_VALUE,
                        'last_fail_url': BAD_VALUE,
                    }
                else:
                    return process_feed(feedparser.parse(r.text))

        rss_url_tpl = self.config['periodic_url_tpl']
        build_name_tpl = self.config['periodic_build_name_tpl']
        conn_kwargs = {
            'timeout': (self.config['periodic_connect_timeout'],
                        self.config['periodic_fetch_timeout']),
        }
        futs = set()
        for project_name in project_names:
            for py_ver in self.config['periodic_python_versions']:
                py_ver_str = "py" + "".join(str(p) for p in py_ver)
                build_name = build_name_tpl % {
                    'project_name': project_name,
                    'py_version': py_ver_str}
                rss_url = rss_url_tpl % {'build_name': build_name}
                self.log.debug("Scheduling call out to %s", rss_url)
                fut = self.executor.submit(requests.get,
                                           rss_url, **conn_kwargs)
                # TODO(harlowja): don't touch the future class and
                # do this in a more sane manner at some point...
                fut.rss_url = rss_url
                fut.build_name = build_name
                fut.project_name = project_name
                fut.py_version = py_ver
                futs.add(fut)
        self.log.debug("Waiting for %s fetch requests", len(futs))
        results = collections.defaultdict(list)
        for fut in futures.as_completed(futs):
            results[fut.project_name].append(
                (fut.py_version, process_req_completion(fut)))
        tbl_headers = [
            "Project",
            "Status",
            'Last failed',
            "Last failed url",
            'Discarded',
        ]
        tbl_body = []
        if (self.config['periodic_shorten'] and
                self.config['shortener_api_key']):
            s = GoogleShortener(
                self.log, self.config['shortener_api_key'],
                timeout=(self.config['shortener_connect_timeout'],
                         self.config['shortener_fetch_timeout']))
            shorten_func = s.safe_shorten
        else:
            shorten_func = lambda long_url: long_url
        for project_name in sorted(results.keys()):
            # This should force sorting by python version...
            for py_version, result in sorted(results[project_name]):
                py_version = ".".join(str(p) for p in py_version)
                last_fail_url = result['last_fail_url']
                if (last_fail_url and
                        last_fail_url not in [BAD_VALUE, NA_VALUE]):
                    last_fail_url = shorten_func(last_fail_url)
                tbl_body.append([
                    project_name.title() + " (" + py_version + ")",
                    result['status'],
                    result['last_fail'],
                    str(last_fail_url),
                    str(result.get('discarded', 0)),
                ])
        buf = six.StringIO()
        buf.write(tabulate(tbl_body, tbl_headers,
                           tablefmt=self.config['tabulate_format']))
        return buf.getvalue()

    def get_configuration_template(self):
        return copy.deepcopy(self.DEF_CONFIG)

    def deactivate(self):
        super(OsloBotPlugin, self).deactivate()
        if self.executor is not None:
            self.executor.shutdown()

    def activate(self):
        super(OsloBotPlugin, self).activate()
        self.executor = futures.ThreadPoolExecutor(
            max_workers=self.DEF_FETCH_WORKERS)
        try:
            if self.config['periodic_check_frequency'] > 0:
                self.start_poller(self.config['periodic_check_frequency'],
                                  self.report_on_feeds)
        except KeyError:
            pass
