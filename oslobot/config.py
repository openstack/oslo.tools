import logging
import os

BOT_DATA_DIR = os.path.join(os.getcwd(), 'data')
BOT_EXTRA_PLUGIN_DIR = os.path.join(os.getcwd(), 'plugins')

# We aren't really using this feature, so memory is fine.
STORAGE = 'Memory'

BOT_LOG_FILE = None
BOT_LOG_LEVEL = logging.DEBUG

# The admins that can send the bot special commands...
#
# For now just taken from current oslo-core list (we should make
# this more dynamic in the future, perhaps reading the list from
# gerrit on startup?).
BOT_ADMINS = [
    'bknudson',
    'bnemec',
    'dhellmann',
    'dims',
    'flaper87',
    'gcb',
    'harlowja',
    'haypo',
    'jd__',
    'lifeless',
    'lxsli',
    'mikal',
    'Nakato',
    # TODO(harlowja): Does case matter?
    'nakato',
    'rbradfor',
    'sileht',
]

# The following will change depending on the backend selected...
BACKEND = 'IRC'
BOT_IDENTITY = {
    'server': 'chat.freenode.net',
    'nickname': 'oslobot',
}
COMPACT_OUTPUT = False
CORE_PLUGINS = ('ACLs', 'Help', 'Health', 'Plugins', 'ChatRoom')

# Rooms we will join by default.
CHATROOM_PRESENCE = [
    '#openstack-oslo',
]
