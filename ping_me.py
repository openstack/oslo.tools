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

"""Script that is useful to run to make commands that will ping
   folks for the oslo weekly irc meeting.
"""

import collections
import sys

NOTIFY_PEPS = [
    'amotoki', 'amrith', 'ansmith', 'bnemec',
    'dansmith', 'dims', 'dougwig', 'e0ne', 'flaper87',
    'garyk', 'haypo', 'hberaud', 'electrocucaracha', 'jd__',
    'johnsom', 'jungleboyj', 'kgiusti', 'kragniz', 'lhx_', 'moguimar',
    'njohnston', 'raildo', 'redrobot',
    'sileht', 'sreshetnyak', 'stephenfin', 'stevemar', 'therve', 'thinrichs',
    'toabctl', 'zhiyan', 'zzzeek', 'gcb',
    'zxy',
]
NOTIFY_PEPS = sorted(NOTIFY_PEPS, key=str.lower)
NUM_PER_LINE = 7
INFO_MESSAGE = ('To be added or removed from the ping list, please submit a '
                'patch to '
                'http://git.openstack.org/cgit/openstack/oslo.tools/tree/'
                'ping_me.py\n'
                )


def main():
    sys.stdout.write("courtesy ping for ")
    num_in_line = 0
    peps = collections.deque(NOTIFY_PEPS)
    while peps:
        pep = peps.popleft()
        sys.stdout.write(pep)
        num_in_line += 1
        if num_in_line >= NUM_PER_LINE:
            sys.stdout.write("\n")
            if peps:
                sys.stdout.write("courtesy ping for ")
            num_in_line = 0
        else:
            if peps:
                sys.stdout.write(", ")
    if num_in_line:
        sys.stdout.write("\n")
    sys.stdout.write(INFO_MESSAGE)


if __name__ == '__main__':
    main()
