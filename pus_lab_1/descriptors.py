"""Module containing various descriptor classes."""
__author__ = 'Luka Sterbic'

import os


class FileDescriptor(object):
    """
    Class modelling a file descriptor.

    A file descriptor is the description of a file in terms of name,
    author, description and, if known, file id and SP id.

    Attributes:
        name: the filename
        author: the author of the file
        description: a description of the file
        file_id: the id of the file
        com_id: the id of the communicator used by the service
            provider to whom the file belongs
    """
    HEADER = "%5s %3s %-15s %-10s %-43s" % (
        "F_ID", "SP", "File", "Author", "Description")

    def __init__(self, name, author, description):
        """Inits the object with all mandatory fields."""
        self.name = name
        self.author = author
        self.description = description
        self.file_id = -1
        self.com_id = -1

    def __str__(self):
        """Concatenates all the information saved in the descriptor"""
        description = self.description

        if len(description) > 43:
            description = description[:40] + "..."

        return "%5d %3d %-15s %-10s %-43s" % (
            self.file_id,
            self.com_id,
            self.name,
            self.author,
            description
        )

    @staticmethod
    def load(author, path):
        """Loads a list of descriptors for files a the given path."""
        descriptors = []

        if not os.path.isdir(path):
            raise ValueError("The path must be a directory.")

        files = [f for f in os.listdir(path)
                 if os.path.isfile(os.path.join(path, f))]

        for filename in files:
            if filename == ".DS_Store":
                continue

            with open(os.path.join(path, filename)) as file:
                descriptors.append(FileDescriptor(
                    filename,
                    author,
                    file.readline().rstrip()
                ))

        return descriptors


class FileBuffer(object):
    """
    File buffer for text files.

    This file buffer is used during the fetch process of remote files.

    Attributes:
        buffer_id: the id of the buffer
        descriptor: the descriptor of the file from which this buffer
            will load content
        lines: the lines of text loaded in this buffer
    """
    ID_COUNTER = 1

    def __init__(self, descriptor):
        """Inits the object with a file descriptor."""
        self.buffer_id = FileBuffer.ID_COUNTER
        FileBuffer.ID_COUNTER += 1
        self.descriptor = descriptor
        self.lines = []

    def load(self, directory):
        """Loads the content of the file."""
        path = os.path.join(directory, self.descriptor.name)
        with open(path) as file:
            self.lines = file.readlines()

    def save(self, directory, name):
        """Saves the content of the buffer to file."""
        path = os.path.join(directory, name)
        with open(path, "w") as file:
            file.writelines(self.lines)

    def __str__(self):
        """Concatenates the lines of the buffer"""
        return "Buffer %d, %s:\n\t%s" % (
            self.buffer_id,
            self.descriptor.name,
            "\t".join(self.lines)
        )


class SPDescriptor(object):
    """
    Service provider descriptor

    Used to describe a service provider in a distributed environment.

    Attributes:
        com_id: communicator id for the service provider
        name: the name of the service provider
        address: tuple containing the IP address and port for th SP
    """
    def __init__(self, com_id, name, address):
        """Inits the object with id, name and address."""
        self.com_id = com_id
        self.name = name
        self.address = address
