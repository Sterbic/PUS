"""Module containing the Communicator server class."""
__author__ = 'Luka Sterbic'

import pickle
import threading
import socket
import socketserver

import communication.com_structs as com
from communication.com_structs import Message, Certificate, FileRequest


class CommunicatorHandler(socketserver.BaseRequestHandler):
    """
    Handler for requests received by the Communicator class.

    This class implements a handler for the exchange of certificates
    verified by the central registry.
    """
    def handle(self):
        request = self.request.recv(com.BUFFER_SIZE)
        message = pickle.loads(request)
        message.request = False

        if message.type == Message.CERTIFICATE:
            certificate = message.content

            if self.server.register_certificate(certificate):
                message.content = self.server.certificate
            else:
                message.content = None
        elif message.type == Message.FETCH_FILE:
            key = self.server.com_keys[message.src_com_id]

            if message.verify(key):
                self.server.loader(message.content)
                message.sign(self.server.key)
            else:
                message.request = True

        self.request.sendall(pickle.dumps(message))


class Communicator(socketserver.TCPServer):
    """
    Communication middleware for service providers.

    This class handles the communication in the public key
    infrastructure backed by a central registry. Each instance creates
    its pair of RSA key and its certificate which is validates by the
    central registry. Validated certificates can be exchanged between
    communicators without the need to contact the central registry.

    Attributes:
        name: the name of the entity using this communicator
        address: tuple containing the IP address and port of the
            entity using this communicator
        cr_address: tuple containing the CRs IP address and port
        loader: loader function for filling file buffer content
        key: RSA key object
        certificate: the certificate of this communicator
        com_certificates: com id indexed dictionary with certificates of
            the other communicators
        com_keys: com id indexed dictionary of all other communicators
            public keys
        communicators: com id indexed dictionary of all other known
            communicators
        cr_certificate: certificate of the CR
        cr_key: public key of the CR
        handler_thread: handles requests from other communicators
    """

    def __init__(self, name, address, cr_address, loader):
        """Inits the object with name, address and CR address."""
        self.name = name
        self.address = address
        self.cr_address = cr_address
        self.loader = loader

        self.key = com.get_rsa_key()
        self.certificate = Certificate(
            name,
            address,
            self.key.publickey().exportKey('PEM')
        )
        self.com_certificates = {}
        self.com_keys = {}
        self.communicators = {}

        print("\nQuerying CR for its certificate...")
        self.cr_certificate = self.__get_certificate(cr_address)
        print("Received certificate for central registry %s\n"
              % self.cr_certificate.name)

        self.cr_key = com.get_rsa_key(self.cr_certificate.public_key)

        print("Requesting certificate signature for %s..." % name)
        self.certificate = self.__sign_certificate()
        print("Received certificate signed by %s" % self.cr_certificate.name)
        print("Received global id %d\n" % self.certificate.com_id)

        self.handler_thread = threading.Thread(target=self.serve_forever)

        socketserver.TCPServer.__init__(self, address, CommunicatorHandler)

    def __sign_certificate(self):
        """Signs the certificate of this communicator."""
        message = Message(Message.SIGN, self.certificate)
        return self.__send_and_get_reply(message, self.cr_address)

    def __exchange_certificate(self, com_address):
        """Attempts to exchange certificates with another entity."""
        com_certificate = self.__get_certificate(com_address, self.certificate)
        return self.register_certificate(com_certificate)

    def register_certificate(self, certificate):
        """Attempts to register the given certificate."""
        if certificate is not None:
            if certificate.verify(self.cr_key):
                self.com_certificates[certificate.com_id] = certificate
                self.com_keys[certificate.com_id] = com.get_rsa_key(
                    certificate.public_key)
                return True

        return False

    def start(self):
        """Starts the communicator."""
        print("Starting communicator handler thread...")
        self.handler_thread.start()
        print("Communicator handler thread started")

    def publish(self, files):
        """Publish all the given files on the central registry."""
        for file_descriptor in files:
            file_descriptor.com_id = self.certificate.com_id

        message = Message(Message.PUBLISH, files)
        return self.__send_and_get_reply(message, self.cr_address)

    def fetch_remote(self):
        """Contacts the CR for sp and file descriptor data."""
        self.communicators = self.__send_and_get_reply(
            Message(Message.FETCH_SP),
            self.cr_address
        )
        files = self.__send_and_get_reply(
            Message(Message.FETCH_FILE),
            self.cr_address
        )

        return dict((file_id, file) for file_id, file in files.items()
                    if file.com_id != self.certificate.com_id)

    def fetch_file(self, buffer, username):
        """Fetches the content of a remote file."""
        print("Fetching remote file %s..." % buffer.descriptor.name)

        com_id = buffer.descriptor.com_id
        address = self.communicators[com_id].address

        if com_id in self.com_certificates:
            print("File is on trusted service provider %d" % com_id)
        else:
            print("File is on unknown service provider %d" % com_id)
            print("Attempting certificate exchange...")

            if not self.__exchange_certificate(address):
                return None
            else:
                print("Certificate exchange completed successfully")

        message = FileRequest(buffer, self.certificate.com_id, username)
        message.sign(self.key)

        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.connect(address)

        soc.sendall(pickle.dumps(message))
        reply = soc.recv(com.BUFFER_SIZE)

        message = pickle.loads(reply)

        if message.request:
            print("Service provider %d refused request" % com_id)
        else:
            print("Verifying received message...")

            if message.verify(self.com_keys[com_id]):
                print("Message verified successfully")
            else:
                print("Message verification failed")

        return message.content

    @staticmethod
    def __get_certificate(address, content=None):
        """Gets the certificate of the entity at the given address."""
        message = Message(Message.CERTIFICATE, content)
        return Communicator.__send_and_get_reply(message, address)

    @staticmethod
    def __send_and_get_reply(message, address):
        """Sends the given message and return the server reply."""
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.connect(address)

        soc.sendall(pickle.dumps(message))

        reply = soc.recv(com.BUFFER_SIZE)
        return pickle.loads(reply).content
