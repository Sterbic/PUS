#!/usr/bin/env python3

"""
Module for the service provider functionality.

The script expects five arguments: the name of the service provider,
the port to be used by the service provider, the ip address and
port of the central registry and the path to the configuration file
with user information.

Usage:
    python3 service_provider.py name port cr_ip cr_port config

Args:
    name: the name of the service provider
    ip: the ip address of the central registry
    port: the port of the service provider
    cr_ip: the ip address of the central registry
    cr_port: the port of the central registry
    config: path to the configuration file
"""
__author__ = 'Luka Sterbic'

import sys
import getpass
import signal

from descriptors import FileDescriptor, FileBuffer
from communication.communicator import Communicator


class User(object):
    """
    Class modelling an SP user.

    Class modeling a service provider user. Each user has a username,
    a password and a home directory where all his files are stored.

    Attributes:
        name: the user's username
        password: the user's password
        home_dir: the user's home directory
        buffers: buffer_id indexed dictionary of all open buffers
    """

    def __init__(self, name, password, home_dir):
        """Inits the object with name, password and home directory."""
        self.name = name
        self.password = password
        self.home_dir = home_dir
        self.buffers = {}

    def __str__(self):
        """Returns the concatenation of all User attributes."""
        return "%-10s %-10s %s" % (self.name, self.password, self.home_dir)


