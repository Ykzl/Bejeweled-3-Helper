import sys
import time
from pynput import keyboard
from PyQt5.QtCore import QDateTime, QPoint, Qt, QTimer
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget
from PyQt5.QtGui import QColor, QCursor, QFont, QMouseEvent, QPainter, QPen
from winMemUtils import getActiveWindowTitle, getWindow, read4Bytes, write4Bytes, pid


color = {
    -1: {"color": QColor(0, 0, 0, 255), "name": ""},
    0: {"color": QColor(255, 0, 0, 255), "name": "红"},
    1: {"color": QColor(255, 255, 255, 255), "name": "白"},
    2: {"color": QColor(0, 255, 0, 255), "name": "绿"},
    3: {"color": QColor(255, 255, 0, 255), "name": "黄"},
    4: {"color": QColor(128, 0, 255, 255), "name": "紫"},
    5: {"color": QColor(255, 128, 0, 255), "name": "橙"},
    6: {"color": QColor(0, 0, 255, 255), "name": "蓝"},
    4294967295: {"color": QColor(0, 0, 0, 255), "name": "无"},
}
special = {
    0: "无",
    1: "火",
    2: "超",
    4: "闪",
    5: "星",
}
saveStates = [None for i in range(12)]
keyPressed = []
logs = ""
logsTime = 0
cursor = None


def saveOrLoad(i):
    global logs, logsTime
    if "shift" in keyPressed:
        saveStates[i] = [[{"color": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x220]), "special": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x228])} for ix in range(8)] for iy in range(8)]
        logs, logsTime = f"已保存至存档 {i}", time.time()
    else:
        if not saveStates[i]:
            logs, logsTime = f"存档 {i} 不存在", time.time()
            return
        for ix in range(8):
            for iy in range(8):
                write4Bytes(0x008E1730, saveStates[i][iy][ix]["color"], [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x220])
                write4Bytes(0x008E1730, saveStates[i][iy][ix]["special"], [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x228])
        logs, logsTime = f"已读取存档 {i}", time.time()


