#!/usr/bin/env python
import subprocess
import time
import sys
import threading
import os
import copy
import re

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

import sip
sip.setapi('QString', 2)
from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QApplication

import termwidget
import highlighter


class BufferedPopen:
    """Bufferred version of Popen.
    Never locks, but uses unlimited buffers. May eat all the system memory, if something goes wrong.
    Output blocks are split to lines"""
    
    def __init__(self, command):
        self._command = command
        
        self._inQueue = Queue()
        self._outQueue = Queue()

        self._inThread = None
        self._outThread = None

    def start(self):
        env = copy.copy(os.environ)
        env['COLUMNS'] = str(2**16)  # Don't need to break lines in the mit scheme. It will be done by text edit
        env['LINES'] = '25'
        self._popen = subprocess.Popen(self._command,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

        self._inThread = threading.Thread(target=self._writeInputThread)
        self._outThread = threading.Thread(target=self._readOutputThread)

        self._mustDie = False
        self._inThread.start()
        self._outThread.start()

    def stop(self):
        self._mustDie = True
        
        try:
            self._popen.terminate()
        except OSError:  # OK, it is already dead
            pass
            
        for i in range(5):
            if self._popen.poll() is None:
                time.sleep(0.04)
            else:
                break
        else:
            self._popen.kill()
            self._popen.wait()

        if self._inThread.is_alive():
            self._inThread.join()
        if self._outThread.is_alive():
            self._outThread.join()
    
    def isAlive(self):
        return self._popen.poll() is None

    def _readOutputThread(self):
        """Reader function. Reads output from process to queue
        """
        # hlamer: Reading output by one character is not effective, but, I don't know 
        # how to implement non-blocking reading of not full lines better
        char = self._popen.stdout.read(1)
        while char:
            self._outQueue.put(char)
            char = self._popen.stdout.read(1)
            

    def _writeInputThread(self):
        """Writer function. Writes data from input queue to process
        """
        while not self._mustDie:
            try:
                text = self._inQueue.get(True, 0.1)
            except Empty:
                continue

            self._popen.stdin.write(text)

    def write(self, text):
        """Write data to the subprocess
        """
        if not self.isAlive():  # Ooops, the process is dead
            raise RuntimeWarning("Process is not running")
        self._inQueue.put(text)  # TODO test on big blocks of text. Make nonblocking even if queue is full

    def readOutput(self):
        """Read stdout data from the subprocess
        """
        text = ''
        while not self._outQueue.empty():
            text += self._outQueue.get(False)
        return text

class _MitSchemeTermWidget(termwidget.TermWidget):
    def __init__(self, mitScheme, *args):
        termwidget.TermWidget.__init__(self, *args)
        self._mitScheme = mitScheme
        self._hl = highlighter.Highlighter(self._edit)

    def isCommandComplete(self, text):
        # TODO support comments
        # Stage 1: remove strings
        index = 0
        foundStrings = []
        while True:
            try:
                index = text.index('"', index)
            except ValueError:
                break;
            
            try:
                endIndex = text.index('"', index + 1)
            except ValueError:
                return False

            foundStrings.append((index, endIndex))
            index = endIndex + 1

        for foundString in foundStrings[::-1]:  # from the last found string
            text = text[:foundString[0]] + text[foundString[1] + 1:]  # remove found string
        
        # Stage 2: calculate braces
        # Let's MIT scheme check if braces are placed correctly. We just check count
        if text.count('(') != text.count(')'):
            return False
        
        return True

    def childExecCommand(self, text):
        self._mitScheme.execCommand(text)

class MitSchemeShell:
    """MIT scheme shell. Implements REPL. Graphical frontend for original terminal version.
    """
    def __init__(self):
        self._term = _MitSchemeTermWidget(self)
        
        self._term.show()
        
        self._processOutputTimer = QTimer()  # I use Qt timer, because we must append data to GUI in the GUI thread
        self._processOutputTimer.timeout.connect(self._processOutput)
        self._processOutputTimer.setInterval(100)

        self._bufferedPopen = BufferedPopen("scheme")
        self._schemeIsRunning = False
        
        self._term.appendOutput("Execute any command to run scheme interpreter\n")

    def __del__(self):
        self.stop()
    
    def start(self):
        self._bufferedPopen.start()
        self._processOutputTimer.start()
        self._schemeIsRunning = True

    def stop(self):
        self._processOutputTimer.stop()
        self._bufferedPopen.stop()
        self._schemeIsRunning = False
    
    def execCommand(self, text):
        if not self._schemeIsRunning:
            self.start()
        self._processOutput() # write old output to the log, and only then write fresh input
        self._bufferedPopen.write(text)
    
    def _processOutput(self):
        output = self._bufferedPopen.readOutput()
        if output:
            self._term.appendOutput(output)
        if self._schemeIsRunning and not self._bufferedPopen.isAlive():
            self._term.appendError("Interpreter process exited. Execute any command to run it again\n")
            self.stop()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    shell = MitSchemeShell()

    app.exec_()

    shell.stop()