class ServiceProvider(object):
    """
    Class modelling a service provider.

    Implementation of a service provider for multiple users with file
    file sharing capabilities. All communication is to be considered
    authentic when signed with a CR approved public key. The service
    provider is a subclass of a TCPServer and handles requests from
    other service providers.

    Attributes:
        name: the SP's name
        users: a username indexed dictionary  of all users
        files: a list of files
        files_by_id: file id indexed dictionary of all files
        files_by_user: username indexed dictionary of all files
        active_user: the currently active user
        remote_files: file_id indexed dictionary of remote files
        communicator: object used to communicate with other providers
    """

    def __init__(self, name, address, cr_address, config):
        """Inits the object with name, address and CR address."""
        print("Initializing service provider %s..." % name)
        print("\t%-15s: %s:%d" % ("Address", address[0], address[1]))
        print("\t%-15s: %s:%d" % ("CR address", cr_address[0], cr_address[1]))
        print("\t%-15s: %s" % ("Config file", config))

        self.name = name

        self.users = {}
        self.files = []
        self.files_by_id = {}
        self.files_by_user = {}

        self.active_user = None

        self.init(config)

        self.remote_files = {}
        self.communicator = Communicator(
            name,
            address,
            cr_address,
            self.load_buffer
        )

    def init(self, config):
        """Configures user and file lists with the given config."""
        print("\nLoading users...")

        with open(config) as file:
            while True:
                line = file.readline().rstrip()

                if not line:
                    break

                user = User(*line.split())

                if user.name in self.users:
                    print("Warning: skipping duplicate username")
                else:
                    self.users[user.name] = user

        print("\t%-10s %-10s %s" % ("Username", "Password", "Home directory"))
        for user in self.users.values():
            print("\t%s" % user)

        print("\nLoading files...")
        for user in self.users.values():
            print("\tLoading files for user %s:" % user.name)

            descriptors = FileDescriptor.load(user.name, user.home_dir)
            for file in descriptors:
                print("\t\t%s" % file.name)

            self.files.extend(descriptors)

    def build_indexes(self):
        """Build file descriptor indexes."""
        for file_descriptor in self.files:
            self.files_by_id[file_descriptor.file_id] = file_descriptor

            file_list = self.files_by_user.get(file_descriptor.author, [])
            file_list.append(file_descriptor)

            self.files_by_user[file_descriptor.author] = file_list

    def create_buffer(self, file_id):
        """Creates and loads a file buffer."""
        buffer = FileBuffer(self.files_by_id[file_id])

        self.load_buffer(buffer)
        self.active_user.buffers[buffer.buffer_id] = buffer

        return buffer

    def load_buffer(self, buffer):
        """Load the content of a file into the given buffer."""
        directory = self.users[buffer.descriptor.author].home_dir
        buffer.load(directory)

    def run(self):
        """Starts the service provider."""
        print("Publishing files on central registry %s..."
              % self.communicator.cr_certificate.name)
        self.files = self.communicator.publish(self.files)
        print("The files were successfully published\n")

        print("Building indexes...")
        self.build_indexes()
        print("File descriptor indexes ready\n")

        signal_blocker = lambda s, f: print("Blocking the signal")
        signal.signal(signal.SIGINT, signal_blocker)
        self.communicator.start()
        signal.signal(signal.SIGINT, self.signal_handler)

        while True:
            if self.active_user is None:
                print("-" * 80)
                if not self.do_login():
                    break

                print("-" * 80)

            command = input("%s$ " % self.active_user.name)
            tokens = command.split()

            if not tokens:
                continue

            if tokens[0] == "logout":
                print("logging out")
                self.active_user = None
            elif tokens[0] == "quit":
                break
            elif tokens[0] == "ls" and len(tokens) == 2:
                self.do_ls(tokens)
            elif tokens[0] == "fetch" and len(tokens) == 2:
                self.do_fetch(tokens)
            elif tokens[0] == "clear":
                self.do_clear(tokens)
            elif tokens[0] == "save" and len(tokens) == 3:
                self.do_save(tokens)
            else:
                print("Unknown command")

        self.shutdown()

    def do_login(self):
        """Asks the user for login parameters."""
        attempts = 3
        while attempts:
            attempts -= 1

            username = input("Username: ")

            if username not in self.users:
                print("The entered username does not exist")
                continue

            user = self.users[username]
            password = getpass.getpass()

            if password == user.password:
                print("Login successful")
                self.active_user = user
                return True

            print("Wrong password")

        return False

    def do_ls(self, tokens):
        """Executes the ls command."""
        if tokens[1] == "my":
            if not self.files_by_user[self.active_user.name]:
                print("No files")
            else:
                print(FileDescriptor.HEADER)
                for file in self.files_by_user[self.active_user.name]:
                    print(file)
        elif tokens[1] == "local":
            print(FileDescriptor.HEADER)
            for user in self.users:
                for file in self.files_by_user[user]:
                    print(file)
        elif tokens[1] == "remote":
            if not self.remote_files:
                print("No remote files")
            else:
                print(FileDescriptor.HEADER)
                for file in self.remote_files.values():
                    print(file)
        elif tokens[1] == "buffers":
            if not self.active_user.buffers:
                print("No active file buffers")
            else:
                for buffer_id in self.active_user.buffers:
                    buffer = self.active_user.buffers[buffer_id]
                    print("%3d %s" % (
                        buffer_id,
                        buffer.descriptor.name
                    ))
        else:
            print("Unknown ls command")

    def do_fetch(self, tokens):
        """Executes the fetch command."""
        if tokens[1] == "remote":
            print("Fetching remote files...")
            self.remote_files = self.communicator.fetch_remote()
            print("Fetched descriptors for %d files"
                  % len(self.remote_files))
        else:
            try:
                file_id = int(tokens[1])

                if file_id in self.files_by_id:
                    buffer = self.create_buffer(file_id)
                elif file_id in self.remote_files:
                    buffer = FileBuffer(self.remote_files[file_id])

                    buffer = self.communicator.fetch_file(
                        buffer,
                        self.active_user.name
                    )

                    self.active_user.buffers[buffer.buffer_id] = buffer

                    if not buffer.lines:
                        return
                else:
                    raise ValueError

                print(buffer)
                return
            except ValueError:
                print("Illegal fetch command")

    def do_clear(self, tokens):
        """Executes the clear command."""
        if len(tokens) == 1:
            print("Clearing all buffers...")
            self.active_user.buffers = {}
        elif len(tokens) == 2:
            try:
                buffer_id = int(tokens[1])

                if buffer_id in self.active_user.buffers:
                    print("Clearing buffer %d..." % buffer_id)
                    del self.active_user.buffers[buffer_id]
                else:
                    print("The given buffer id is not in use")
            except ValueError:
                print("Illegal buffer id")
        else:
            print("Illegal clear command")

    def do_save(self, tokens):
        """Executes the save command."""
        try:
            buffer_id = int(tokens[1])

            if buffer_id not in self.active_user.buffers:
                print("The buffer %d is not in use" % buffer_id)
            else:
                self.active_user.buffers[buffer_id].save(
                    self.active_user.home_dir,
                    tokens[2]
                )
                print("Buffer %d saves successfully" % buffer_id)
        except ValueError:
            print("Illegal save command")
        except IOError:
            print("An error has occurred while writing to file")

    def shutdown(self):
        """Shutdown this service provider."""
        print("-" * 80)
        print("Shutting down service provider...")
        print("Shutting down communicator handler thread...")

        self.communicator.shutdown()

        print("Shutdown of communicator thread completed")
        print("Shutdown completed for %s" % self.name)

    def signal_handler(self, signal_n, _):
        """Intercept a signal and shutdown the service provider."""
        name = "Unknown signal"

        for key in signal.__dict__.keys():
            if key.startswith("SIG") and getattr(signal, key) == signal_n:
                name = key
                break

        print("\nIntercepted %s signal" % name)
        self.shutdown()
        sys.exit(0)


def main(name, ip, port, cr_ip, cr_port, config):
    """
    Main function of this script.

    Starts the service provider at the specified port and waits for
    user input.

    Args:
        name: the name of the service provider
        ip: the ip address of the central registry
        port: the port of the service provider
        cr_ip: the ip address of the central registry
        cr_port: the port of the central registry
        config: path to the configuration file
    """
    address = (ip, int(port))
    cr_address = (cr_ip, int(cr_port))

    sp = ServiceProvider(name, address, cr_address, config)
    sp.run()


if __name__ == "__main__":
    if len(sys.argv) != 7:
        print(__doc__)
        exit(1)

    main(*sys.argv[1:])
