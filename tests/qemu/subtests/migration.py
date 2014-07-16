

def run(test):
    vm = test.env.get_vm(test.params.main_vm)
    vm.migrate()