class Window(QWidget):
    def __init__(self, parent=None):
        def createButtonSavestate(i):
            button = QPushButton(f"{i}", self)
            button.setGeometry(15 + 50 * i, self.height() - 110, 50, 50)
            button.clicked.connect(lambda: saveOrLoad(i))
            return button

        def createButtonCursorColor(i):
            button = QPushButton(f"{color[i]['name']}", self)
            button.setGeometry(15 + 50 * i, 975, 50, 50)
            button.setEnabled(False)
            button.clicked.connect(lambda: write4Bytes(0x008E1730, i, [0xBE8, 0xF8 + 4 * cursor[0] + 32 * cursor[1], 0x220]))
            return button

        def createButtonCursorSpecial(i, xpos, name):
            button = QPushButton(name, self)
            button.setGeometry(15 + 50 * xpos, 1025, 50, 50)
            button.setEnabled(False)
            button.clicked.connect(lambda: write4Bytes(0x008E1730, i, [0xBE8, 0xF8 + 4 * cursor[0] + 32 * cursor[1], 0x228]))
            return button

        super().__init__(parent)
        self.setWindowTitle("Bejeweled 3 Helper")
        self.setGeometry(*getWindow())
        self.buttonSavestate = [createButtonSavestate(i) for i in range(10)]
        self.buttonCursorColor = [createButtonCursorColor(i) for i in range(7)]
        self.buttonCursorSpecial = []
        self.buttonCursorSpecial.append(createButtonCursorSpecial(0, 0, special[0]))
        self.buttonCursorSpecial.append(createButtonCursorSpecial(1, 1, special[1]))
        self.buttonCursorSpecial.append(createButtonCursorSpecial(2, 2, special[2]))
        self.buttonCursorSpecial.append(createButtonCursorSpecial(4, 3, special[4]))
        self.buttonCursorSpecial.append(createButtonCursorSpecial(5, 4, special[5]))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateData)
        self.timer.start(10)

    def updateData(self):
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        global cursor
        if event.button() == Qt.LeftButton:
            x, y = event.pos().x(), event.pos().y()
            if 10 <= x < 522 and 400 <= y < 912:
                ix, iy = int((x - 10) / 64), int((y - 400) / 64)
                if cursor != (ix, iy):
                    cursor = (ix, iy)
                    for button in self.buttonCursorColor + self.buttonCursorSpecial:
                        button.setEnabled(True)
                    return
            cursor = None
            for button in self.buttonCursorColor + self.buttonCursorSpecial:
                button.setEnabled(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景
        painter.setBrush(QColor(0, 0, 64, 64))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

        # 字体
        font = QFont("等线", 20, QFont.Bold)
        painter.setFont(font)

        # 获取信息
        startReadTime = time.time()
        systemTime = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss.zzz")
        statistics = {
            "gem": [read4Bytes(0x008E170C, [0xB80, 0xD0 + i * 4]) for i in range(11)],
        }
        mode = ""
        field = [
            [
                {
                    "address": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * ix + 32 * iy]),
                    "color": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x220]),
                    "special": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x228]),
                }
                for ix in range(8)
            ]
            for iy in range(8)
        ]
        score = read4Bytes(0x008E1730, [0xBE8, 0xD24])
        progressAnim = read4Bytes(0x008E1730, [0xBE8, 0xD68], "float")
        progress = read4Bytes(0x008E1730, [0xBE8, 0xE00])
        level = read4Bytes(0x008E1730, [0xBE8, 0xE04])
        if mode == "Ice Storm":
            iceCombo = read4Bytes(0x008E1730, [0xBE8, 0x36C8])
            currentTime = read4Bytes(0x008E1730, (0xBE8, 0xE38))
            iceComboTime = read4Bytes(0x008E1730, [0xBE8, 0x36BC])
            iceComboAllowTime = read4Bytes(0x008E1730, [0xBE8, 0x36C4])
        endReadTime = time.time()

        # 绘制
        drawX, drawY = 10, 10
        self.drawText(painter, drawX, drawY, systemTime)
        drawY += 30
        self.drawText(painter, drawX, drawY, f"Process ID: {pid}")
        drawY += 30
        self.drawText(painter, drawX, drawY, f"获取信息耗时: {endReadTime-startReadTime:.3f}")
        drawY += 30
        self.drawText(painter, drawX, drawY, f"总宝石数: {statistics['gem'][0]}")
        drawY += 30
        self.drawText(painter, drawX, drawY, f"等级: {level} 分数: {score}")
        drawY += 30
        self.drawText(painter, drawX, drawY, f"进展: {progressAnim*100:.2f}% ({progress}/{level * 750 + 2500 if level<30 else 25000})")
        drawY = 350
        mousePos = self.mapFromGlobal(QCursor.pos())
        for i, button in enumerate(self.buttonSavestate):
            if button.geometry().contains(mousePos) and saveStates[i]:
                field = saveStates[i]
                self.drawText(painter, drawX, drawY, f"*预览: 存档 {i}")
        drawY += 50
        for iy in range(8):
            for ix in range(8):
                gridX, gridY = drawX + ix * 64, drawY + iy * 64
                gridColor = color[field[iy][ix]["color"]]["color"]
                self.drawRect(painter, gridX, gridY, gridX + 64, gridY + 64, gridColor)
                if field[iy][ix]["special"] > 0:
                    textColor = Qt.black if field[iy][ix]["special"] != 2 else Qt.white
                    self.drawText(painter, gridX + 19, gridY + 19, special[field[iy][ix]["special"]], textColor)
        if cursor:
            cursorAddress = field[cursor[1]][cursor[0]]["address"]
            cursorColor = field[cursor[1]][cursor[0]]["color"]
            cursorSpecial = field[cursor[1]][cursor[0]]["special"]
            cursorPen = QPen(QColor(0, 0, 0, 255), 2) if cursorColor <= 6 else QPen(QColor(255, 255, 255, 255), 2)
            self.drawRect(painter, drawX + 64 * cursor[0] + 8, drawY + 64 * cursor[1] + 8, drawX + 64 * cursor[0] + 56, drawY + 64 * cursor[1] + 56, brush=Qt.NoBrush, border=cursorPen)
            self.drawText(painter, drawX, drawY + 520, f"地址: 0x{hex(cursorAddress)[2:].upper()}")
            self.drawText(painter, drawX, drawY + 550, f"颜色: {color[cursorColor]['name']} 特宝:{special[cursorSpecial]}")

        if mode == "Ice Storm":
            ratio = (iceComboAllowTime + iceComboTime - currentTime) / iceComboAllowTime
            self.drawText(painter, drawX + 255, drawY, f"x{iceCombo}", Qt.blue if ratio > 0 and iceCombo > 0 else Qt.black)
            drawY += 30
            self.drawRect(painter, drawX + 9, drawY - 1, drawX + 511, drawY + 41)
            if iceCombo > 0:
                self.drawRect(painter, drawX + 10, drawY, int(drawX + 10 + 510 * ratio), drawY + 40, Qt.blue, Qt.NoPen)

        drawY = self.height() - 60
        self.drawText(painter, drawX, drawY, "日志:")
        drawY += 25
        self.drawText(painter, drawX, drawY, f"{logs}", QColor(0, 0, 0, min(255, max(0, int(64 * (logsTime + 4 - time.time()))))))

        painter.end()

    def drawText(self, painter: QPainter, X, Y, text, color=Qt.black):
        painter.setPen(color)
        textRect = self.rect()
        textRect.moveTopLeft(QPoint(X, Y))
        painter.drawText(textRect, Qt.AlignLeft, text)

    def drawRect(self, painter: QPainter, X1, Y1, X2, Y2, brush=QColor(255, 255, 255, 255), border=QPen(QColor(0, 0, 0, 255), 1)):
        if X2 < X1 or Y2 < Y1:
            return
        painter.setPen(border)
        painter.setBrush(brush)
        rect = self.rect()
        rect.setWidth(X2 - X1)
        rect.setHeight(Y2 - Y1)
        rect.moveLeft(X1)
        rect.moveTop(Y1)
        painter.drawRect(rect)

    def closeWindow(self):
        self.close()


def onKeyboardPress(key):
    global keyPressed, logs, logsTime
    try:
        if key.vk not in keyPressed:
            keyPressed.append(key.vk)
        if key.vk in range(48, 57):  # 大键盘的数字键 0-9
            title = getActiveWindowTitle()
            if title != "Bejeweled 3" and title != "Bejeweled 3 Helper":
                return
            keyID = key.vk - 48
            saveOrLoad(keyID)
    except AttributeError:
        if key.name not in keyPressed:
            keyPressed.append(key.name)


def onKeyboardRelease(key):
    global keyPressed
    try:
        if key.vk in keyPressed:
            keyPressed.remove(key.vk)
    except AttributeError:
        if key.name in keyPressed:
            keyPressed.remove(key.name)


listenerKeyboard = keyboard.Listener(on_press=onKeyboardPress, on_release=onKeyboardRelease)
listenerKeyboard.start()

app = QApplication(sys.argv)
win = Window()
win.show()
sys.exit(app.exec())
