#!/usr/bin/env python

import sys
import subprocess

import sip
sip.setapi('QString', 2)
from PyQt4.QtGui import QApplication


import termwidget

class SysShell:
    """System shell. Test for terminal widget. Don't try to reuse it as a real system shell
    """
    def __init__(self):
        self._term = termwidget.TermWidget()
        self._term.returnPressed.connect(self._onReturnPressed)
        self._term.show()
        self._popen = None

    def _isCommandComplete(self, text):
        def skipQuotes(text):
            quote = text[0]
            text = text[1:]
            endIndex = text.index(quote)
            return text[endIndex:]
        while text:
            if text[0] in ('"', "'"):
                try:
                    text = skipQuotes(text)
                except ValueError:
                    return False
            text = text[1:]
        return True
    
    def _onReturnPressed(self, text):
        if self._isCommandComplete(text):
            self._term.execCurrentCommand()
            
            popen = subprocess.Popen(str(text), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = popen.communicate()
            if stdout:
                self._term.appendOutput(stdout)
            if stderr:
                self._term.appendError(stderr)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    shell = SysShell()

    app.exec_()
