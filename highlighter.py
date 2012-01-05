import re

from PyQt4.QtGui import QColor, QFont, QSyntaxHighlighter, \
                        QTextBlockUserData, QTextCharFormat, QTextCursor, QTextEdit


class _FoundBrace:
    def __init__(self, block, pos, brace):
        self.pos = pos
        self.brace = brace
        self.block = block

class _FoundBracesIterator:
    def __init__(self, block, index, forward):
        self._block = block
        self._index = index
        self._forward = forward
    
    def __iter__(self):
        return self
    
    def next(self):
        while True:
            if not self._block.isValid():
                raise StopIteration()
            foundBraces = self._block.userData().foundBraces
            if self._forward:
                if self._index < len(foundBraces):
                    ret = foundBraces[self._index]
                    self._index += 1
                    return ret
                else:  # end of block, switch block and iterate again
                    self._block = self._block.next()
                    self._index = 0
            else:
                if self._index >= 0:
                    ret = foundBraces[self._index]
                    self._index -= 1
                    return ret
                else:  # end of block, switch block and iterate again
                    self._block = self._block.previous()
                    if self._block.isValid():
                        self._index = len(self._block.userData().foundBraces) - 1

def _makeFormat(bg=None, fg=None, bold=False):
    format = QTextCharFormat()
    if bg is not None:
        format.setBackground(QColor(bg))
    if fg is not None:
        format.setForeground(QColor(fg))
    if bold:
        format.setFontWeight(QFont.Bold)

    return format

# TODO have own QPalette
DEFAULT_STYLE = {   'defaultBackground':    QColor("#ffffff"),
                    'defaultForeground':    QColor("#000000"),
                    'matchedBrace':         _makeFormat(bg="#ffff7f", fg="#ff0000"),
                    'unMatchedBrace':       _makeFormat(bg="#ff0000", fg="#ffffff"),
                    'keyword':              _makeFormat(bold=True),
                    'standardFunction':     _makeFormat(fg="#000080", bold=True),
                    'number':               _makeFormat(fg='#008080'),
                }

