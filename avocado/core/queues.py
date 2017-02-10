import os
import sys

from multiprocessing import queues


class SimpleQueue(queues.SimpleQueue):

    # There's no get/put methods in multiprocessing.SimpleQueue
    # Instead, the _make_methods is in charge to create the self.put()
    # and self.get(), containing the corresponding functions.
    # Let's override _make_methods so we can make some tricks.
    def _make_methods(self):
        super(SimpleQueue, self)._make_methods()

        # Create a queue to send the module_path from put() to be used
        # in get()
        internal_queue = queues.SimpleQueue()

        # Hold on ;)
        _put = self.put

        # Custom put()
        def put(value):
            module_dir = None
            # If we are to put 'func_at_exit', let's discover the
            # module_dir for the injected function
            if 'func_at_exit' in value:
                path = sys.modules.get(value['func_at_exit'].__module__).__file__
                module_dir = os.path.abspath(os.path.dirname(path))
            # Informing the module_dir to be consumed by get()
            internal_queue.put(module_dir)
            # Finally putting the msg in the actual queue
            _put(value)

        # Here is our put() with steroids.
        self.put = put

        # hold on
        _get = self.get

        # Custom get()
        def get():
            internal_msg = internal_queue.get()
            # Is there anything in the internal queue?
            if internal_msg:
                # If yes, it's a module_path, so let's include it in the
                # sys.path to be able to load in in the actual get()
                _syspath = sys.path[:]
                sys.path.insert(1, internal_msg)
            # Actual get()
            msg = _get()

            # Restoring the sys.path
            if internal_msg:
                sys.path = _syspath

            # Returning the msg, possibly with a func_at_exit nicely
            # loaded
            return msg

        # And here is our customized get()
        self.get = get
