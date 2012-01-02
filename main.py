#!/usr/bin/env python

import sys
import sip
sip.setapi('QString', 2)
from PyQt4.QtGui import QApplication

import terminal

app = QApplication(sys.argv)

shell = terminal.SysShell()

app.exec_()