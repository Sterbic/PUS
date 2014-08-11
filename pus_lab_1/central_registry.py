#!/usr/bin/env python3

"""
Module for the central registry functionality.

The script expects two arguments, the IP address and port to be used
for incoming connections.

Usage:
    python3 central_registry.py name port

Args:
    name: the name of the central registry
    ip: the ip address of the central registry
    port: the port on which te central registry listens
"""
from communication import com_structs

__author__ = 'Luka Sterbic'

import sys
import signal
import pickle
import threading
import socketserver

from descriptors import SPDescriptor


class RequestHandler(socketserver.BaseRequestHandler):
    """
    Request handler for SP requests.

    This class handles communicator requests. A communicator can query
    for the certificate of the central registry, it can ask the CR to
    sign its certificate and it can ask the CR to publish its files so
    that other communicators become aware of them.
    """

    def handle(self):
        request = self.request.recv(com_structs.BUFFER_SIZE)
        message = pickle.loads(request)
        message.request = False

        if message.type == com_structs.Message.CERTIFICATE:
            self.print_log(self.client_address, "Sending certificate")
            message.content = self.server.certificate
        elif message.type == com_structs.Message.SIGN:
            certificate = message.content

            self.print_log(
                self.client_address,
                "Signing certificate for %s" % certificate.name
            )

            self.server.register_certificate(message.content)

            self.print_log(
                self.client_address,
                "Assigned com_id %d to %s" % (certificate.com_id,
                                              certificate.name)
            )
        elif message.type == com_structs.Message.PUBLISH:
            files = message.content

            self.print_log(
                self.client_address,
                "Publishing %d files for com_id %d" % (
                    len(files), files[0].com_id)
            )

            self.server.publish(files)
        elif message.type == com_structs.Message.FETCH_SP:
            self.print_log(
                self.client_address,
                "Sending service provider data"
            )
            message.content = self.server.service_providers
        elif message.type == com_structs.Message.FETCH_FILE:
            self.print_log(
                self.client_address,
                "Sending files data"
            )
            message.content = self.server.public_files
        else:
            message.request = True

        self.request.sendall(pickle.dumps(message))

    @staticmethod
    def print_log(address, string):
        """Prints log for given address and string."""
        print("%15s : %-5d - %s" % (address[0], address[1], string))


class CentralRegistry(socketserver.TCPServer):
    """
    Class modelling a central registry.

    Implementation of a central registry as a subclass of a TCPServer.
    The central registry serves communicator requests and on SIGINT
    stops all of its threads.

    Attributes:
        name: the name of this central registry
        address: tuple containing the IP address and port for this CR
        key: RSA key object
        certificate: shareable certificate for this CR
        binary_certificate: binary format of the certificate
        handler_thread: thread for serving communicator requests
        com_id_counter: global communicator id counter
        service_providers: a dictionary of all service providers
            indexed by com_id
        file_id_counter: global file id counter
        public_files: file id indexed dictionary with all publicly
            available files
    """

    def __init__(self, name, address):
        """Inits the object with name and address."""
        print("Initializing central registry %s..." % name)
        print("\t%-15s: %s:%d\n" % ("Address", address[0], address[1]))

        self.name = name
        self.address = address
        self.key = com_structs.get_rsa_key()

        self.certificate = com_structs.Certificate(
            name,
            address,
            self.key.publickey().exportKey("PEM")
        )
        self.binary_certificate = pickle.dumps(self.certificate)

        self.handler_thread = threading.Thread(target=self.serve_forever)

        self.com_id_counter = 1
        self.service_providers = {}

        self.file_id_counter = 1
        self.public_files = {}

        socketserver.TCPServer.__init__(self, address, RequestHandler)

    def start(self):
        """Start handling requests."""
        print("Starting %s server..." % self.name)
        self.handler_thread.start()

        print("Server thread started\n\nServing requests...")
        print("%15s : %-5s - %s" % ("IP address", "Port", "Action"))
        print("-" * 80)

        signal.signal(signal.SIGINT, self.signal_handler)
        self.handler_thread.join()

    def shutdown(self):
        """Shutdown the server."""
        print("Shutting down %s communicator handler thread..." % self.name)
        socketserver.TCPServer.shutdown(self)
        print("Shutdown of %s server completed" % self.name)

    def signal_handler(self, signal_n, _):
        """Intercept a signal and shutdown the server."""
        name = "Unknown signal"

        for key in signal.__dict__.keys():
            if key.startswith("SIG") and getattr(signal, key) == signal_n:
                name = key
                break

        print("-" * 80)
        print("\nIntercepted %s signal" % name)
        self.shutdown()

    def register_certificate(self, certificate):
        """Registers the given communicator certificate."""
        certificate.com_id = self.com_id_counter
        self.com_id_counter += 1

        certificate.sign(self.key)

        descriptor = SPDescriptor(
            certificate.com_id,
            certificate.name,
            certificate.address
        )

        self.service_providers[descriptor.com_id] = descriptor

    def publish(self, files):
        """Adds the given files to the publicly available files."""
        for file_descriptor in files:
            file_descriptor.file_id = self.file_id_counter
            self.file_id_counter += 1
            self.public_files[file_descriptor.file_id] = file_descriptor


def main(name, ip_address, port):
    """
    Main function of this script.

    Starts the central registry at the specified port and waits for
    user requests.

    Args:
        name: the name of the central registry
        ip: the ip address of the central registry
        port: the port of the central registry
    """
    address = (ip_address, int(port))
    central_registry = CentralRegistry(name, address)

    signal_blocker = lambda s, f: print("Blocking the signal")
    signal.signal(signal.SIGINT, signal_blocker)

    central_registry.start()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        exit(1)

    main(*sys.argv[1:])
