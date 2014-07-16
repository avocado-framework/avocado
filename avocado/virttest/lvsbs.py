"""
Higher order classes for Libvirt Sandbox Service (lxc) service container testing
"""

from autotest.client import utils
from autotest.client.shared.service import COMMANDS
from virttest.staging import service
import lvsb_base
import virsh


class SandboxService(object):

    """
    Management for a single new/existing sandboxed service
    """

    def __init__(self, params, service_name, uri='lxc:///'):
        """Initialize connection to sandbox service with name and parameters"""
        # Intended workflow is:
        #   Use virt-sandbox-service for create/destroy
        #   Use service/systemd for runtime management
        #   Use virsh for list/edit/modify manipulation
        self.virsh = virsh.Virsh(uri=uri, ignore_status=True)
        self.command = lvsb_base.SandboxCommandBase(params, service_name)
        self.command.BINARY_PATH_PARAM = params.get('virt_sandbox_service_binary',
                                                    "virt-sandbox-service")
        self.command.add_optarg('--connect', uri)
        # We need to pass self.service_name to service.Factory.create_service to
        # create a service. Then we will get a SpecificServiceManager object as
        # self.service. But SpecificServiceManager is not pickleable, save init
        # args here.
        self._run = utils.run
        self.service = service.Factory.create_service(self.service_name,
                                                      run=self._run)
        # make self.start() --> self.service.start()
        self._bind_service_commands()

    def _bind_service_commands(self):
        """Setup service methods locally for __init__ and __setstate__"""
        for command in COMMANDS:
            # Use setattr to keep pylint quiet
            setattr(self, command, getattr(self.service, command))

    def __getstate__(self):
        """Serialize instance for pickling"""
        # SandboxCommandBase is directly pickleable
        return {'command': self.command, 'run': self._run, 'virsh': dict(virsh)}

    def __setstate__(self, state):
        """Actualize instance from state"""
        # virsh is it's own dict of init params
        self.virsh = virsh.Virsh(**state['virsh'])
        # already used it's own get/sets state methods when unpickling state
        self.command = state['command']
        # Recreate SpecificServiceManager from the init args
        self._run = state['run']
        self.service = service.Factory.create_service(self.service_name,
                                                      run=self._run)
        self._bind_service_commands()

    # Enforce read-only at all levels
    @property
    def service_name(self):
        return self.command.name

    # property accessor functions must be defined before naming attribute
    def __get_uri__(self):
        return self.virsh.uri

    def __set_uri__(self, uri):
        self.virsh.uri = uri

    def __del_uri__(self):
        # Virsh class interface insists this attribute exist, but can be None
        self.virsh.uri = None

    # Property definition must follow accessor definitions
    uri = property(__get_uri__, __set_uri__, __del_uri__)

    def create(self):
        return self.command.run(extra='create')

    def destroy(self):
        return self.command.run(extra='destroy')

    # Specialized list calls can just call self.virsh.dom_list() directly
    @property  # behave like attribute to make value-access easier
    def list(self):
        """
        Return list of dictionaries mapping column names to values
        """
        # For simple callers, just return list of names to be convenient
        cmdresult = self.virsh.dom_list()  # uri is passed automatically
        result = []
        column_names = None  # scope outside loop
        for lineno, line in cmdresult.stdout.strip():
            if lineno == 0:
                column_names = line.strip().split()
                assert len(column_names) > 2
            else:
                assert column_names is not None
                # raises exception when column_names & value count mismatch
                items = [(column_names[index].lower(), value.lower())
                         for index, value in line.strip().split()]
                # combine [('id',99), ('name', 'foobar'), ('state', 'running')]
                result.append(dict(items))
        return result

    # Specialized list calls can just call self.virsh.dom_list() directly
    @property  # behave like attribute for easy passing to XML handling methods
    def xmlstr(self):
        return self.virsh.dumpxml(self.service_name).stdout.strip()
