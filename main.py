import os
import sys
import time
import pickle
from pynput import keyboard
from PyQt5.QtCore import QDateTime, QPoint, Qt, QTimer
from PyQt5.QtWidgets import QApplication, QComboBox, QLabel, QPushButton, QWidget
from PyQt5.QtGui import QColor, QCursor, QFont, QMouseEvent, QPainter, QPen, QPixmap
from winMemUtils import getActiveWindowTitle, getWindow, read4Bytes, write4Bytes, pid


color = {
    -1: {"color": QColor(0, 0, 0, 0), "name": ""},
    0: {"color": QColor(255, 0, 0, 255), "name": "红"},
    1: {"color": QColor(255, 255, 255, 255), "name": "白"},
    2: {"color": QColor(0, 255, 0, 255), "name": "绿"},
    3: {"color": QColor(255, 255, 0, 255), "name": "黄"},
    4: {"color": QColor(255, 0, 255, 255), "name": "紫"},
    5: {"color": QColor(255, 128, 0, 255), "name": "橙"},
    6: {"color": QColor(0, 128, 255, 255), "name": "蓝"},
    4294967295: {"color": QColor(0, 0, 0, 255), "name": "无"},
}
special = {
    -1: {"name": "", "shortName": ""},
    0: {"name": "普通", "shortName": ""},
    1: {"name": "火焰", "shortName": "火"},
    2: {"name": "超能", "shortName": "超"},
    4: {"name": "闪电", "shortName": "闪"},
    5: {"name": "超新星", "shortName": "星"},
    # 16: {"name": "倍率", "shortName": ""},
    # 32: {"name": "步数炸弹芯", "shortName": ""},
    # 64: {"name": "时间炸弹芯", "shortName": ""},
    # 128: {"name": "蝴蝶", "shortName": ""},
    # 256: {"name": "毁灭", "shortName": ""},
    # 512: {"name": "炸弹壳", "shortName": ""},
    # 4096: {"name": "Scrambler", "shortName": ""},
}
if os.path.exists("saveStates.dump"):
    with open("saveStates.dump", "rb") as f:
        saveStates = pickle.load(f)
else:
    saveStates = [None for i in range(10)]
keyPressed = []
logs = ""
logsTime = 0
cursor = None


def readGem(x, y):
    gem = {
        "address": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * x + 32 * y]),
        "color": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * x + 32 * y, 0x220]),
        "special": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * x + 32 * y, 0x228]),
    }
    if gem["special"] == 2:
        gem["preColor"] = read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * x + 32 * y, 0x21C])
    return gem


def saveOrLoad(i):
    global logs, logsTime
    if "shift" in keyPressed and "ctrl_l" in keyPressed:
        saveStates[i] = [[readGem(ix, iy) for ix in range(8)] for iy in range(8)]
        logs, logsTime = f"已保存至存档 {i}", time.time()
    elif "ctrl_l" in keyPressed:
        if not saveStates[i]:
            logs, logsTime = f"存档 {i} 不存在", time.time()
            return
        for ix in range(8):
            for iy in range(8):
                write4Bytes(0x008E1730, saveStates[i][iy][ix]["color"], [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x220])
                write4Bytes(0x008E1730, saveStates[i][iy][ix]["special"], [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x228])
                if "preColor" in saveStates[i][iy][ix]:
                    write4Bytes(0x008E1730, saveStates[i][iy][ix]["preColor"], [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x21C])
        logs, logsTime = f"已读取存档 {i}", time.time()


