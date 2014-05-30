# Copyright 2014 OpenCore LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import os
import sh
import sys
import time
from string import Template

class MongoInitializer(object):
    def __init__(self):
        """
        Create a new initializer
        Param user The user login for the git repo
        """
        self.template_dir = None
        self.template_repo = None

        self.container_data_dir = MongoConfig.data_directory
        self.container_log_dir = MongoConfig.log_directory

    def new_host_name(self, instance_id):
        """
        Generate a new hostname
        """
        return 'mongo' + str(instance_id)

    def _execute_service(self, containers, entry_point, fabric, cmd):
        """
        Start the service on the containers. 
        """
        for c in containers:
            fabric.cmd([c], '/service/sbin/startnode %s' % cmd)

        # Now wait a couple seconds to make sure
        # everything has started.
        time.sleep(5)
    def start_service(self, containers, entry_point, fabric):
        self._execute_service(containers, entry_point, fabric, "start")
    def restart_service(self, containers, entry_point, fabric):
        self._execute_service(containers, entry_point, fabric, "restart")
    def stop_service(self, containers, entry_point, fabric):        
        self._execute_service(containers, entry_point, fabric, "stop")

    def _generate_config_dir(self, uuid):
        """
        Generate a new configuration.
        """
        return 'mongo_' + str(uuid)

    def get_necessary_ports(self, num_instances):
        """
        Get the ports necessary.
        """
        return []

    def get_exposed_ports(self, num_instances):
        """
        Get the internal ports. 
        """
        return [MongoConfig.MONGO_PORT]

    def get_total_instances(self, num_instances, layers):
        instances = []

        for i in range(num_instances):
            instances.append('mongo')

        return instances

    def generate(self, num):
        """
        Generate a new configuration
        Param num Number of instances that need to be configured
        Param image Image type of the instances
        """
        return MongoConfig(num)

    def _generate_mongo_config(self, host_dir, config):
        """
        Generate the MongoDB configuration file. 
        """
        in_file = open(self.template_dir + '/mongodb.conf.template', 'r')
        out_file = open(host_dir + '/mongodb.conf', 'w+')

        changes = { "MONGO_LOG":config.log_directory, 
                    "MONGO_DATA":config.data_directory }

        for line in in_file:
            s = Template(line).substitute(changes)
            out_file.write(s)

        out_file.close()
        in_file.close()

    def apply(self, config, containers):
        """
        Apply the configuration to the instances
        """
        entry_point = { 'type' : 'mongo' }
        config_dirs = []

        # Keep track of the MongoDB IP address. 
        entry_point['ip'] = str(containers[0]['data_ip'])

        new_config_dir = "/tmp/" + self._generate_config_dir(config.uuid)
        try:
            sh.mkdir('-p', new_config_dir)
        except:
            sys.stderr.write('could not create config dir ' + new_config_dir)

        # This file records all instances so that we can
        # generate the hosts file. 
        entry_point['instances'] = []
        for server in containers:
            entry_point['instances'].append([server['data_ip'], server['host_name']])

        if not 'storage' in containers[0]:
            # This is being called as a storage service. 
            # The client service doesn't do anything right now. 
            self._generate_mongo_config(new_config_dir, config)

        # Transfer the configuration. 
        for c in containers:
            config_files = new_config_dir + '/*'
            config_dirs.append([c['container'],
                                config_files, 
                                config.config_directory])

        return config_dirs, entry_point

class MongoConfig(object):
    log_directory = '/service/logs'
    config_directory = '/service/conf/mongodb'
    data_directory = '/service/data'
    MONGO_PORT = 27017

    def __init__(self, num):
        self.num = num
        self.mongo_port = MongoConfig.MONGO_PORT
        self.config_directory = MongoConfig.config_directory
        self.log_directory = MongoConfig.log_directory
        self.data_directory = MongoConfig.data_directory
