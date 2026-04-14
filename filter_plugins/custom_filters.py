# filter_plugins/custom_filters.py — custom Jinja2 filters
#
# Ansible auto-loads every .py under the project-root filter_plugins/ directory.
# No extra configuration needed — use in templates and vars as: {{ value | filter_name }}
#
# Built-in filter cheat-sheet:
#   {{ list | unique }}            deduplicate
#   {{ list | sort }}              sort
#   {{ list | flatten }}           flatten nested lists
#   {{ dict | dict2items }}        dict → [{key:..., value:...}]
#   {{ list | items2dict }}        list → dict
#   {{ dict | combine(other) }}    merge dicts
#   {{ str | regex_search(pat) }}  regex search
#   {{ str | regex_replace(p,r) }} regex replace
#   {{ val | default(x, true) }}   default also for empty (true = replace boolean false too)
#   {{ val | mandatory }}          fail immediately if undefined
#   {{ b | ternary(x, y) }}        ternary: b ? x : y
#   {{ n | human_readable }}       bytes → human (1073741824 → "1.0 GB")
#   {{ str | b64encode }}          base64 encode
#   {{ str | password_hash('sha512') }} generate a password hash
#   {{ path | basename }}          filename portion of a path
#   {{ path | dirname }}           directory portion of a path
#   {{ path | expanduser }}        expand a leading ~

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import re


def to_nginx_size(value):
    """
    Convert bytes into an Nginx size string.
    {{ 1073741824 | to_nginx_size }}  →  "1g"
    {{ 10485760 | to_nginx_size }}    →  "10m"
    """
    value = int(value)
    if value >= 1073741824:
        return f"{value // 1073741824}g"
    elif value >= 1048576:
        return f"{value // 1048576}m"
    elif value >= 1024:
        return f"{value // 1024}k"
    return str(value)


def cidr_to_nginx_allow(cidr_list):
    """
    Convert a CIDR list into Nginx `allow` directives.
    {{ ['10.0.0.0/8'] | cidr_to_nginx_allow }}  →  ['allow 10.0.0.0/8;']
    """
    return [f"allow {cidr};" for cidr in cidr_list]


def mask_secret(value, visible=4):
    """
    Mask a sensitive string, showing only the first N characters
    (for debug output so the secret does not leak).
    {{ 'SuperSecret123' | mask_secret }}  →  "Supe**********"
    """
    s = str(value)
    if len(s) <= visible:
        return '*' * len(s)
    return s[:visible] + '*' * (len(s) - visible)


def env_badge(env, style='bracket'):
    """
    Return a readable badge for the environment name.
    {{ 'production' | env_badge }}  →  "[PROD]"
    {{ 'staging' | env_badge }}     →  "[STAGING]"
    """
    mapping = {
        'production':  'PROD',
        'prod':        'PROD',
        'staging':     'STAGING',
        'stage':       'STAGING',
        'development': 'DEV',
        'dev':         'DEV',
        'testing':     'TEST',
        'test':        'TEST',
    }
    label = mapping.get(env.lower(), env.upper())
    if style == 'bracket':
        return f"[{label}]"
    elif style == 'emoji':
        emoji_map = {'PROD': '🔴', 'STAGING': '🟡', 'DEV': '🟢', 'TEST': '🔵'}
        return emoji_map.get(label, '⚪')
    return label


def parse_version(version_string):
    """
    Parse a version string into a comparable tuple.
    {{ 'v2.3.1' | parse_version }}  →  [2, 3, 1]
    Usage: {{ '2.3.1' | parse_version >= '2.0.0' | parse_version }}
    """
    clean = re.sub(r'^[vV]', '', str(version_string))
    parts = re.split(r'[.\-]', clean)
    result = []
    for part in parts:
        try:
            result.append(int(part))
        except ValueError:
            result.append(part)
    return result


def to_systemd_bool(value):
    """
    Convert a Python bool / Ansible yes-no into systemd's yes/no format.
    {{ true | to_systemd_bool }}  →  "yes"
    {{ false | to_systemd_bool }} →  "no"
    """
    if isinstance(value, bool):
        return "yes" if value else "no"
    s = str(value).lower()
    return "yes" if s in ('true', 'yes', '1', 'on') else "no"


class FilterModule(object):
    """Ansible discovers filters through this class."""

    def filters(self):
        return {
            'to_nginx_size':    to_nginx_size,
            'cidr_to_nginx_allow': cidr_to_nginx_allow,
            'mask_secret':      mask_secret,
            'env_badge':        env_badge,
            'parse_version':    parse_version,
            'to_systemd_bool':  to_systemd_bool,
        }
