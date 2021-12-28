.PHONY: install all

# Places to install to
sbindir=usr/sbin
systemddir=lib/systemd/system
udevdir=lib/udev/rules.d

all:

install:
	install -d $(DESTDIR)/$(sbindir)
	install -d $(DESTDIR)/$(systemddir)
	install -d $(DESTDIR)/$(udevdir)
	install -m 755 quicktill-serial-barcode-bridge.py $(DESTDIR)/$(sbindir)/quicktill-serial-barcode-bridge
	install -m 644 quicktill-serial-barcode-bridge.service $(DESTDIR)/$(systemddir)
	install -m 644 60-serial-barcode-scanner.rules $(DESTDIR)/$(udevdir)
