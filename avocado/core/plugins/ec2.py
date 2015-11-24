# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#

"""
Run tests on an EC2 (Amazon Elastic Cloud) instance.
"""

import boto3
import uuid
import tempfile
import os
import time

from . import plugin
from ..remoter import Remote
from ..remote import RemoteTestResult
from ..remote import RemoteTestRunner


class KeyPairWrapper(object):

    def __init__(self, service, name, stream):
        self.keypair = service.create_key_pair(KeyName=name)
        self.keyfile = os.path.join(tempfile.gettempdir(),
                                    '{}.pem'.format(name))
        with open(self.keyfile, 'w') as keyfile_obj:
            keyfile_obj.write(self.keypair.key_material)
        os.chmod(self.keyfile, 0o400)
        stream.notify(event='message',
                      msg=("KEYPAIR    : %s" % self.keyfile))

    def destroy(self):
        self.keypair.delete()
        try:
            os.remove(self.keyfile)
        except OSError:
            pass


class EC2InstanceWrapper(object):

    def __init__(self, args, stream):
        self.ec2 = boto3.resource('ec2')
        self.uuid = uuid.uuid1()
        self.name = 'avocado-test-%s' % self.uuid
        # Create keypair
        self.keypair = KeyPairWrapper(service=self.ec2, name=self.name,
                                      stream=stream)
        sgid_list = args.ec2_security_group_ids.split(',')
        # Create instance
        inst_list = self.ec2.create_instances(ImageId=args.ec2_ami_file_id,
                                              MinCount=1, MaxCount=1,
                                              KeyName=self.keypair.keypair.name,
                                              SecurityGroupIds=sgid_list,
                                              SubnetId=args.ec2_subnet_id,
                                              InstanceType=args.ec2_instance_type)
        self.instance = inst_list[0]
        stream.notify(event='message',
                      msg=("EC2_ID     : %s" % self.instance.id))
        # Rename the instance
        self.ec2.create_tags(Resources=[self.instance.id],
                             Tags=[{'Key': 'Name', 'Value': self.name}])
        self.instance.wait_until_running()
        # Get public IP
        while self.instance.public_ip_address is None:
            time.sleep(1)
            self.instance.reload()
        stream.notify(event='message',
                      msg=("EC2_IP     : %s" %
                           self.instance.public_ip_address))
        # Install avocado in the instance
        self.remoter = Remote(hostname=self.instance.public_ip_address,
                              username=args.ec2_ami_username,
                              key_filename=self.keypair.keyfile,
                              timeout=120, attempts=10, quiet=False)
        self.install_avocado(distro_type=args.ec2_ami_distro_type)

    def install_avocado(self, distro_type):
        retrieve_cmd = None
        install_cmd = None
        if distro_type == 'fedora':
            remote_repo = ('https://repos-avocadoproject.rhcloud.com/static/'
                           'avocado-fedora.repo')
            local_repo = '/etc/yum.repos.d/avocado.repo'
            retrieve_cmd = 'sudo curl %s -o %s' % (remote_repo, local_repo)
            install_cmd = 'sudo dnf install -y avocado'
        elif distro_type == 'el':
            remote_repo = ('https://repos-avocadoproject.rhcloud.com/static/'
                           'avocado-el.repo')
            local_repo = '/etc/yum.repos.d/avocado.repo'
            retrieve_cmd = 'sudo curl %s -o %s' % (remote_repo, local_repo)
            install_cmd = 'sudo yum install -y avocado'
        elif distro_type == 'ubuntu':
            remote_repo = ('deb http://ppa.launchpad.net/lmr/avocado/ubuntu '
                           'wily main')
            local_repo = '/etc/apt/sources.list.d/avocado.list'
            retrieve_cmd = ('sudo echo "%s" > %s' % (remote_repo, local_repo))
            install_cmd = 'sudo apt-get install --yes --force-yes avocado'

        self.remoter.run(retrieve_cmd, timeout=120)
        self.remoter.run(install_cmd, timeout=120)

    def destroy(self):
        self.instance.terminate()
        self.keypair.destroy()


