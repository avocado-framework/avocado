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
# Copyright: Red Hat Inc. 2016
# Author: Lukas Doktor <ldoktor@redhat.com>
import time
import atexit
import logging
"""
Multi-host synchronization and communication plugin
"""
import SocketServer
import socket
import threading

from .base import CLI


# TODO: Create "avocado.plugins" log and use __name__ instead
# TODO: This log must start early and re-log the content when job output dir
#       is initialized
LOG = logging.getLogger("avocado.test")


class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

    barriers = {}
    lock = threading.Lock()

    def _abort_barrier(self, name, host):
        with self.lock:
            barrier = self.barriers[name]
            barrier["hosts"].remove(host)
            if not len(barrier["hosts"]):
                self.log("REMOVING BARRIER %s ABORT" % name)
                del self.barriers[name]

    def log(self, msg, level=logging.DEBUG):
        LOG.log(level, "%s:%s: %s", self.client_address[0],
                self.client_address[1], msg)

    def _handle_barrier(self, data):
        # Identify barrier
        no_clients, name = data.split(':', 1)
        no_clients = int(no_clients)
        host = "%s:%s" % self.client_address
        with self.lock:
            if name not in self.barriers:
                self.log("CREATING BARRIER %s" % name, logging.INFO)
                self.barriers[name] = {"no_clients": no_clients,
                                       "hosts": [host],
                                       "handled_hosts": []}
            elif self.barriers[name]["no_clients"] != no_clients:
                msg = ("Barrier %s exists with different no_clients"
                       % name)
                self.log("ABORT:%s" % msg)
                self.request.sendall("ABORT:%s" % msg)
                return
            elif len(self.barriers[name]["hosts"]) == no_clients:
                msg = ("ABORT:Barrier %s has got enough clients: %s"
                       % (name, self.barriers[name]))
                self.log(msg, logging.ERROR)
                self.request.sendall(msg)
                return
            else:
                self.log("JOINING BARRIER %s" % name, logging.INFO)
                self.barriers[name]["hosts"].append(host)
        # Wait until barrier reached
        barrier = self.barriers[name]
        self.request.settimeout(1)
        data = ""
        while len(barrier["hosts"]) < no_clients:
            if barrier.get("abort"):
                self.request.settimeout(None)
                self.log("ABORT:%s" % barrier.get("abort"))
                self.request.sendall("ABORT:%s" % barrier.get("abort"))
                self._abort_barrier(name, host)
                return
            try:
                data += self.request.recv(1024)
                self.log(data)
            except socket.timeout:
                continue
            if data.startswith("ABORT:"):
                barrier["abort"] = "%s: %s" % (host, data[6:])
                self._abort_barrier(name, host)
                return
        # Barrier reached, make sure all clients are there
        self.request.settimeout(None)
        self.log("REACHED")
        self.request.sendall("REACHED")
        self.request.settimeout(1)
        deadline = time.time() + 10
        data = ""
        while time.time() < deadline:
            if barrier.get("abort"):
                self.request.settimeout(None)
                self.log("ABORT:%s" % barrier.get("abort"))
                self.request.sendall("ABORT:%s" % barrier.get("abort"))
                self._abort_barrier(name, host)
                return
            try:
                data += self.request.recv(1024)
                self.log(data)
            except socket.timeout:
                continue
            if data == "ACK":
                break
        else:
            self.request.settimeout(None)
            msg = "%s did not responded on REACHED" % host
            barrier["abort"] = msg
            self.log("ABORT:%s" % msg)
            self.request.sendall("ABORT:%s" % msg)
            self._abort_barrier(name, host)
            return
        # Got ack
        self.request.settimeout(None)
        self.log("GOGOGO")
        self.request.sendall("GOGOGO")
        barrier["handled_hosts"].append(host)
        # This host is inside barrier, clean this barrier if necessary
        with self.lock:
            if len(barrier["hosts"]) == len(barrier["handled_hosts"]):
                # I'm the last, remove the barrier
                self.log("REMOVING BARRIER %s PASS" % name, logging.INFO)
                del self.barriers[name]

    def handle(self):
        cmd, data = self.request.recv(1024).split(':', 1)
        self.log("%s:%s" % (cmd, data))

        # TODO: Add support for sending pickled objects
        if cmd == "BARRIER":
            return self._handle_barrier(data)
        else:
            msg = "Unknown command: %s:%s" % (cmd, data)
            self.request.sendall("ERROR:" + msg)
            self.log(msg, level=logging.ERROR)


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass


def parse_addr(value):
    if ':' in value:
        host, port = value.rsplit(":", 1)
        return host, int(port)
    else:
        return "", int(value)


class Sync(CLI):

    """
    Multi-host synchronization and communication plugin
    """

    name = 'sync'
    description = "Allows multi-host synchronization and communication"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = "multi-host synchronization"
        group = run_subcommand_parser.add_argument_group(msg)
        group.add_argument("--sync-server", metavar="ADDR:PORT",
                           help="Enable listening on given ADDR and PORT.")
        group.add_argument("--sync", metavar="ADDR:PORT", help="Use this "
                           "address to connect to the sync server (started "
                           "by --sync-server). If --sync-server, it's value "
                           "is used as default for --sync (you can override, "
                           "though)")

    def run(self, args):
        def exit_server(server):
            server.shutdown()
            server.server_close()
        if not hasattr(args, "sync_server"):
            return
        client = args.sync
        server = args.sync_server
        if server:
            if not client:
                client = server
            tcp_server = ThreadedTCPServer(parse_addr(server),
                                           ThreadedTCPRequestHandler)

            server_thread = threading.Thread(target=tcp_server.serve_forever)
            server_thread.setDaemon(True)
            server_thread.start()

            atexit.register(exit_server, tcp_server)

        if client:
            if not hasattr(args, "default_multiplex_tree"):
                raise RuntimeError("Multiplexer required by sync plugin is "
                                   "not avaliable.")
            node = args.default_multiplex_tree.get_node("/plugins/sync", True)
            node.value["addr"], node.value["port"] = parse_addr(client)
