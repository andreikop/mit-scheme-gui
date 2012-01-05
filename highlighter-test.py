#!/usr/bin/env python

import sys

import sip
sip.setapi('QString', 2)
from PyQt4.QtGui import QApplication, QTextEdit

import highlighter

code = \
"""
(define func (x)
    (map (lambda (y) (+ x y))
        x))
"""

if __name__ == '__main__':
    app = QApplication(sys.argv)

    edit = QTextEdit()
    hl = highlighter.Highlighter(edit)
    
    edit.setPlainText(code)
    edit.show()

    app.exec_()