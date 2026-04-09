#!/usr/bin/env python3
"""
inventory/dynamic/custom_inventory.py — 自定义动态 Inventory 脚本
用途: 从任意数据源（CMDB、数据库、API）生成 Ansible inventory
运行: ansible-playbook site.yml -i inventory/dynamic/custom_inventory.py
测试: python custom_inventory.py --list | python -m json.tool

必须支持两个参数:
  --list  : 返回所有主机和组的 JSON
  --host HOSTNAME : 返回指定主机的变量 JSON（现代方式用 _meta 代替此接口）
"""

import argparse
import json
import os
import sys


def get_inventory():
    """
    模拟从 CMDB/API 获取主机数据，返回标准 Ansible inventory 格式。

    实际使用时可替换为:
    - requests.get("https://cmdb.example.com/api/hosts")
    - psycopg2 查询 PostgreSQL
    - boto3 / libcloud 查询云平台
    """
    # 模拟数据
    hosts_from_cmdb = [
        {"hostname": "app01.example.com", "ip": "10.0.1.21", "role": "webserver", "env": "production"},
        {"hostname": "app02.example.com", "ip": "10.0.1.22", "role": "webserver", "env": "production"},
        {"hostname": "db01.example.com",  "ip": "10.0.2.21", "role": "database",  "env": "production", "db_role": "primary"},
        {"hostname": "db02.example.com",  "ip": "10.0.2.22", "role": "database",  "env": "production", "db_role": "replica"},
    ]

    inventory = {
        "_meta": {
            "hostvars": {}  # 每台主机的变量放在 _meta.hostvars 里，避免 --host 调用
        },
        "all": {
            "children": ["webservers", "dbservers"]
        },
        "webservers": {"hosts": []},
        "dbservers":  {"hosts": []},
    }

    for host in hosts_from_cmdb:
        hostname = host["hostname"]

        # 填充主机变量
        inventory["_meta"]["hostvars"][hostname] = {
            "ansible_host": host["ip"],
            "env": host["env"],
        }
        if "db_role" in host:
            inventory["_meta"]["hostvars"][hostname]["db_role"] = host["db_role"]

        # 按 role 分组
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
        # 现代做法: 所有变量在 --list 的 _meta 里返回，--host 返回空
        inventory = get_inventory()
        hostvars = inventory.get("_meta", {}).get("hostvars", {})
        print(json.dumps(hostvars.get(args.host, {}), indent=2))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
