#!/usr/bin/env python

import sys

import sip
sip.setapi('QString', 2)
from PyQt4.QtGui import QApplication, QTextEdit

import highlighter

code = \
"hello, world"

if __name__ == '__main__':
    app = QApplication(sys.argv)

    edit = QTextEdit()
    hl = highlighter.SchemeHighlighter(edit)
    
    edit.setPlainText(code)
    edit.show()

    app.exec_()
