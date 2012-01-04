#!/usr/bin/env python
import subprocess
import time
import sys
import threading

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

import sip
sip.setapi('QString', 2)
from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QApplication

import termwidget

class BufferedPopen(subprocess.Popen):
    """Bufferred version of Popen.
    Never locks, but uses unlimited buffers. May eat all the system memory, if something goes wrong.
    Output blocks are split to lines"""
    
    def __init__(self, *args, **kwargs):
        subprocess.Popen.__init__(self, *args, **kwargs)
        
        self._mustDie = False
        self._inQueue = Queue()
        self._outQueue = Queue()
        self._inThread = threading.Thread(target=self._writeInputThread)
        self._outThread = threading.Thread(target=self._readOutputThread)
        self._inThread.start()
        self._outThread.start()
    
    def terminate(self):
        self._mustDie = True
        subprocess.Popen.terminate(self)
        for i in range(5):
            if self.poll() is None:
                time.sleep(0.04)
            else:
                break
        else:
            self.kill()
            self.wait()

        self._inThread.join()
        self._outThread.join()

    def _readOutputThread(self):
        """Reader function. Reads output from process to queue
        """
        # hlamer: Reading output by one character is not effective, but, I don't know 
        # how to implement non-blocking reading of not full lines better
        char = self.stdout.read(1)
        while char:
            self._outQueue.put(char)
            char = self.stdout.read(1)
            

    def _writeInputThread(self):
        """Writer function. Writes data from input queue to process
        """
        while not self._mustDie:
            try:
                text = self._inQueue.get(True, 0.1)
            except Empty:
                continue
            self.stdin.write(text)
    
    def write(self, text):
        """Write data to the subprocess
        """
        self._inQueue.put(text)  # TODO test on big blocks of text. Make nonblocking even if queue is full
    
    def read(self):
        """Read data from the subprocess
        """
        text = ''
        while not self._outQueue.empty():
            text += self._outQueue.get(False)
        return text

class MitSchemeShell:
    """MIT scheme shell. Implements REPL. Graphical frontend for original terminal version.
    """
    def __init__(self):
        self._term = termwidget.TermWidget()
        self._term.returnPressed.connect(self._onReturnPressed)
        self._term.show()
        self._bufferedPopen = BufferedPopen("scheme", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self._processOutputTimer = QTimer()  # I use Qt timer, because we must append data to GUI in the GUI thread
        self._processOutputTimer.timeout.connect(self._processOutput)
        self._processOutputTimer.start(100)

    def __del__(self):
        self._bufferedPopen.terminate()

    def _isCommandComplete(self, text):
        return True
    
    def _onReturnPressed(self, text):
        self._processOutput() # write old output to the log, and only then write fresh input
        if self._isCommandComplete(text):
            self._term.execCurrentCommand()
            self._bufferedPopen.write(text)
    
    def _processOutput(self):
        self._term.appendOutput(self._bufferedPopen.read())

if __name__ == '__main__':
    app = QApplication(sys.argv)

    shell = MitSchemeShell()

    app.exec_()
    
    del shell
