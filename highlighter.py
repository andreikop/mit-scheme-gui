import re

from PyQt4.QtGui import QColor, QSyntaxHighlighter, \
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

class Style:
    def __init__(self):
        self.defaultBackground = QColor("#ffffff")
        self.defaultForeground = QColor("#000000")
        # TODO generate own QPalette
        self.matchedBrace = self._makeFormat("#ffff7f", "#ff0000")
        self.unMatchedBrace = self._makeFormat("#ff0000", "#ffffff")
    
    def _makeFormat(self, background, foreground):
        format = QTextCharFormat()
        format.setBackground(QColor(background))
        format.setForeground(QColor(foreground))
        return format

class Highlighter(QSyntaxHighlighter):
    """Scheme (Lisp dialect) syntax highlighter
    """

    def __init__(self, textEdit):
        QSyntaxHighlighter.__init__(self, textEdit)
        self._textEdit = textEdit

        self._style = Style()
        
        #self._textEdit.setTextBackgroundColor(self._style.defaultBackground)
        #self._textEdit.setTextColor(self._style.defaultForeground)

        self._bracePattern = re.compile('[\(\)]')

        textEdit.cursorPositionChanged.connect(self._onCursorPositionChanged)

    def highlightBlock(self, text):
        #self.setFormat(0, 7, QColor("red"))
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
            sel.format = self._style.matchedBrace
        else:
            sel.format = self._style.unMatchedBrace
        return sel
