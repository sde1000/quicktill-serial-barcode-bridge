#!/usr/bin/env python3

import argparse
import logging
from pathlib import Path
from ctypes import CDLL, get_errno
from ctypes.util import find_library
from errno import EINTR
from io import FileIO
import selectors
import socket
import os
import sys
import struct
from typing import Dict, Callable, Optional, NoReturn

WatchCallback = Callable[[int, str], None]

log = logging.getLogger("quicktill-serial-barcode-bridge")
_libc = CDLL(find_library("c") or "libc.so.6")
sel = selectors.DefaultSelector()


class INotify(FileIO):
    CREATE = 0x100
    DELETE_SELF = 0x400
    ONLYDIR = 0x1000000
    ISDIR = 0x40000000

    _event_header = struct.Struct("iIII")

    def __init__(self, log: logging.Logger):
        self.log = log.getChild("INotify")
        fd = _libc.inotify_init1(os.O_NONBLOCK)
        super().__init__(fd, mode='rb')
        self.watches: Dict[int, WatchCallback] = {}
        sel.register(self, selectors.EVENT_READ, self.data_available)

    def add_watch(self, path: Path, mask: int, callback: WatchCallback) -> \
        Optional[int]:  # noqa
        while True:
            rc: int = _libc.inotify_add_watch(
                self.fileno(), os.fsencode(path), mask)
            if rc != -1:
                self.watches[rc] = callback
                return rc
            errno = get_errno()
            if errno != EINTR:
                raise OSError(errno, os.strerror(errno))

    def del_watch(self, wd: int) -> None:
        del self.watches[wd]
        _libc.inotify_rm_watch(self.fileno(), wd)

    def data_available(self) -> None:
        self.log.debug("INotify data available")
        while True:
            data = self.read()
            if not data:
                return
            pos = 0
            while pos < len(data):
                wd, mask, cookie, namesize = self._event_header.unpack_from(
                    data, pos)
                pos += self._event_header.size + namesize
                name = os.fsdecode(
                    data[pos - namesize:pos].split(b'\x00', 1)[0])
                if wd not in self.watches:
                    self.log.debug(
                        "received event for wd %d that no longer exists", wd)
                else:
                    self.watches[wd](mask, name)


class DirWatcher:
    def __init__(self, path: Path, log: logging.Logger, s: socket.socket):
        self.log = log.getChild(f"DirWatcher({path})")
        self.s = s
        self.ino = INotify(self.log)
        self.path = path
        self.parent = path.parent
        if self.path == self.parent:
            self.log.error(
                "Monitoring for barcode scanners in the root directory "
                "is not supported.")
            sys.exit(1)
        self.parent_wd = self.ino.add_watch(
            self.parent, self.ino.CREATE | self.ino.ONLYDIR,
            self.parent_callback)
        self.wd: Optional[int] = None
        if path.exists():
            self.dir_exists()

    def dir_exists(self) -> None:
        self.log.debug("path now exists")
        if not self.path.is_dir():
            self.log.error("path is not a directory")
            sys.exit(1)
        self.wd = self.ino.add_watch(
            self.path,
            self.ino.CREATE | self.ino.DELETE_SELF | self.ino.ONLYDIR,
            self.callback)
        for f in self.path.iterdir():
            Scanner(f, self.s, self.log)

    def parent_callback(self, mask: int, name: str) -> None:
        self.log.debug("parent callback mask=%x name=%s", mask, name)
        if mask & (self.ino.CREATE | self.ino.ISDIR) \
           and name == self.path.name:
            self.dir_exists()

    def callback(self, mask: int, name: str) -> None:
        self.log.debug("callback mask=%x name=%s", mask, name)
        if mask & self.ino.DELETE_SELF:
            self.log.debug("path no longer exists")
            if self.wd:
                self.ino.del_watch(self.wd)
            self.wd = None
        elif mask & self.ino.CREATE:
            Scanner(self.path / name, self.s, self.log)


class Scanner:
    def __init__(self, path: Path, s: socket.socket, log: logging.Logger):
        self.log = log.getChild(f"Scanner({path})")
        self.s = s
        self.path = path
        self.f = open(path)
        os.set_blocking(self.f.fileno(), False)
        sel.register(self.f, selectors.EVENT_READ, self.data_available)
        self.log.info("connected")

    def data_available(self) -> None:
        data = self.f.readline().strip()
        if not data:
            self.log.info("disconnected")
            sel.unregister(self.f)
            self.f.close()
            return
        self.log.info("read %s", data)
        try:
            self.s.send(data.encode("utf-8"))
        except ConnectionRefusedError:
            self.log.debug('udp send: connection refused')


def run(args: argparse.Namespace) -> NoReturn:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((args.host, args.port))
    for d in args.directory:
        DirWatcher(d, log, s)

    while True:
        events = sel.select()
        for key, mask in events:
            key.data()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Serial barcode scanner bridge")
    parser.add_argument(
        '--host', default="127.0.0.1",
        help="Host to deliver barcodes to")
    parser.add_argument(
        '--port', default=8456, type=int,
        help="Port to deliver barcodes to")
    parser.add_argument(
        '--verbose', '-v', default=False, action="store_true",
        help="Print details as barcodes and scanners are detected")
    parser.add_argument(
        '--debug', default=False, action="store_true",
        help="Enable debug output")
    parser.add_argument(
        'directory', nargs="*", type=Path, default=[Path("/dev/barcode")])
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)
    run(args)
