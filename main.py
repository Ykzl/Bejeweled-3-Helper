import sys
from pynput import keyboard, mouse
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPoint
from PyQt5.QtGui import QPainter, QColor, QFont, QPen
import pygetwindow as gw
import win32gui
import ctypes
import os
import time


def getActiveWindowTitle():
    hwnd = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(hwnd)


def getWindow(title="Bejeweled 3"):
    try:
        window = gw.getWindowsWithTitle(title)[0]
        x, y, width, height = window.left + 8, window.top + 32, window.width - 16, window.height - 40
        return (x + width, y, int(16 / 9 * height - width), height)
    except IndexError:
        print(f"Window with title '{title}' not found.")
        return (0, 0, 533, 1200)


def getPID(pName):
    PIDs = os.popen(f'wmic process where name="{pName}" get processid').readlines()
    for line in PIDs:
        if line.strip().isdigit():
            return int(line.strip())


def read4Bytes(address, offsets=[], dataType="int", buffer=None):
    if not buffer:
        buffer = ctypes.create_string_buffer(4)
    if ctypes.windll.kernel32.ReadProcessMemory(processHandle, address, buffer, 4, ctypes.byref(ctypes.c_ulong(0))):
        if dataType == "float" and not offsets:
            output = ctypes.c_float.from_buffer_copy(buffer.raw).value
        else:
            output = int.from_bytes(buffer.raw, byteorder="little")
    else:
        return -1

    if offsets:
        if output == 0:
            return -1
        return read4Bytes(output + offsets[0], offsets[1:], dataType, buffer)
    else:
        return output


def write4Bytes(address, data, offsets=[], dataType="int"):
    if len(offsets) >= 2:
        address = read4Bytes(address, offsets[:-1])
        if address <= 0:
            return False
    if len(offsets) >= 1:
        address += offsets[-1]

    if dataType == "int":
        buffer = ctypes.create_string_buffer(int(data).to_bytes(4, byteorder="little"))
    elif dataType == "float":
        buffer = ctypes.create_string_buffer(ctypes.c_float(float(data)).raw)

    success = ctypes.windll.kernel32.WriteProcessMemory(processHandle, address, buffer, len(buffer), ctypes.byref(ctypes.c_ulong(0)))

    if not success:
        error_code = ctypes.GetLastError()
        print(f"Failed to write to memory. Error code: {error_code}")
        return False

    return True


pid = getPID("Bejeweled3.exe")
processHandle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)
color = {
    0: QColor(255, 0, 0),
    1: QColor(255, 255, 255),
    2: QColor(0, 255, 0),
    3: QColor(255, 255, 0),
    4: QColor(128, 0, 255),
    5: QColor(255, 128, 0),
    6: QColor(0, 0, 255),
}
saveStates = [None for i in range(12)]
keyPressed = []
logs = ""
logsTime = 0


class Window(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bejeweled 3 Helper")
        self.setGeometry(*getWindow())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateData)
        self.timer.start(10)

    def updateData(self):
        self.update()

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
        field = [[{"color": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x220]), "special": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x228])} for ix in range(8)] for iy in range(8)]
        if mode == "Ice Storm":
            iceCombo = read4Bytes(0x008E1730, [0xBE8, 0x36C8])
            currentTime = read4Bytes(0x008E1730, (0xBE8, 0xE38))
            iceComboTime = read4Bytes(0x008E1730, [0xBE8, 0x36BC])
            iceComboAllowTime = read4Bytes(0x008E1730, [0xBE8, 0x36C4])
        endReadTime = time.time()

        # 绘制
        drawX, drawY = 10, 10
        sideLength = 64
        self.drawText(painter, drawX, drawY, systemTime)
        drawY += 25
        self.drawText(painter, drawX, drawY, f"Process ID: {pid}")
        drawY += 25
        self.drawText(painter, drawX, drawY, f"获取信息耗时: {endReadTime-startReadTime:.3f}")
        drawY += 25
        self.drawText(painter, drawX, drawY, f"总宝石数: {statistics['gem'][0]}")
        drawY += 40
        for iy in range(8):
            for ix in range(8):
                gridX, gridY = drawX + ix * sideLength, drawY + iy * sideLength
                gridColor = color.get(field[iy][ix]["color"], QColor(0, 0, 0))
                self.drawRect(painter, gridX, gridY, gridX + sideLength, gridY + sideLength, gridColor)
                match (field[iy][ix]["special"]):
                    case 1:
                        self.drawText(painter, gridX + 18, gridY + 18, "火")
                    case 2:
                        self.drawText(painter, gridX + 18, gridY + 18, "超", Qt.white)
                    case 4:
                        self.drawText(painter, gridX + 18, gridY + 18, "闪")
                    case 5:
                        self.drawText(painter, gridX + 18, gridY + 18, "星")
                    case _:
                        pass
        drawY += 300

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

    def drawText(self, painter, X, Y, text, color=Qt.black):
        painter.setPen(color)
        textRect = self.rect()
        textRect.moveTopLeft(QPoint(X, Y))
        painter.drawText(textRect, Qt.AlignLeft, text)

    def drawRect(self, painter, X1, Y1, X2, Y2, brush=QColor(255, 255, 255), border=QPen(QColor(0, 0, 0), 1)):
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
            if "shift" in keyPressed:
                saveStates[keyID] = [[{"color": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x220]), "special": read4Bytes(0x008E1730, [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x228])} for ix in range(8)] for iy in range(8)]
                logs, logsTime = f"已保存至存档 {keyID}", time.time()
            else:
                if not saveStates[keyID]:
                    logs, logsTime = f"存档 {keyID} 不存在", time.time()
                    return
                for ix in range(8):
                    for iy in range(8):
                        write4Bytes(0x008E1730, saveStates[keyID][iy][ix]["color"], [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x220])
                        write4Bytes(0x008E1730, saveStates[keyID][iy][ix]["special"], [0xBE8, 0xF8 + 4 * ix + 32 * iy, 0x228])
                logs, logsTime = f"已读取存档 {keyID}", time.time()
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
