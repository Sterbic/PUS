"""Module containing classes and methods for SP/CR communication."""
__author__ = 'Luka Sterbic'

from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256

RSA_KEY_BITS = 1024
BUFFER_SIZE = 4096


class Certificate(object):
    """
    Class modeling a digital certificate.

    A digital certificate contains a name of an entity and its public
    key in PEM format. It can be signed by passing a private key to
    the sign() method and it can be verified by passing a public key
    to the verify() method.

    Attributes:
        name: the name of the holder of the certificate
        address: tuple containing ip address and port of the holder
        public_key: pem formatted public key of the holder
        com_id: central registry issued id if available
    """
    def __init__(self, name, address, public_key, com_id=0):
        """Inits the object with name and public key."""
        self.name = name
        self.address = address
        self.public_key = public_key
        self.signature = None
        self.com_id = com_id

    def sign(self, key):
        """Signs this certificate with the given private key."""
        self.signature = key.sign(self.hash(), b"")

    def verify(self, key):
        """Verify this certificate with the given public key."""
        return key.verify(self.hash(), self.signature)

    def hash(self):
        """Computes the hash of this certificate."""
        sha = SHA256.new(self.name.encode("ascii"))
        sha.update(self.public_key)
        return sha.digest()


class Message(object):
    """
    A message for the communication between SPs and the CR.

    This class is the only object used for communication between the
    central registry and communicators.

    Attributes:
        msg_type: the type of the message, should be in TYPES
        content: the content of the message
        request: true if the message is a request, false otherwise
    """
    CERTIFICATE = "CERTIFICATE"
    SIGN = "SIGN"
    PUBLISH = "PUBLISH"
    FETCH_SP = "FETCH_SP"
    FETCH_FILE = "FETCH_FILE"
    TYPES = {CERTIFICATE, SIGN, PUBLISH, FETCH_SP, FETCH_FILE}

    def __init__(self, msg_type, content=None, request=True):
        if msg_type not in Message.TYPES:
            raise ValueError("Unknown message type.")

        self.type = msg_type
        self.content = content
        self.request = request


class FileRequest(Message):
    """
    Class implementing a file request message.

    This class is used in the file transfer protocol between two
    communicators. It extends the basic communication class Message
    and ads functionality for hashing, signing and verifying the
    content of the request.

    Attributes:
        buffer: the file buffer used in the request
        src_com_id: com id of the entity that made the request
        username: name of the user that made the request
    """
    def __init__(self, buffer, src_com_id, username):
        """Inits the object with content and username."""
        self.username = username
        self.src_com_id = src_com_id
        self.signature = None
        Message.__init__(self, Message.FETCH_FILE, buffer)

    def sign(self, key):
        """Signs this certificate with the given private key."""
        self.signature = key.sign(self.hash(), b"")

    def verify(self, key):
        """Verify this certificate with the given public key."""
        return key.verify(self.hash(), self.signature)

    def hash(self):
        """Computes the hash of this file request."""
        sha = SHA256.new(self.username.encode("ascii"))
        sha.update(self.type.encode("ascii"))

        if self.content.lines:
            for line in self.content.lines:
                sha.update(line.encode("ascii"))

        descriptor = self.content.descriptor

        hash_string = "%d %d %d %d" % (
            descriptor.com_id,
            self.src_com_id,
            descriptor.com_id,
            descriptor.file_id
        )
        sha.update(hash_string.encode("ascii"))

        return sha.digest()


def get_rsa_key(pem=None):
    """
    Generate a RSA key object.

    Generate a new RSA key object or construct it from the given PEM
    format if the pem argument is defined.

    Args:
        pem: pem representation of the key

    Returns:
        RSA key object
    """
    if pem is None:
        return RSA.generate(RSA_KEY_BITS)
    else:
        return RSA.importKey(pem)
