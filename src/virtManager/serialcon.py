#
# Copyright (C) 2006 Red Hat, Inc.
# Copyright (C) 2006 Daniel P. Berrange <berrange@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import gtk
import vte
import os
import gobject
import termios
import tty

class vmmSerialConsole:
    def __init__(self, config, vm):

        self.vm = vm
        self.config = config

        self.window = gtk.Window()
        self.window.hide()
        self.window.set_title(vm.get_name() + " " + _("serial console"))

	self.terminal = vte.Terminal()
	self.terminal.set_cursor_blinks(True)
	self.terminal.set_emulation("xterm")
	self.terminal.set_font_from_string("fixed 10")
	self.terminal.set_scrollback_lines(1000)
	self.terminal.set_audible_bell(False)
	self.terminal.set_visible_bell(True)

        self.terminal.connect("commit", self.send_data)
	self.terminal.show()

	scrollbar = gtk.VScrollbar()
	scrollbar.set_adjustment(self.terminal.get_adjustment())

	box = gtk.HBox()
	box.pack_start(self.terminal)
	box.pack_start(scrollbar)

	self.window.add(box)

        self.ptyio = None
        self.ptysrc = None
        self.ptytermios = None

        self.window.connect("delete-event", self.close)


    def show(self):
        self.opentty()
        self.window.show_all()
        self.window.present()

    def close(self, src=None, ignore=None):
        self.closetty()
        self.window.hide()
        return True

    def opentty(self):
        if self.ptyio != None:
            self.closetty()
        pty = self.vm.get_serial_console_tty()

        if pty == None:
            return
        self.ptyio = os.open(pty, os.O_RDWR | os.O_NONBLOCK | os.O_NOCTTY)
        self.ptysrc = gobject.io_add_watch(self.ptyio, gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP, self.display_data)

        # Save term settings & set to raw mode
        self.ptytermios = termios.tcgetattr(self.ptyio)
        tty.setraw(self.ptyio)

    def closetty(self):
        if self.ptyio == None:
            return
        # Restore term settings
        try:
            termios.tcsetattr(self.ptyio, termios.TCSADRAIN, self.ptytermios)
        except:
            # The domain may already have exited, destroying the pty, so ignore
            pass
        os.close(self.ptyio)
        gobject.source_remove(self.ptysrc)
        self.ptyio = None
        self.ptysrc = None
        self.ptytermios = None

    def send_data(self, src, text, length):
        if self.ptyio != None:
            os.write(self.ptyio, text)

    def display_data(self, src, cond):
        if cond == gobject.IO_IN:
            data = os.read(self.ptyio, 1024)
            self.terminal.feed(data, len(data))
            return True
        else:
            self.closetty()
            return False

