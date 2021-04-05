#
# Copyright 2021 Red Hat Inc.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import glob
from importlib import import_module

try:
    import yaml

    # use C version if possible for speedup
    try:
        from yaml import CSafeLoader as SafeLoader
    except ImportError:
        from yaml import SafeLoader
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from ansible_collections.ansible.netcommon.plugins.action.network import (
    ActionModule as ActionNetworkModule,
)


class ActionModule(ActionNetworkModule):
    def run(self, task_vars=None):
        result = {}
        resource_modules = []
        os_value = self._task.args.get("os") or self._play_context.network_os
        if not os_value:
            return {'error': "either of 'os' option value or 'ansible_network_os' variable value is required to be set"}

        if len(os_value.split(".")) != 3:
            msg = "OS value name should be provided as a full name including collection in the" \
                  " format <org-name>.<collection-name>.<plugin-name>"
            return {'error': msg}

        cref = dict(
            zip(["corg", "cname", "plugin"], os_value.split("."))
        )
        modulelib = "ansible_collections.{corg}.{cname}.plugins.modules".format(
            corg=cref['corg'], cname=cref['cname'])

        module_dir_path = os.path.dirname(import_module(modulelib).__file__)
        module_paths = glob.glob(f"{module_dir_path}/[!_]*.py")
        for module_path in module_paths:
            module_name = os.path.basename(module_path).split('.')[0]
            docs = getattr(import_module(f"{modulelib}.{module_name}"), "DOCUMENTATION")
            if self.is_resource_module(docs):
                resource_modules.append(module_name)

        result.update({'modules': resource_modules})
        return result

    def is_resource_module(self, docs):
        doc_obj = yaml.load(docs, SafeLoader)
        if 'config' in doc_obj['options'] and 'state' in doc_obj['options']:
            return True
