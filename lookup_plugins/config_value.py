# lookup_plugins/config_value.py — 自定义 Lookup 插件示例
#
# 用途: 从自定义配置源（CMDB、配置中心）动态查找配置值
# 使用:
#   vars:
#     db_host: "{{ lookup('config_value', 'database.host') }}"
#     app_port: "{{ lookup('config_value', 'app.port', env='production') }}"
#
# Ansible 自动从以下位置加载:
#   - 项目根目录的 lookup_plugins/
#   - ansible.cfg 中 lookup_plugins 配置的路径

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
  name: config_value
  author: platform-team
  short_description: Fetch configuration values from a config store
  description:
    - Retrieves configuration values from a centralized config store.
    - Falls back to a default value if the key is not found.
    - In this demo, uses a hard-coded dict; replace with real API calls.
  options:
    _terms:
      description: Dot-notation config keys to look up
      required: true
    env:
      description: Environment to query (production, staging, etc.)
      type: str
      default: production
    default:
      description: Default value if key not found
      type: raw
      default: None
"""

EXAMPLES = r"""
- name: Get database host
  ansible.builtin.debug:
    msg: "{{ lookup('config_value', 'database.host') }}"

- name: Get multiple values
  ansible.builtin.debug:
    msg: "{{ query('config_value', 'app.port', 'app.workers') }}"
"""

RETURN = r"""
  _list:
    description: List of config values corresponding to the queried keys
    type: list
"""

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase


# 模拟配置存储（实际替换为 CMDB API / Consul / etcd 调用）
MOCK_CONFIG_STORE = {
    "production": {
        "database.host": "db01.example.com",
        "database.port": "3306",
        "app.port": "8080",
        "app.workers": "4",
        "cache.host": "redis01.example.com",
        "cache.port": "6379",
    },
    "staging": {
        "database.host": "staging-db01.example.com",
        "database.port": "3306",
        "app.port": "8080",
        "app.workers": "2",
        "cache.host": "staging-redis01.example.com",
        "cache.port": "6379",
    },
}


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        # 获取参数
        env = kwargs.get("env", "production")
        default = kwargs.get("default", None)

        config = MOCK_CONFIG_STORE.get(env, {})
        results = []

        for term in terms:
            value = config.get(term)
            if value is None:
                if default is not None:
                    value = default
                else:
                    raise AnsibleError(
                        f"config_value: key '{term}' not found in env '{env}' "
                        f"and no default provided"
                    )
            results.append(value)

        return results
