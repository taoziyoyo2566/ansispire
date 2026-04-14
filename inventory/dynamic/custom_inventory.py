#!/usr/bin/env python3
"""
inventory/dynamic/custom_inventory.py — example dynamic-inventory script.

Purpose: generate an Ansible inventory from an arbitrary data source
(CMDB, database, API).
Run:  ansible-playbook site.yml -i inventory/dynamic/custom_inventory.py
Test: python custom_inventory.py --list | python -m json.tool

Must support two arguments:
  --list           : return JSON of all hosts and groups
  --host HOSTNAME  : return JSON of variables for the given host
                     (modern approach uses _meta in --list instead)
"""

import argparse
import json
import os
import sys


def get_inventory():
    """
    Simulate fetching host data from a CMDB/API and return the standard
    Ansible inventory structure.

    In production, replace the mock data with one of:
      - requests.get("https://cmdb.example.com/api/hosts")
      - psycopg2 queries against PostgreSQL
      - boto3 / libcloud calls against a cloud provider
    """
    # Mock data
    hosts_from_cmdb = [
        {"hostname": "app01.example.com", "ip": "10.0.1.21", "role": "webserver", "env": "production"},
        {"hostname": "app02.example.com", "ip": "10.0.1.22", "role": "webserver", "env": "production"},
        {"hostname": "db01.example.com",  "ip": "10.0.2.21", "role": "database",  "env": "production", "db_role": "primary"},
        {"hostname": "db02.example.com",  "ip": "10.0.2.22", "role": "database",  "env": "production", "db_role": "replica"},
    ]

    inventory = {
        "_meta": {
            "hostvars": {}  # per-host variables live in _meta.hostvars to avoid --host calls
        },
        "all": {
            "children": ["webservers", "dbservers"]
        },
        "webservers": {"hosts": []},
        "dbservers":  {"hosts": []},
    }

    for host in hosts_from_cmdb:
        hostname = host["hostname"]

        # Populate host variables
        inventory["_meta"]["hostvars"][hostname] = {
            "ansible_host": host["ip"],
            "env": host["env"],
        }
        if "db_role" in host:
            inventory["_meta"]["hostvars"][hostname]["db_role"] = host["db_role"]

        # Group by role
        if host["role"] == "webserver":
            inventory["webservers"]["hosts"].append(hostname)
        elif host["role"] == "database":
            inventory["dbservers"]["hosts"].append(hostname)

    return inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--host", type=str)
    args = parser.parse_args()

    if args.list:
        print(json.dumps(get_inventory(), indent=2))
    elif args.host:
        # Modern approach: all vars are returned in --list via _meta; --host returns empty.
        inventory = get_inventory()
        hostvars = inventory.get("_meta", {}).get("hostvars", {})
        print(json.dumps(hostvars.get(args.host, {}), indent=2))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