class Window(QWidget):
    def __init__(self, parent=None):
        def createButtonSavestate(i):
            button = QPushButton(f"{i}", self)
            button.setGeometry(15 + 50 * i, self.height() - 110, 50, 50)
            button.clicked.connect(lambda: saveOrLoad(i))
            return button

        def comboSpecialChanged():
            if not cursor:
                return
            write4Bytes(0x008E1730, int(self.comboSpecial.currentText().split(":")[0]), [0xBE8, 0xF8 + 4 * cursor[0] + 32 * cursor[1], 0x228])

        super().__init__(parent)
        self.setWindowTitle("Bejeweled 3 Helper")
        self.setGeometry(*getWindow())

        originBG = QPixmap("bg.jpg")
        self.bg = originBG.copy(originBG.width() - int(4 * self.height() / 9), 0, int(4 * self.height() / 9), originBG.height())
        self.buttonSavestate = [createButtonSavestate(i) for i in range(10)]
        self.comboColor = QComboBox(self)
        self.comboColor.setGeometry(10, 950, 120, 20)
        self.comboColor.addItems([f"{k}: {v['name']}" for k, v in color.items() if v["name"]])
        self.comboColor.currentIndexChanged.connect(lambda: write4Bytes(0x008E1730, int(self.comboColor.currentText().split(":")[0]), [0xBE8, 0xF8 + 4 * cursor[0] + 32 * cursor[1], 0x220]))
        self.comboColor.setEnabled(False)
        self.comboSpecial = QComboBox(self)
        self.comboSpecial.setGeometry(150, 950, 120, 20)
        self.comboSpecial.addItems([f"{k}: {v['name']}" for k, v in special.items() if v["name"]])
        self.comboSpecial.currentIndexChanged.connect(comboSpecialChanged)
        self.comboSpecial.setEnabled(False)

        # self.mode=""

        self.updateData()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateData)
        self.timer.start(10)

    def updateData(self):

        startReadTime = time.time()
        self.statistics = {
            "gem": [read4Bytes(0x008E170C, [0xB80, 0xD0 + i * 4]) for i in range(11)],
        }
        self.field = [[readGem(ix, iy) for ix in range(8)] for iy in range(8)]
        self.game = {
            "score": read4Bytes(0x008E1730, [0xBE8, 0xD24]),
            "progressAnim": read4Bytes(0x008E1730, [0xBE8, 0xD68], "float"),
            "progress": read4Bytes(0x008E1730, [0xBE8, 0xE00]),
            "level": read4Bytes(0x008E1730, [0xBE8, 0xE04]),
        }
        # if self.mode == "Ice Storm":
        #    iceCombo = read4Bytes(0x008E1730, [0xBE8, 0x36C8])
        #    currentTime = read4Bytes(0x008E1730, (0xBE8, 0xE38))
        #    iceComboTime = read4Bytes(0x008E1730, [0xBE8, 0x36BC])
        #    iceComboAllowTime = read4Bytes(0x008E1730, [0xBE8, 0x36C4])
        self.readTime = time.time() - startReadTime

        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        global cursor
        if event.button() == Qt.LeftButton:
            x, y = event.pos().x(), event.pos().y()
            if 10 <= x < 522 and 400 <= y < 912:
                ix, iy = int((x - 10) / 64), int((y - 400) / 64)
                if cursor != (ix, iy):
                    cursor = (ix, iy)
                    cursorColor = self.field[cursor[1]][cursor[0]]["color"]
                    cursorSpecial = self.field[cursor[1]][cursor[0]]["special"]
                    self.comboColor.setEnabled(True)
                    self.comboColor.setCurrentIndex(cursorColor if 0 <= cursorColor <= 6 else 7)
                    self.comboSpecial.setEnabled(True)
                    self.comboSpecial.setEditable(True)
                    self.comboSpecial.setEditText(f"{cursorSpecial}: {special[cursorSpecial]['name']}" if cursorSpecial in special else f"{cursorSpecial}")
                    return
            cursor = None
            self.comboColor.setEnabled(False)
            self.comboSpecial.setEnabled(False)
            self.comboSpecial.setEditable(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        def drawText(X, Y, text, color=Qt.black, font=QFont("等线", 20, QFont.Bold)):
            painter.setFont(font)
            painter.setPen(color)
            textRect = self.rect()
            textRect.moveTopLeft(QPoint(X, Y))
            painter.drawText(textRect, Qt.AlignLeft, text)

        def drawRect(X1, Y1, X2, Y2, brush=QColor(255, 255, 255, 255), border=QPen(QColor(0, 0, 0, 255), 1)):
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

        # 背景
        painter.drawPixmap(self.rect(), self.bg)

        # 绘制
        drawX, drawY = 10, 10
        drawText(
            drawX,
            drawY,
            f"""{QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss.zzz")}
Process ID: {pid}
获取信息耗时: {self.readTime:.3f}
总宝石数: {self.statistics['gem'][0]}
等级: {self.game["level"]+1} 分数: {self.game["score"]}
进展: {self.game["progressAnim"]*100:.2f}% ({self.game["progress"]}/{self.game["level"] * 750 + 2500 if self.game["level"]<30 else 25000})
""",
        )

        field = self.field
        drawX, drawY = 10, 350
        mousePos = self.mapFromGlobal(QCursor.pos())
        for i, button in enumerate(self.buttonSavestate):
            if button.geometry().contains(mousePos) and saveStates[i]:
                field = saveStates[i]
                drawText(drawX, drawY, f"*预览: 存档 {i}")

        drawX, drawY = 10, 400
        for iy in range(8):
            for ix in range(8):
                gridX, gridY = drawX + ix * 64, drawY + iy * 64
                gridColor = field[iy][ix]["color"]
                gridSpecial = field[iy][ix]["special"]
                drawRect(gridX, gridY, gridX + 64, gridY + 64, color[gridColor]["color"])
                if "preColor" in field[iy][ix]:
                    textColor = color[field[iy][ix]["preColor"]]["color"] if 0 <= field[iy][ix]["preColor"] <= 6 else Qt.gray
                else:
                    textColor = Qt.black if 0 <= gridColor <= 6 else Qt.white
                #drawText(gridX + 2, gridY + 2, hex(field[iy][ix]["address"])[2:].upper(), textColor, QFont("等线", 10))
                drawText(gridX + 19, gridY + 19, special[gridSpecial]["shortName"] if gridSpecial in special else "？", textColor)
        if cursor:
            cursorColor = field[cursor[1]][cursor[0]]["color"]
            cursorSpecial = field[cursor[1]][cursor[0]]["special"]
            cursorPen = QPen(QColor(0, 0, 0, 255), 2) if cursorColor <= 6 else QPen(QColor(255, 255, 255, 255), 2)
            drawRect(drawX + 64 * cursor[0] + 8, drawY + 64 * cursor[1] + 8, drawX + 64 * cursor[0] + 56, drawY + 64 * cursor[1] + 56, brush=Qt.NoBrush, border=cursorPen)
            drawText(drawX, drawY + 520, f"颜色: {color[cursorColor]['name']} 特宝:{special[cursorSpecial]['name'] if cursorSpecial in special else cursorSpecial}")

        # if self.mode == "Ice Storm":
        #    ratio = (iceComboAllowTime + iceComboTime - currentTime) / iceComboAllowTime
        #    drawText(drawX + 255, drawY, f"x{iceCombo}", Qt.blue if ratio > 0 and iceCombo > 0 else Qt.black)
        #    drawY += 30
        #    drawRect(drawX + 9, drawY - 1, drawX + 511, drawY + 41)
        #    if iceCombo > 0:
        #        drawRect(drawX + 10, drawY, int(drawX + 10 + 510 * ratio), drawY + 40, Qt.blue, Qt.NoPen)

        drawX, drawY = 10, self.height() - 60
        drawText(drawX, drawY, "日志:")
        drawText(drawX, drawY + 25, f"{logs}", QColor(0, 0, 0, min(255, max(0, int(64 * (logsTime + 4 - time.time()))))))

        painter.end()

    def closeEvent(self, event):
        with open("saveStates.dump", "wb") as f:
            pickle.dump(saveStates, f)


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
