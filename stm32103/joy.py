import tkinter as tk
import csv
import time
from pynput import keyboard
import serial
import struct

# 初始化摇杆值
left_stick = {'x': 0, 'y': 0}
right_stick = {'x': 0, 'y': 0}
xs_dis = 0.1  # 每次移动的像素

# 控制命令定义
CMD_FLIGHT_LAND = 0x03  # 起飞/降落命令
CMD_EMER_STOP = 0x04    # 紧急停机命令
CMD_FLIGHT_MODE = 0x01  # 飞行模式命令

# 创建csv文件并写入表头
csv_file = open('joystick_values.csv', mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Time (s)', 'Left Stick X', 'Left Stick Y', 'Right Stick X', 'Right Stick Y'])
csv_file.flush()

# 创建串口连接
ser = serial.Serial('COM10', 9600, timeout=1)  # 根据实际串口号设置

# 记录摇杆值到csv文件
def record_to_csv():
    current_time = time.time() - start_time
    csv_writer.writerow([current_time, left_stick['x'], left_stick['y'], right_stick['x'], right_stick['y']])
    csv_file.flush()  # 每次写入后刷新文件
    window.after(100, record_to_csv)  # 每100ms记录一次

# 发送飞行命令数据包
def send_packet_CMD(command):
    data = [0xAA, 0xAF, 0x50, 0x02, 0x00, command]
    checksum = sum(data) % 256
    data.append(checksum)
    ser.write(bytes(data))
    print(f"飞行命令已发送: {bytes(data).hex()}")

# 更新摇杆的控制命令并发送数据包
def update_joystick_positions():
    # 限制摇杆的最大偏移范围
    left_stick['x'] = max(-2, min(left_stick['x'], 2))
    left_stick['y'] = max(-2, min(left_stick['y'], 2))
    right_stick['x'] = max(-2, min(right_stick['x'], 2))
    right_stick['y'] = max(-2, min(right_stick['y'], 2))

    # 计算无人机控制参数
    roll = left_stick['x'] * 10  # 横滚
    pitch = left_stick['y'] * 10  # 俯仰
    yaw = right_stick['x'] * 10  # 偏航
    thrust = right_stick['y'] * 10  # 油门

    # 控制模式和飞行模式
    remoterData = {
        'roll': roll,
        'pitch': pitch,
        'yaw': yaw,
        'thrust': thrust,
        'ctrlMode': 0,  # 控制模式，0: 手动模式
        'flightMode': 0  # 飞行模式
    }

    # 打包控制数据并发送
    send_packet_DATA(remoterData)

# 构建和发送控制数据包
def send_packet_DATA(remoterData):
    data = [0xAA, 0xAF, 0x50, 0x1D, 0x01]  # 包头
    data += list(struct.pack('<f', remoterData['roll']))
    data += list(struct.pack('<f', remoterData['pitch']))
    data += list(struct.pack('<f', remoterData['yaw']))
    data += list(struct.pack('<f', remoterData['thrust']))
    data.append(remoterData['ctrlMode'])
    data.append(remoterData['flightMode'])
    checksum = sum(data) % 256
    data.append(checksum)
    ser.write(bytes(data))
    print(f"控制数据已发送: {bytes(data).hex()}")

# 键盘事件处理
def on_press(key):
    global left_stick, right_stick
    try:
        if key.char == 'w':  # 上
            left_stick['y'] += xs_dis
        elif key.char == 's':  # 下
            left_stick['y'] -= xs_dis
        elif key.char == 'a':  # 左
            left_stick['x'] -= xs_dis
        elif key.char == 'd':  # 右
            left_stick['x'] += xs_dis
        elif key.char == 'i':  # 上
            right_stick['y'] += xs_dis
        elif key.char == 'k':  # 下
            right_stick['y'] -= xs_dis
        elif key.char == 'j':  # 左
            right_stick['x'] -= xs_dis
        elif key.char == 'l':  # 右
            right_stick['x'] += xs_dis
        elif key.char == 'b':  # 重置摇杆
            left_stick['x'] = 0
            left_stick['y'] = 0
            right_stick['x'] = 0
            right_stick['y'] = 0
        elif key.char == 't':  # 一键起飞
            send_packet_CMD(CMD_FLIGHT_LAND)
        elif key.char == 'e':  # 一键紧急停机
            send_packet_CMD(CMD_EMER_STOP)
    except AttributeError:
        pass

    update_joystick_positions()

def on_release(key):
    if key == keyboard.Key.esc:
        return False  # 退出监听

# 创建主窗口
window = tk.Tk()
window.title("虚拟摇杆控制无人机")
window.geometry("600x350")

# 创建左摇杆区域
left_stick_frame = tk.Frame(window, width=300, height=300, bg='lightgrey')
left_stick_frame.grid(row=0, column=0)
left_stick_canvas = tk.Canvas(left_stick_frame, width=300, height=300, bg='white')
left_stick_canvas.create_rectangle(50, 50, 250, 250, outline="black")  # 添加边框
left_stick_canvas.pack()

# 创建右摇杆区域
right_stick_frame = tk.Frame(window, width=300, height=300, bg='lightgrey')
right_stick_frame.grid(row=0, column=1)
right_stick_canvas = tk.Canvas(right_stick_frame, width=300, height=300, bg='white')
right_stick_canvas.create_rectangle(50, 50, 250, 250, outline="black")  # 添加边框
right_stick_canvas.pack()

# 更新摇杆位置的初始圆形
left_stick_canvas.create_oval(150 + left_stick['x'] * 50 - 10, 150 - left_stick['y'] * 50 - 10,
                              150 + left_stick['x'] * 50 + 10, 150 - left_stick['y'] * 50 + 10,
                              fill='red', tags='stick')
right_stick_canvas.create_oval(150 + right_stick['x'] * 50 - 10, 150 - right_stick['y'] * 50 - 10,
                               150 + right_stick['x'] * 50 + 10, 150 - right_stick['y'] * 50 + 10,
                               fill='blue', tags='stick')

# 显示摇杆值
left_stick_label = tk.Label(window, text=f'Left Stick: X={left_stick["x"]:.2f}, Y={left_stick["y"]:.2f}')
left_stick_label.grid(row=1, column=0)

right_stick_label = tk.Label(window, text=f'Right Stick: X={right_stick["x"]:.2f}, Y={right_stick["y"]:.2f}')
right_stick_label.grid(row=1, column=1)

# 启动键盘监听
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# 定时记录摇杆值
start_time = time.time()
record_to_csv()

# 启动主窗口
window.mainloop()

# 关闭文件
csv_file.close()
ser.close()
