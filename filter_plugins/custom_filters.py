# filter_plugins/custom_filters.py — 自定义 Jinja2 过滤器
#
# Ansible 自动加载项目根目录下 filter_plugins/ 中的所有 .py 文件
# 无需额外配置，直接在模板和 vars 中使用: {{ value | filter_name }}
#
# 内置常用过滤器备忘:
#   {{ list | unique }}           去重
#   {{ list | sort }}             排序
#   {{ list | flatten }}          扁平化嵌套列表
#   {{ dict | dict2items }}       字典转 [{key:..., value:...}] 列表
#   {{ list | items2dict }}       列表转字典
#   {{ dict | combine(other) }}   合并字典
#   {{ str | regex_search(pat) }} 正则搜索
#   {{ str | regex_replace(p,r) }}正则替换
#   {{ val | default(x, true) }}  空值也用默认（true = boolean false 也替换）
#   {{ val | mandatory }}         未定义则立即报错
#   {{ b | ternary(x, y) }}       三元: b ? x : y
#   {{ n | human_readable }}      字节数转人类可读（1073741824 → "1.0 GB"）
#   {{ str | b64encode }}         Base64 编码
#   {{ str | password_hash('sha512') }} 生成密码哈希
#   {{ path | basename }}         路径中的文件名
#   {{ path | dirname }}          路径中的目录部分
#   {{ path | expanduser }}       展开 ~ 路径

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import re


def to_nginx_size(value):
    """
    将字节数转为 Nginx 大小字符串。
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
    将 CIDR 列表转为 Nginx allow 指令列表。
    {{ ['10.0.0.0/8'] | cidr_to_nginx_allow }}  →  ['allow 10.0.0.0/8;']
    """
    return [f"allow {cidr};" for cidr in cidr_list]


def mask_secret(value, visible=4):
    """
    遮盖敏感字符串，只显示前 N 位（用于 debug 输出，避免泄露）。
    {{ 'SuperSecret123' | mask_secret }}  →  "Supe**********"
    """
    s = str(value)
    if len(s) <= visible:
        return '*' * len(s)
    return s[:visible] + '*' * (len(s) - visible)


def env_badge(env, style='bracket'):
    """
    根据环境名返回可读标记。
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
    解析版本字符串为可比较的元组。
    {{ 'v2.3.1' | parse_version }}  →  [2, 3, 1]
    使用: {{ '2.3.1' | parse_version >= '2.0.0' | parse_version }}
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
    将 Python bool / Ansible yes/no 转为 systemd 的 yes/no 格式。
    {{ true | to_systemd_bool }}  →  "yes"
    {{ false | to_systemd_bool }} →  "no"
    """
    if isinstance(value, bool):
        return "yes" if value else "no"
    s = str(value).lower()
    return "yes" if s in ('true', 'yes', '1', 'on') else "no"


class FilterModule(object):
    """Ansible 通过此类发现过滤器"""

    def filters(self):
        return {
            'to_nginx_size':    to_nginx_size,
            'cidr_to_nginx_allow': cidr_to_nginx_allow,
            'mask_secret':      mask_secret,
            'env_badge':        env_badge,
            'parse_version':    parse_version,
            'to_systemd_bool':  to_systemd_bool,
        }