class EC2TestResult(RemoteTestResult):

    """
    Amazon EC2 (Elastic Cloud) Test Result class.
    """

    def __init__(self, stream, args):
        super(EC2TestResult, self).__init__(stream, args)
        self.instance = None
        self.keypair = None
        self.command_line_arg_name = '--ec2-ami-file-id'

    def setup(self):
        self.stream.notify(event='message', msg="AMI_ID     : %s"
                           % self.args.ec2_ami_file_id)
        self.instance = EC2InstanceWrapper(self.args, self.stream)

        try:
            # Finish remote setup and copy the tests
            self.args.remote_hostname = self.instance.instance.public_ip_address
            self.args.remote_key_file = self.instance.keypair.keyfile
            self.args.remote_port = self.args.ec2_instance_ssh_port
            self.args.remote_username = self.args.ec2_ami_username
            self.args.remote_timeout = self.args.ec2_login_timeout
            self.args.remote_password = None
            self.args.remote_no_copy = False
            super(EC2TestResult, self).setup()
        except Exception:
            self.tear_down()
            raise

    def tear_down(self):
        super(EC2TestResult, self).tear_down()
        self.instance.destroy()


class RunEC2(plugin.Plugin):

    """
    Run tests on an EC2 (Amazon Elastic Cloud) instance
    """

    name = 'run_ec2'
    enabled = True
    ami_parser = None

    def configure(self, parser):
        msg = 'test execution on an EC2 (Amazon Elastic Cloud) instance'
        username = 'fedora'
        valid_distros = ['fedora (for Fedora > 22)',
                         'el (for RHEL/CentOS > 6.0)',
                         'ubuntu (for Ubuntu > 14.04)']
        self.ami_parser = parser.runner.add_argument_group(msg)
        self.ami_parser.add_argument('--ec2-ami-file-id',
                                     dest='ec2_ami_file_id',
                                     help=('Amazon Machine Image ID. '
                                           'Example: ami-e08adb8a'))
        self.ami_parser.add_argument('--ec2-ami-username',
                                     dest='ec2_ami_username',
                                     default=username,
                                     help=('User for the AMI image login. '
                                           'Defaults to root'))
        self.ami_parser.add_argument('--ec2-ami-distro-type',
                                     dest='ec2_ami_distro_type',
                                     default='fedora',
                                     help=('AMI base Linux Distribution. '
                                           'Valid values: %s. '
                                           'Defaults to fedora' %
                                           ', '.join(valid_distros)))
        self.ami_parser.add_argument('--ec2-instance-ssh-port',
                                     dest='ec2_instance_ssh_port',
                                     default=22,
                                     help=('sshd port for the EC2 instance. '
                                           'Defaults to 22'))
        self.ami_parser.add_argument('--ec2-security-group-ids',
                                     dest='ec2_security_group_ids',
                                     help=('Comma separated list of EC2 '
                                           'security group IDs. '
                                           'Example: sg-a5e1d7b0'))
        self.ami_parser.add_argument('--ec2-subnet-id',
                                     dest='ec2_subnet_id',
                                     help=('EC2 subnet ID. '
                                           'Example: subnet-ec4a72c4'))
        self.ami_parser.add_argument('--ec2-instance-type',
                                     dest='ec2_instance_type',
                                     help=('EC2 instance type. '
                                           'Example: c4.xlarge'))
        self.ami_parser.add_argument('--ec2-login-timeout', metavar='SECONDS',
                                     help=("Amount of time (in seconds) to "
                                           "wait for a successful connection"
                                           " to the EC2 instance. Defaults"
                                           " to 120 seconds"),
                                     default=120, type=int)
        self.configured = True

    @staticmethod
    def _check_required_args(app_args, enable_arg, required_args):
        """
        :return: True when enable_arg enabled and all required args are set
        :raise sys.exit: When missing required argument.
        """
        if (not hasattr(app_args, enable_arg) or
                not getattr(app_args, enable_arg)):
            return False
        missing = []
        for arg in required_args:
            if not getattr(app_args, arg):
                missing.append(arg)
        if missing:
            from .. import output, exit_codes
            import sys
            view = output.View(app_args=app_args)
            e_msg = ('Use of %s requires %s arguments to be set. Please set %s'
                     '.' % (enable_arg, ', '.join(required_args),
                            ', '.join(missing)))

            view.notify(event='error', msg=e_msg)
            return sys.exit(exit_codes.AVOCADO_FAIL)
        return True

    def activate(self, app_args):
        if self._check_required_args(app_args,
                                     'ec2_ami_file_id',
                                     ('ec2_ami_file_id',
                                      'ec2_security_group_ids',
                                      'ec2_subnet_id',
                                      'ec2_instance_type')):
            self.ami_parser.set_defaults(remote_result=EC2TestResult,
                                         test_runner=RemoteTestRunner)
