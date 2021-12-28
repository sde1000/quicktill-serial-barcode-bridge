quicktill-serial-barcode-bridge
===============================

This is an interface between barcode scanners that present as USB CDC
devices and the `quicktill` application. Barcode scans are delivered
as UDP packets to localhost:8456.

Any barcode scanner that can be configured to appear as a USB CDC
device should work. This is usually listed in the manual as "USB COM"
or "USB Virtual Serial Port" mode.

If your scanner's USB vendor and product ID are not listed in the file
`60-serial-barcode-scanner.rules`, you will need to add your own udev
rule to enable it to work. Create a file
`/etc/udev/rules.d/60-serial-barcode-scanner.rules` containing a line
like the following:

```
KERNEL=="ttyACM[0-9]*", SUBSYSTEM=="tty", ATTRS{idVendor}=="1eab", ATTRS{idProduct}=="8306", MODE="660", GROUP="dialout", SYMLINK+="barcode/scanner-%n"
```

Substitute in your own values for `idVendor` and `idProduct`; you can
find them by running `usb_devices` and searching for `Driver=cdc_acm`.

After you have created this file, unplug and re-plug your barcode
scanner. A link to the device file should appear in `/dev/barcode`.

Please create an issue on github when you find devices that work but
which are not listed in `60-serial-barcode-scanner.rules`, so I can
add them to future releases.

Copying
-------

quicktill-serial-barcode-bridge is Copyright (C) 2021 Stephen Early <steve@assorted.org.uk>

It is distributed under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see [this
link](http://www.gnu.org/licenses/).

Installing
----------

To build quicktill-serial-barcode-bridge, start with this repository as the
current working directory:

    make install

To build the Debian package:

    dpkg-buildpackage