class Highlighter(QSyntaxHighlighter):
    """Scheme (Lisp dialect) syntax highlighter
    """
    KEYWORDS = ("case\-lambda", "call/cc", "class", "define\-class", "exit\-handler", "field", "import", "inherit", 
    "init\-field", "interface", "let\*\-values", "let\-values", "let/ec", "mixin", "opt\-lambda", "override", "protect",
    "provide", "public", "rename", "require", "require\-for\-syntax", "syntax", "syntax\-case", "syntax\-error", "unit/sig",
    "unless", "when", "with\-syntax", "and", "begin", "call\-with\-current\-continuation", "call\-with\-input\-file",
    "call\-with\-output\-file", "case", "cond", "define", "define\-syntax", "delay", "do", "dynamic\-wind", "else",
    "for\-each", "if", "lambda", "let", "let\*", "let\-syntax", "letrec", "letrec\-syntax", "map", "or", "syntax\-rules")
    
    STANDARD_FUNCTIONS = ("'", "\*", "\+", ",", ",@", "\-", "\.\.\.", "/", ";", "<", "<=", "=", "<=", ">", ">=", "`", "abs",
    "acos", "angle", "append", "apply", "asin", "assoc", "assq", "assv", "atan", "boolean\?", "caar", "cadr",
    "call\-with\-input\-file", "call\-with\-output\-file", "call\-with\-values", "car", "cdddar", "cddddr", "cdr", "ceiling", 
    "char\->integer", "char\-alphabetic\?", "char\-ci<=\?", "char\-ci<\?", "char\-ci=\?", "char\-ci>=\?", "char\-ci>\?",
    "char\-downcase", "char\-lower\-case\?", "char\-numeric\?", "char\-ready\?", "char\-upcase", "char\-upper\-case\?",
    "char\-whitespace\?", "char<=\?", "char<\?", "char=\?", "char>=\?", "char>\?", "char\?", "close\-input\-port",
    "close\-output\-port", "complex\?","cons", "cos", "current\-input\-port", "current\-output\-port", "denominator",
    "display", "eof\-object\?", "eq\?",
    "equal\?", "eqv\?", "eval", "even\?", "exact\->inexact", "exact\?", "exp", "expt", "#f", "floor", "force", "gcd", 
    "imag\-part", "inexact\->exact", "inexact\?", "input\-port\?", "integer\->char", "integer\?", "interaction\-environment",
    "lcm", "length", "list", "list\->string", "list\->vector", "list\-ref", "list\-tail", "list\?", "load", "log",
    "magnitude", "make\-polar", "make\-rectangular", "make\-string", "make\-vector", "max", "member", "memq", "memv", "min",
    "modulo", "negative\?", "newline", "not", "null\-environment", "null\?", "number\->string", "number\?", "numerator",
    "odd\?", "open\-input\-file", "open\-output\-file", "output\-port\?", "pair\?", "peek\-char", "port\?", "positive\?",
    "procedure\?", "quasiquote", "quote", "quotient", "rational\?", "rationalize", "read", "read\-char", "real\-part",
    "real\?", "remainder", "reverse", "round", "scheme\-report\-environment", "set!", "set\-car!", "set\-cdr!", "sin",
    "sqrt", "string", "string\->list", "string\->number", "string\->symbol", "string\-append", "string\-ci<=\?",
    "string\-ci<\?", "string\-ci=\?", "string\-ci>=\?", "string\-ci>\?", "string\-copy", "string\-fill!", "string\-length",
    "string\-ref", "string\-set!", "string<=\?", "string<\?", "string=\?", "string>=\?", "string>\?", "string\?", "substring", 
    "symbol\->string", "symbol\?", "#t", "tan", "transcript\-off", "transcript\-on", "truncate", "values", "vector", 
    "vector\->list", "vector\-fill!", "vector\-length", "vector\-ref", "vector\-set!", "with\-input\-from\-file",
    "with\-output\-to\-file", "write", "write\-char", "zero\?")
    
    NUMBERS = (r"\d", )

    def __init__(self, textEdit):
        QSyntaxHighlighter.__init__(self, textEdit)
        self._textEdit = textEdit
        textEdit.setFont(QFont("Monospace"))

        self._bracePattern = re.compile('[\(\)]')

        self._patternsToApply = { 'keyword':          self._makePatternFromList(self.KEYWORDS),
                                  'standardFunction': self._makePatternFromList(self.STANDARD_FUNCTIONS),
                                  'number':           self._makePatternFromList(self.NUMBERS),
                                }

        textEdit.cursorPositionChanged.connect(self._onCursorPositionChanged)

    def _makePatternFromList(self, strings):
        for s in strings:
            if s[0].isalnum():
                s = r'\b' + s
            else:
                s = r'[^\b]' + s
            if s[-1].isalnum():
                s = s + r'\b'
            else:
                s = s + r'[^\b]'

        pattern = '|'.join(strings)  # join to one pattern
        return re.compile(pattern)

    def highlightBlock(self, text):
        for style, pattern in self._patternsToApply.items():
            for match in pattern.finditer(text):
                self.setFormat(match.start(), len(match.group(0)), DEFAULT_STYLE[style])

        self._generateBraceIndex(text)
    
    def _generateBraceIndex(self, text):
        data = self.currentBlockUserData()
        if data is None:
            data = QTextBlockUserData()
        foundBraces = []
        for match in self._bracePattern.finditer(text):
            foundBraces.append(_FoundBrace(self.currentBlock(), match.start(), match.group(0)))
        data.foundBraces = foundBraces
        self.setCurrentBlockUserData(data)

    def _onCursorPositionChanged(self):
        cursor = self._textEdit.textCursor()
        pos = None
        brace = None
        if not cursor.atBlockStart():
            charBefore = cursor.block().text()[cursor.positionInBlock() - 1]
            if self._bracePattern.match(charBefore):
                pos = cursor.positionInBlock() - 1
                brace = charBefore
        if brace is None:
            if not cursor.atBlockEnd():
                charAfter = cursor.block().text()[cursor.positionInBlock()]
                if self._bracePattern.match(charAfter):
                    pos = cursor.positionInBlock()
                    brace = charAfter
        
        selections = []
        if brace is not None:
            matchedBrace = self._findMatching(cursor.block(), pos, brace)
            if matchedBrace is not None:
                selections.append(self._makeExtraSelection(matchedBrace.block, matchedBrace.pos, True))
                selections.append(self._makeExtraSelection(cursor.block(), pos, True))
            else:
                selections.append(self._makeExtraSelection(cursor.block(), pos, False))
        self._textEdit.setExtraSelections(selections)

    def _findMatching(self, block, pos, brace):
        foundBraces = block.userData().foundBraces
        braceIndex = None
        for index, foundBrace in enumerate(foundBraces):
            if foundBrace.pos == pos:
                braceIndex = index
                break;
        else:
            assert 0  # Brace must be found!
        
        forward = brace == '('
        if forward:
            startIndex = braceIndex + 1
        else:
            startIndex = braceIndex - 1
        openedCount = 1
        for foundBrace in _FoundBracesIterator(block, startIndex, forward):
            if foundBrace.brace == brace:
                openedCount += 1
            else:
                openedCount -= 1
            if openedCount == 0:
                return foundBrace
        
        return None

    def _makeExtraSelection(self, block, pos, matched):
        sel = QTextEdit.ExtraSelection()
        sel.cursor = QTextCursor(block)
        sel.cursor.setPosition(block.position() + pos, QTextCursor.MoveAnchor)
        sel.cursor.setPosition(block.position() + pos + 1, QTextCursor.KeepAnchor)
        if matched:
            sel.format = DEFAULT_STYLE['matchedBrace']
        else:
            sel.format = DEFAULT_STYLE['unMatchedBrace']
        return sel