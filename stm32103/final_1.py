import tkinter as tk
import csv
from pynput import keyboard
import time
import serial
import struct
import threading

# 初始化全局变量
left_stick = {'x': 0, 'y': 0}  # 左摇杆
right_stick = {'x': 0, 'y': 0}  # 右摇杆
xs_dis = 0.1  # 每次移动的像素
buffer = b''  # 串口数据缓冲区
start_time = time.time()

# 摇杆更新标志
update_needed = False


# 共享数据（从串口读取的数据）
shared_data = {
    'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0, 'altitude': 0.0,
    'a_x': 0, 'a_y': 0, 'a_z': 0,
    'v_x': 0, 'v_y': 0, 'v_z': 0,
    'q_x': 0, 'q_y': 0, 'q_z': 0
}

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

# 创建串口连接
ser = serial.Serial('COM10', 9600, timeout=1)

# 创建 CSV 文件并写入表头
csv_file = open('flight_data.csv', mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow([
    'Time (s)', 'Yaw', 'Thrust', 'Roll', 'Pitch',
    'Measured Roll', 'Measured Pitch', 'Measured Yaw', 'Measured Altitude',
    'a_x', 'a_y', 'a_z', 'v_x', 'v_y', 'v_z', 'q_x', 'q_y', 'q_z'
])
csv_file.flush()

# 线程锁
serial_lock = threading.Lock()  # 保护串口访问
data_lock = threading.Lock()    # 保护共享数据

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

def send_packet_CMD(CMD_MODE=CMD_FLIGHT_LAND):
    with serial_lock:
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

# 定时发送数据包
def send_packet_data_periodically():
    send_packet_DATA(ser)
    window.after(10, send_packet_data_periodically)  # 每 10ms 发送一次

# 16位十六进制转有符号整数
def hex_to_signed_int(hex_str, bit_length=16):
    value = int(hex_str, 16)
    if value & (1 << (bit_length - 1)):
        value -= 1 << bit_length
    return value

# 定义一个函数，将输入的整数转换为十六进制字符串
def hex_str(num_zu):
    # 将整数转换为十六进制字符串
    hex_str = num_zu.hex()
    # 在十六进制字符串前加上"0x"
    hex_value = f"0x{hex_str}"
    # 返回转换后的十六进制字符串
    return hex_value

# 处理串口数据帧
def process_frame(frame):
    print(f"Processing frame: {frame.hex()}")  # 调试输出
    if len(frame) >= 3 and frame[:3] == b'\xaa\xaa\x01':
        print("Status frame detected")
        parse_status_frame(frame)
    elif len(frame) >= 3 and frame[:3] == b'\xaa\xaa\xf1':
        print("AVP frame detected")
        parse_avp_frame(frame)

def parse_status_frame(frame):
    if len(frame) < 13:
        return
    
    roll = hex_str(frame[4:6])
    pitch = hex_str(frame[6:8])
    yaw = hex_str(frame[8:10])
    altitude = hex_str(frame[10:14])
    
    roll_c = hex_to_signed_int(roll, 16)
    pitch_c = hex_to_signed_int(pitch, 16)
    yaw_c = hex_to_signed_int(yaw, 16)
    altitude_c = hex_to_signed_int(altitude, 32)
    
    flight_mode = frame[14]
    unlock_status = frame[15]
    checksum = frame[16]   
    
    roll_z = roll_c / 100.0
    pitch_z = pitch_c / 100.0
    yaw_z = yaw_c / 100.0
    altitude_z = altitude_c / 100.0    
    
    with data_lock:
        shared_data['roll'] = roll_z
        shared_data['pitch'] = pitch_z
        shared_data['yaw'] = yaw_z
        shared_data['altitude'] = altitude_z

def parse_avp_frame(frame):
    if len(frame) < 13:
        return
    a_x = hex_str(frame[4:6])
    a_y = hex_str(frame[6:8])
    a_z = hex_str(frame[8:10])
    v_x = hex_str(frame[10:12])
    v_y = hex_str(frame[12:14])
    v_z = hex_str(frame[14:16])
    q_x = hex_str(frame[16:18])
    q_y = hex_str(frame[18:20])
    q_z = hex_str(frame[20:22])
    
    a_x_c = hex_to_signed_int(a_x, 16)
    a_y_c = hex_to_signed_int(a_y, 16)
    a_z_c = hex_to_signed_int(a_z, 16)
    
    v_x_c = hex_to_signed_int(v_x, 16)
    v_y_c = hex_to_signed_int(v_y, 16)
    v_z_c = hex_to_signed_int(v_z, 16)

    q_x_c = hex_to_signed_int(q_x, 16)
    q_y_c = hex_to_signed_int(q_y, 16)
    q_z_c = hex_to_signed_int(q_z, 16)
    with data_lock:
        shared_data['a_x'] = a_x_c
        shared_data['a_y'] = a_y_c
        shared_data['a_z'] = a_z_c
        shared_data['v_x'] = v_x_c
        shared_data['v_y'] = v_y_c
        shared_data['v_z'] = v_z_c
        shared_data['q_x'] = q_x_c
        shared_data['q_y'] = q_y_c
        shared_data['q_z'] = q_z_c

# 读取串口数据
def read_serial_data():
    global buffer
    while True:
        with serial_lock:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                buffer += data
                while True:
                    start_index = buffer.find(b'\xaa\xaa')
                    if start_index == -1:
                        break
                    if start_index > 0:
                        buffer = buffer[start_index:]
                    if len(buffer) < 4:
                        break
                    data_length = buffer[3]
                    total_length = 2 + 1 + 1 + data_length + 1
                    if len(buffer) < total_length:
                        break
                    frame = buffer[:total_length]
                    process_frame(frame)
                    buffer = buffer[total_length:]
        time.sleep(0.00001)  # 添加延时以降低 CPU 占用




# 保存数据到 CSV
def record_to_csv():
    current_time = time.time() - start_time
    with data_lock:
        csv_writer.writerow([
            current_time,
            remoterData['yaw'], remoterData['thrust'], remoterData['roll'], remoterData['pitch'],
            shared_data['roll'], shared_data['pitch'], shared_data['yaw'], shared_data['altitude'],
            shared_data['a_x'], shared_data['a_y'], shared_data['a_z'],
            shared_data['v_x'], shared_data['v_y'], shared_data['v_z'],
            shared_data['q_x'], shared_data['q_y'], shared_data['q_z']
        ])
    csv_file.flush()
    window.after(20, record_to_csv)

# 键盘控制
def on_press(key):
    global update_needed
    try:
        char = key.char
        if char == 'w': left_stick['y'] += xs_dis
        elif char == 's': left_stick['y'] -= xs_dis
        elif char == 'a': left_stick['x'] -= xs_dis
        elif char == 'd': left_stick['x'] += xs_dis
        elif char == 'i': right_stick['y'] += xs_dis
        elif char == 'k': right_stick['y'] -= xs_dis
        elif char == 'j': right_stick['x'] -= xs_dis
        elif char == 'l': right_stick['x'] += xs_dis
        elif char == 'b': left_stick.update({'x': 0, 'y': 0}); right_stick.update({'x': 0, 'y': 0})
        elif char == 't': send_packet_CMD(CMD_FLIGHT_LAND)
        elif char == 'e': send_packet_CMD(CMD_EMER_STOP)
    except AttributeError:
        pass
    update_needed = True  # 标记需要更新
 
# 摇杆更新——键盘控制相关   
# 修改periodic_update函数，移除update_needed标志
def periodic_update():
    update_joystick_positions()
    window.after(50, periodic_update)  # 每50ms更新一次

def on_release(key):
    if key == keyboard.Key.esc:
        return False

# 数值映射
def map_value(value, min_in=-2, max_in=2, min_out=0, max_out=100):
    return (value - min_in) / (max_in - min_in) * (max_out - min_out) + min_out

# 更新摇杆位置和 GUI
def update_joystick_positions():
    left_stick['x'] = max(-2, min(left_stick['x'], 2))
    left_stick['y'] = max(-2, min(left_stick['y'], 2))
    right_stick['x'] = max(-2, min(right_stick['x'], 2))
    right_stick['y'] = max(-2, min(right_stick['y'], 2))

    left_stick_canvas.delete('stick')
    right_stick_canvas.delete('stick')
    left_stick_canvas.create_oval(150 + left_stick['x'] * 50 - 10, 150 - left_stick['y'] * 50 - 10,
                                  150 + left_stick['x'] * 50 + 10, 150 - left_stick['y'] * 50 + 10,
                                  fill='red', tags='stick')
    right_stick_canvas.create_oval(150 + right_stick['x'] * 50 - 10, 150 - right_stick['y'] * 50 - 10,
                                   150 + right_stick['x'] * 50 + 10, 150 - right_stick['y'] * 50 + 10,
                                   fill='blue', tags='stick')

    remoterData['thrust'] = map_value(left_stick['y'], -2, 2, 0, 100)
    remoterData['yaw'] = map_value(left_stick['x'], -2, 2, -200, 200)
    remoterData['pitch'] = map_value(right_stick['y'], -2, 2, -50, 50)
    remoterData['roll'] = map_value(right_stick['x'], -2, 2, -50, 50)

    left_stick_label.config(text=f'Left: yaw={remoterData["yaw"]:.2f}, thrust={remoterData["thrust"]:.2f}')
    right_stick_label.config(text=f'Right: roll={remoterData["roll"]:.2f}, pitch={remoterData["pitch"]:.2f}')
    # 复制数据到局部变量，减少锁的持有时间
    with data_lock:
        roll = shared_data['roll']
        pitch = shared_data['pitch']
        yaw = shared_data['yaw']
        altitude = shared_data['altitude']
        a_x = shared_data['a_x']
        a_y = shared_data['a_y']
        a_z = shared_data['a_z']
        v_x = shared_data['v_x']
        v_y = shared_data['v_y']
        v_z = shared_data['v_z']
        q_x = shared_data['q_x']
        q_y = shared_data['q_y']
        q_z = shared_data['q_z']
        
    # 更新GUI组件
    roll_label.config(text=f"Roll: {roll:.2f}")
    pitch_label.config(text=f"Pitch: {pitch:.2f}")
    yaw_label.config(text=f"Yaw: {yaw:.2f}")
    altitude_label.config(text=f"Altitude: {altitude:.2f}")
    a_x_label.config(text=f"a_x: {a_x}")
    a_y_label.config(text=f"a_y: {a_y}")
    a_z_label.config(text=f"a_z: {a_z}")
    v_x_label.config(text=f"v_x: {v_x}")
    v_y_label.config(text=f"v_y: {v_y}")
    v_z_label.config(text=f"v_z: {v_z}")
    q_x_label.config(text=f"q_x: {q_x}")
    q_y_label.config(text=f"q_y: {q_y}")
    q_z_label.config(text=f"q_z: {q_z}")

# 控制模式切换
def toggle_ctrl_mode():
    remoterData['ctrlMode'] = {0: 1, 1: 3, 3: 0}[remoterData['ctrlMode']]
    ctrl_mode_label.config(text=f'Control Mode: {"手动" if remoterData["ctrlMode"] == 0 else "定高" if remoterData["ctrlMode"] == 1 else "定点"}模式')

# 解锁/加锁
def toggle_lock():
    remoterData['RCLock'] = 1 - remoterData['RCLock']
    lock_mode_label.config(text=f'Lock Mode: {"已解锁" if remoterData["RCLock"] == 0 else "已加锁"}')

# 鼠标控制
def move_left_stick(event):
    left_stick['x'] = (event.x - 150) / 50
    left_stick['y'] = (150 - event.y) / 50
    update_joystick_positions()

def move_right_stick(event):
    right_stick['x'] = (event.x - 150) / 50
    right_stick['y'] = (150 - event.y) / 50
    update_joystick_positions()

def reset_right_stick(event):
    right_stick['x'] = 0
    right_stick['y'] = 0
    update_joystick_positions()

# 创建 GUI
window = tk.Tk()
window.title("飞行控制器")
window.geometry("900x600")

# 左摇杆区域
left_stick_frame = tk.Frame(window, width=300, height=300)
left_stick_frame.grid(row=0, column=0)
left_stick_canvas = tk.Canvas(left_stick_frame, width=300, height=300, bg='white')
left_stick_canvas.create_rectangle(50, 50, 250, 250, outline="black")
left_stick_canvas.pack()

# 右摇杆区域
right_stick_frame = tk.Frame(window, width=300, height=300)
right_stick_frame.grid(row=0, column=1)
right_stick_canvas = tk.Canvas(right_stick_frame, width=300, height=300, bg='white')
right_stick_canvas.create_rectangle(50, 50, 250, 250, outline="black")
right_stick_canvas.pack()

# 数据显示区域
data_frame = tk.Frame(window, width=300, height=600)
data_frame.grid(row=0, column=2, rowspan=2)

left_stick_label = tk.Label(data_frame, text="Left: yaw=0.00, thrust=0.00")
left_stick_label.pack()
right_stick_label = tk.Label(data_frame, text="Right: roll=0.00, pitch=0.00")
right_stick_label.pack()
roll_label = tk.Label(data_frame, text="Roll: 0.00")
roll_label.pack()
pitch_label = tk.Label(data_frame, text="Pitch: 0.00")
pitch_label.pack()
yaw_label = tk.Label(data_frame, text="Yaw: 0.00")
yaw_label.pack()
altitude_label = tk.Label(data_frame, text="Altitude: 0.00")
altitude_label.pack()
a_x_label = tk.Label(data_frame, text="a_x: 0")
a_x_label.pack()
a_y_label = tk.Label(data_frame, text="a_y: 0")
a_y_label.pack()
a_z_label = tk.Label(data_frame, text="a_z: 0")
a_z_label.pack()
v_x_label = tk.Label(data_frame, text="v_x: 0")
v_x_label.pack()
v_y_label = tk.Label(data_frame, text="v_y: 0")
v_y_label.pack()
v_z_label = tk.Label(data_frame, text="v_z: 0")
v_z_label.pack()
q_x_label = tk.Label(data_frame, text="q_x: 0")
q_x_label.pack()
q_y_label = tk.Label(data_frame, text="q_y: 0")
q_y_label.pack()
q_z_label = tk.Label(data_frame, text="q_z: 0")
q_z_label.pack()

# 按钮和状态
ctrl_mode_button = tk.Button(window, text="切换控制模式", command=toggle_ctrl_mode)
ctrl_mode_button.grid(row=1, column=0)
ctrl_mode_label = tk.Label(window, text="Control Mode: 定高模式")
ctrl_mode_label.grid(row=2, column=0)

lock_mode_button = tk.Button(window, text="解锁/加锁", command=toggle_lock)
lock_mode_button.grid(row=1, column=1)
lock_mode_label = tk.Label(window, text="Lock Mode: 已解锁")
lock_mode_label.grid(row=2, column=1)

# 绑定事件
left_stick_canvas.bind('<B1-Motion>', move_left_stick)
right_stick_canvas.bind('<B1-Motion>', move_right_stick)
right_stick_canvas.bind('<ButtonRelease-1>', reset_right_stick)

# 启动键盘监听
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# 启动读取线程
read_thread = threading.Thread(target=read_serial_data, daemon=True)
read_thread.start()

# 定时任务
update_joystick_positions()
send_packet_data_periodically()
record_to_csv()
periodic_update()

# 主循环
window.mainloop()

# 清理
csv_file.close()
ser.close()