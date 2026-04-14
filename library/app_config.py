#!/usr/bin/python
# -*- coding: utf-8 -*-
# library/app_config.py — example custom module
# Purpose: demonstrate writing an idempotent Ansible module in Python
# Usage:
#   - name: Manage app config
#     app_config:
#       path: /etc/myapp/config.json
#       key: database.host
#       value: "10.0.2.11"
#       state: present

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: app_config
short_description: Manage JSON application configuration
description:
  - Reads/writes a JSON config file using dot-notation keys.
  - Idempotent: only reports changed when value actually changes.
options:
  path:
    description: Path to the JSON config file.
    required: true
    type: str
  key:
    description: Dot-notation key (e.g., "database.host").
    required: true
    type: str
  value:
    description: Value to set. Required when state=present.
    type: raw
  state:
    description: Whether the key should be present or absent.
    choices: [present, absent]
    default: present
    type: str
'''

EXAMPLES = r'''
- name: Set database host
  app_config:
    path: /etc/myapp/config.json
    key: database.host
    value: "10.0.2.11"
    state: present

- name: Remove deprecated key
  app_config:
    path: /etc/myapp/config.json
    key: legacy.feature_flag
    state: absent
'''

RETURN = r'''
previous_value:
  description: Value before the change (if any).
  returned: when state=present and key existed
  type: raw
'''

import json
import os
from ansible.module_utils.basic import AnsibleModule


def get_nested(d, keys):
    """Get a nested dict value by a dot-path."""
    for key in keys:
        if not isinstance(d, dict) or key not in d:
            return None
        d = d[key]
    return d


def set_nested(d, keys, value):
    """Set a nested dict value by a dot-path."""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def delete_nested(d, keys):
    """Delete a nested dict key by a dot-path."""
    for key in keys[:-1]:
        if key not in d:
            return False
        d = d[key]
    if keys[-1] in d:
        del d[keys[-1]]
        return True
    return False


def run_module():
    module_args = dict(
        path=dict(type='str', required=True),
        key=dict(type='str', required=True),
        value=dict(type='raw', required=False),
        state=dict(type='str', default='present', choices=['present', 'absent']),
    )

    result = dict(changed=False, previous_value=None)
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    path = module.params['path']
    key = module.params['key']
    value = module.params['value']
    state = module.params['state']
    keys = key.split('.')

    # Read the existing config
    config = {}
    if os.path.exists(path):
        with open(path, 'r') as f:
            config = json.load(f)

    current_value = get_nested(config, keys)
    result['previous_value'] = current_value

    if state == 'present':
        if current_value != value:
            result['changed'] = True
            if not module.check_mode:
                set_nested(config, keys, value)
    elif state == 'absent':
        if current_value is not None:
            result['changed'] = True
            if not module.check_mode:
                delete_nested(config, keys)

    # Write the file (idempotent: only write when changed)
    if result['changed'] and not module.check_mode:
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
