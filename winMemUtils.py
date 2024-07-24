import ctypes
import os
import pygetwindow as gw
import win32gui


def getActiveWindowTitle():
    hwnd = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(hwnd)


def getWindow(title="Bejeweled 3"):
    try:
        for window in gw.getWindowsWithTitle(title):
            if window.title != title:
                continue
            x, y, width, height = window.left + 8, window.top + 32, window.width - 16, window.height - 40
            return (x + width, y, int(16 / 9 * height - width), height)
        print(f"Window with title '{title}' not found.")
        return (0, 0, 533, 1200)
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
