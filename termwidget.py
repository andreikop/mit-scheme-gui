import cgi

from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QColor, QLineEdit, QPalette, QTextEdit, QVBoxLayout, QWidget

class TermWidget(QWidget):
    """Widget wich represents terminal. It only displays text and allows to enter text.
    All highlevel logic should be implemented by client classes

    User pressed Enter. Client class should decide, if command must be executed or user may continue edit it
    """

    returnPressed = pyqtSignal(unicode)

    def __init__(self, *args):
        QWidget.__init__(self, *args)
        self._browser = QTextEdit(self)
        self._browser.setReadOnly(True)

        self._edit = QLineEdit(self)
        self._edit.returnPressed.connect(self._onReturnPressed)
        self.setFocusProxy(self._edit)
        self._edit.setFocus()

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._browser)
        layout.addWidget(self._edit)
        
        self._browser.append(self._format('in', 'hello, world'))
        self._browser.append(self._format('err', 'hello, world'))
            
    def _format(self, style, text):
        """Convert text to HTML for inserting it to browser
        """
        assert style in ('in', 'out', 'err')

        text = cgi.escape(text)
        text = text.replace('\n', '<br/>')
        
        if style != 'out':
            defBg = self._browser.palette().color(QPalette.Base)
            h, s, v, a = defBg.getHsvF()
            
            if style == 'in':
                if v > 0.5:  # white background
                    v = v - (v / 8)  # make darker
                else:
                    v = v + ((1 - v) / 4)  # make ligher
            else:  # err
                if v < 0.5:
                    v = v + ((1 - v) / 4)  # make ligher

                if h == -1:  # make red
                    h = 0
                    s = .4
                else:
                    h = h + ((1 - h) * 0.5)  # make more red
            
            bg = QColor.fromHsvF(h, s, v).name()
            text = '<span style="background-color: %s;">%s</span>' % (bg, text)
        
        
        return text
        
        
    def echo(self):
        """Append text from input to output
        """
        self._browser.append(self._format('in', self._edit.text()))
    
    def appendOutput(self, text):
        """Appent text to output widget
        """
        self._browser.append(self._format('out', text))

    def appendError(self, text):
        """Appent error text to output widget. Text is drawn with red background
        """
        self._browser.append(self._format('err', text))

    def clearEdit(self):
        """Clear edit line
        """
        self._edit.clear()

    def _onReturnPressed(self):
        """Handler of Enter pressing in the lineedit
        """
        self.returnPressed.emit(self._edit.text())
