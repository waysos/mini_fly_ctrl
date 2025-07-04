# 双摇杆控制器
import tkinter as tk
import csv
from pynput import keyboard
import time
import serial
import struct

# 初始化全局变量存储摇杆值
left_stick = {'x': 0, 'y': 0}
right_stick = {'x': 0, 'y': 0}
xs_dis = 0.1  # 每次移动的像素

# 创建csv文件并写入表头
csv_file = open('joystick_values.csv', mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Time (s)', 'Left Stick X', 'Left Stick Y', 'Right Stick X', 'Right Stick Y'])
csv_file.flush()  # 刷新缓冲区

# 创建串口连接
ser = serial.Serial('COM10', 9600, timeout=1)  # 根据实际串口号设置

# 定义消息结构
DOWN_BYTE1 = 0xAA
DOWN_BYTE2 = 0xAF

# 下行命令
DOWN_REMOTOR = 0x50  # 控制电机

# 控制命令类型
REMOTOR_CMD = 0x00  # 控制命令标识符
# 控制数据标识符
REMOTOR_DATA = 0x01  # 数据标识符

# 控制命令
CMD_GET_MSG = 0x01 # 获取四轴信息（自检）
CMD_GET_CANFLY = 0x02  # 获取四轴是否能飞
CMD_FLIGHT_LAND = 0x03 # 起飞、降落
CMD_EMER_STOP = 0x04 # 紧急停机
CMD_FLIP = 0x05 # 4D翻滚
CMD_POWER_MODULE = 0x06 # 打开关闭扩展模块电源
CMD_LEDRING_EFFECT = 0x07 # 设置RGB灯环效果
CMD_POWER_VL53LXX = 0x08 # 打开关闭激光

# 控制数据内容
remoterData = {
    'roll': 0.0,         # 横滚角度（Roll）
    'pitch': 0.0,        # 俯仰角度（Pitch）
    'yaw': 0.0,          # 偏航角度（Yaw）
    'thrust': 0.0,      # 推力（油门）
    'trimPitch': 0.0,    # pitch微调
    'trimRoll': 0.0,     # roll微调
    'ctrlMode': 1,       # 控制模式（0为手动模式，1为定高模式，3为定点模式）
    'flightMode': 0,     # 飞行模式（0为X-mode 1为无头模式）
    'RCLock': 0          # 遥控器锁定状态（0表示解锁）
}

# 校验和计算函数
def calculate_checksum(data):
    # 步骤 1: 计算逐字节的和
    total_sum = sum(data)
    
    # 步骤 2: 对总和进行模 256 运算
    checksum = total_sum % 256
    
    # 步骤 3: 返回校验和
    return checksum

# 将数据转换为字节
def float_to_bytes(value):
    # 使用 IEEE 754 标准的 float -> bytes 转换
    return struct.pack('<f', value)  # 小端字节序

# 构建CMD数据包 输入为八个控制命令，默认为起飞降落指令
def create_packet_CMD(CMD_MODE = CMD_FLIGHT_LAND): 
    # 数据部分: [命令ID, 数据长度, 数据...]
    data = [
        DOWN_BYTE1,  # 帧头1
        DOWN_BYTE2,  # 帧头2
        DOWN_REMOTOR,  # 控制命令ID
        0x02,  # 数据长度: len(data) + 1（控制命令标识符）
        REMOTOR_CMD,  # 数据[0]: 控制命令标识符
        CMD_MODE  # 数据[1]: 控制命令，起飞/降落
    ]
    
    # 计算校验和
    checksum = calculate_checksum(data)
    
    # 添加校验和到数据包末尾
    data.append(checksum)
    
    # 转换为字节格式发送
    return bytes(data)

# 控制命令发送函数，第一参数为端口，第二个为控制命令
def send_packet_CMD(CMD_MODE = CMD_FLIGHT_LAND):
    # 获取构建的控制命令数据包
    packet = create_packet_CMD(CMD_MODE)
    
    # 发送数据包
    ser.write(packet)
    print(f"数据包已发送: {packet.hex()}")
    if CMD_MODE == CMD_FLIGHT_LAND:
        print("飞机已起飞/降落")
    elif CMD_MODE == CMD_EMER_STOP:
        print("飞机已紧急停机")
    

# 构建DATA数据包
def create_packet_DATA():
    # 创建数据部分
    data = [
        DOWN_BYTE1,  # 帧头1
        DOWN_BYTE2,  # 帧头2
        DOWN_REMOTOR,  # 控制命令ID
        0x1D,  # 数据长度 29-1 (结构体 remoterData_t 的长度)
        REMOTOR_DATA,  # 控制数据标识符
    ]
    
    # 添加 remoterData_t 的数据（浮点数按小端字节序转换）
    data += list(float_to_bytes(remoterData['roll']))  # roll
    data += list(float_to_bytes(remoterData['pitch']))  # pitch
    data += list(float_to_bytes(remoterData['yaw']))  # yaw
    data += list(float_to_bytes(remoterData['thrust']))  # thrust
    data += list(float_to_bytes(remoterData['trimPitch']))  # trimPitch
    data += list(float_to_bytes(remoterData['trimRoll']))  # trimRoll
    
    # 添加控制模式（ctrlMode）
    data.append(remoterData['ctrlMode'])
    
    # 添加飞行模式（flightMode）
    data.append(remoterData['flightMode'])
    
    # 添加遥控器锁定状态（RCLock）
    data.append(remoterData['RCLock'])
    
    # 添加 0x00 字节进行字节对齐
    data.append(0x00)
    
    # 校验和计算前，确保所有数据已包括
    # print(f"构建的数据：{data}")  # 打印出所有数据
    
    # 计算校验和
    checksum = calculate_checksum(data)
    
    # 添加校验和到数据包末尾
    data.append(checksum)
    
    # 转换为字节格式
    return bytes(data)

# 发送数据包到设备
def send_packet_DATA(serial_port):
    # 获取构建的控制命令数据包
    packet = create_packet_DATA()
    
    # 发送数据包
    serial_port.write(packet)
    print(f"数据包已发送: {packet.hex()}")

# 接收并打印从串口接收到的数据
def receive_packet(serial_port):
    # 读取串口数据
    if serial_port.in_waiting > 0:  # 检查是否有数据
        received_data = serial_port.read(serial_port.in_waiting)  # 读取所有数据
        print(f"接收到的字节数据: {received_data.hex()}")
        return received_data
    return None

# DATA发送函数
# 修改后的定时发送数据包函数
def send_packet_data_periodically():
    # 发送数据包
    send_packet_DATA(ser)
    
    # 接收数据并打印（可选）
    receive_packet(ser)
    
    # 设定0.001秒后再次调用此函数，持续发送数据包
    window.after(1, send_packet_data_periodically)  # 每1毫秒再次调用自己

# 记录摇杆值到csv文件
def record_to_csv():
    current_time = time.time() - start_time
    csv_writer.writerow([current_time, left_stick['x']/2, left_stick['y']/2, right_stick['x']/2, right_stick['y']/2])
    csv_file.flush()  # 每次写入后刷新文件
    window.after(20, record_to_csv)  # 每100ms记录一次

def on_press(key):
    global left_stick, right_stick  # 声明为全局变量
    try:
        if key.char == 'w':
            left_stick['y'] += xs_dis
        elif key.char == 's':
            left_stick['y'] -= xs_dis
        elif key.char == 'a':
            left_stick['x'] -= xs_dis
        elif key.char == 'd':
            left_stick['x'] += xs_dis
        elif key.char == 'i':
            right_stick['y'] += xs_dis
        elif key.char == 'k':
            right_stick['y'] -= xs_dis
        elif key.char == 'j':
            right_stick['x'] -= xs_dis
        elif key.char == 'l':
            right_stick['x'] += xs_dis
        elif key.char == 'b':  # 按下B键时重置摇杆位置
            left_stick['x'] = 0
            left_stick['y'] = 0
            right_stick['x'] = 0
            right_stick['y'] = 0
        elif key.char == 't':  # 一键起飞
            send_packet_CMD(CMD_FLIGHT_LAND)
        elif key.char == 'e':  # 一键紧急停机
            send_packet_CMD(CMD_EMER_STOP)
        # elif key.char == 'o': 
        #     send_packet_data_periodically()
    except AttributeError:
        pass
    update_joystick_positions()

def on_release(key):
    if key == keyboard.Key.esc:
        return False  # 退出监听

# 数值映射函数，从-2到2映射到0到100
def map_value(value, min_in=-2, max_in=2, min_out=0, max_out=100):
    return (value - min_in) / (max_in - min_in) * (max_out - min_out) + min_out

# 更新摇杆的位置和数值显示
def update_joystick_positions():
    # 清除之前的圆形
    left_stick_canvas.delete('stick')
    right_stick_canvas.delete('stick')

    # 限制左摇杆位置
    left_stick['x'] = max(-2, min(left_stick['x'], 2))
    left_stick['y'] = max(-2, min(left_stick['y'], 2))

    # 限制右摇杆位置
    right_stick['x'] = max(-2, min(right_stick['x'], 2))
    right_stick['y'] = max(-2, min(right_stick['y'], 2))

    # 绘制新的圆形位置
    left_stick_canvas.create_oval(150 + left_stick['x'] * 50 - 10, 150 - left_stick['y'] * 50 - 10,
                                  150 + left_stick['x'] * 50 + 10, 150 - left_stick['y'] * 50 + 10,
                                  fill='red', tags='stick')

    right_stick_canvas.create_oval(150 + right_stick['x'] * 50 - 10, 150 - right_stick['y'] * 50 - 10,
                                   150 + right_stick['x'] * 50 + 10, 150 - right_stick['y'] * 50 + 10,
                                   fill='blue', tags='stick')

    # left_stick_label.config(text=f'Left Stick: X={left_stick["x"]/2:.2f}, Y={left_stick["y"]/2:.2f}')
    left_stick_label.config(text=f'Left Stick: yaw={remoterData["yaw"]:.2f}, thrust={remoterData["thrust"]:.2f}')
    # right_stick_label.config(text=f'Right Stick: X={right_stick["x"]/2:.2f}, Y={right_stick["y"]/2:.2f}')
    right_stick_label.config(text=f'Right Stick: roll={remoterData["roll"]:.2f}, pitch={remoterData["pitch"]:.2f}')
    
    # 将摇杆位置映射到油门、偏航、俯仰、横滚
    remoterData['thrust'] = map_value(left_stick['y'], -2, 2, 0, 100)# 油门映射
    remoterData['yaw'] = map_value(left_stick['x'], -2, 2, -200, 200)# 偏航映射
    remoterData['pitch'] = map_value(right_stick['y'], -2, 2, -50, 50)# 俯仰映射
    remoterData['roll'] = map_value(right_stick['x'], -2, 2, -50, 50)# 横滚映射
    
# button回调函数
def toggle_ctrl_mode():
    # 控制模式在 0, 1, 3 之间切换
    if remoterData['ctrlMode'] == 0:
        remoterData['ctrlMode'] = 1  # 切换到定高模式
    elif remoterData['ctrlMode'] == 1:
        remoterData['ctrlMode'] = 3  # 切换到定点模式
    elif remoterData['ctrlMode'] == 3:
        remoterData['ctrlMode'] = 0  # 切换到手动模式
    
    # 打印当前模式
    print(f"当前控制模式: {remoterData['ctrlMode']}")
    # 更新控制模式标签
    if remoterData['ctrlMode'] == 0:
        ctrl_mode_label.config(text=f'Control Mode:手动模式')
    elif remoterData['ctrlMode'] == 1:
        ctrl_mode_label.config(text=f'Control Mode:定高模式')
    elif remoterData['ctrlMode'] == 3:
        ctrl_mode_label.config(text=f'Control Mode:定点模式')
    
    # 发送更新后的控制命令包
    # send_packet_DATA(ser)

def toggle_lock():
    # 解锁加锁函数
    if remoterData['RCLock'] == 0:
        remoterData['RCLock'] = 1  # 加锁
    elif remoterData['RCLock'] == 1:
        remoterData['RCLock'] = 0  # 解锁
        
    # 打印当前模式
    if remoterData['RCLock'] == 0:
        lock_mode_label.config(text=f'Lock Mode:已解锁')
    elif remoterData['RCLock'] == 1:
        lock_mode_label.config(text=f'Lock Mode:已加锁')
    

# 鼠标拖动事件处理
def move_left_stick(event):
    left_stick['x'] = (event.x - 150) / 50
    left_stick['y'] = (150 - event.y) / 50
    update_joystick_positions()

def move_right_stick(event):
    right_stick['x'] = (event.x - 150) / 50
    right_stick['y'] = (150 - event.y) / 50
    update_joystick_positions()

# 鼠标释放事件处理，重置右摇杆位置
def reset_right_stick(event):
    right_stick['x'] = 0
    right_stick['y'] = 0
    update_joystick_positions()

def get_joystick_values():
    return left_stick['x']/2, left_stick['y']/2, right_stick['x']/2, right_stick['y']/2



# 创建主窗口
window = tk.Tk()
window.title("双摇杆控制器")
window.geometry("600x380")

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

left_stick_canvas.create_oval(150 + left_stick['x'] * 50 - 10, 150 - left_stick['y'] * 50 - 10,
                              150 + left_stick['x'] * 50 + 10, 150 - left_stick['y'] * 50 + 10,
                              fill='red', tags='stick')
right_stick_canvas.create_oval(150 + right_stick['x'] * 50 - 10, 150 - right_stick['y'] * 50 - 10,
                              150 + right_stick['x'] * 50 + 10, 150 - right_stick['y'] * 50 + 10,
                              fill='blue', tags='stick')

# 创建摇杆数值显示标签
left_stick_label = tk.Label(window, text=f'Left Stick: yaw={remoterData["yaw"]:.2f}, thrust={remoterData["thrust"]:.2f}')
# left_stick_label.config(text=f'Left Stick: yaw={remoterData['yaw']:.2f}, thrust={remoterData['thrust']:.2f}')
left_stick_label.grid(row=1, column=0)

right_stick_label = tk.Label(window, text=f'Right Stick: roll={remoterData["roll"]:.2f}, pitch={remoterData["pitch"]:.2f}')
# right_stick_label.config(text=f'Right Stick: roll={remoterData['roll']:.2f}, pitch={remoterData['pitch']:.2f}')
right_stick_label.grid(row=1, column=1)

# 创建控制模式按钮
ctrl_mode_button = tk.Button(window, text="切换控制模式", command=toggle_ctrl_mode)
ctrl_mode_button.grid(row=2, column=0)

# 创建控制模式标签显示当前模式, columnspan=2
if remoterData['ctrlMode'] == 0:
    ctrl_mode_label = tk.Label(window, text=f'Control Mode:手动模式')
elif remoterData['ctrlMode'] == 1:
    ctrl_mode_label = tk.Label(window, text=f'Control Mode:定高模式')
elif remoterData['ctrlMode'] == 3:
    ctrl_mode_label = tk.Label(window, text=f'Control Mode:定点模式')
ctrl_mode_label.grid(row=3, column=0)

# 创建解锁按钮
lock_mode_button = tk.Button(window, text="解锁/加锁", command=toggle_lock)
lock_mode_button.grid(row=2, column=1)

# 显示当前解锁状态
if remoterData['RCLock'] == 0:
    lock_mode_label = tk.Label(window, text=f'Lock Mode:已解锁')
elif remoterData['RCLock'] == 1:
    lock_mode_label = tk.Label(window, text=f'Lock Mode:已加锁')
lock_mode_label.grid(row=3, column=1)

# 绑定鼠标事件
left_stick_canvas.bind('<B1-Motion>', move_left_stick)
right_stick_canvas.bind('<B1-Motion>', move_right_stick)
right_stick_canvas.bind('<ButtonRelease-1>', reset_right_stick)  # 鼠标释放时重置右摇杆

# 监听键盘输入
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# 定时记录摇杆值
start_time = time.time()
record_to_csv()

# 持续发送数据包
send_packet_data_periodically()
update_joystick_positions() # 初始为零，需要先更新一下像素点位置
# 启动主窗口
window.mainloop()

# 关闭文件
csv_file.close()
