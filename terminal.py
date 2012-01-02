import subprocess

import termwidget

class SysShell:
    """System shell. Test for terminal widget
    """
    def __init__(self):
        self._term = termwidget.TermWidget()
        self._term.returnPressed.connect(self._onReturnPressed)
        self._term.show()
        self._popen = None
    
    def _onReturnPressed(self, text):
        self._term.echo()
        self._term.clearEdit()
        
        popen = subprocess.Popen(str(text), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = popen.communicate()
        if stdout:
            self._term.appendOutput(stdout)
        if stderr:
            self._term.appendError(stderr)
