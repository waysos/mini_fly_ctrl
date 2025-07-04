import serial
import struct
import tkinter as tk
from tkinter import ttk

# 打开串口
ser = serial.Serial('COM10', 9600, timeout=1)

# 缓存不完整帧
buffer = b''

def hex_to_signed_int(hex_str, bit_length=16):
    value = int(hex_str, 16)
    if value & (1 << (bit_length - 1)):
        value -= 1 << bit_length
    return value

def hex_str(num_zu):
    hex_str = num_zu.hex()
    hex_value = f"0x{hex_str}"
    return hex_value

def parse_status_frame(frame):
    if len(frame) < 13:
        print("Invalid frame length")
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
    
    # 更新GUI中的变量
    update_gui(roll_z, pitch_z, yaw_z, altitude_z)

def parse_avp_frame(frame):
    if len(frame) < 13:
        print("Invalid frame length")
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

    # 更新GUI中的变量
    update_gui_avp(a_x_c, a_y_c, a_z_c, v_x_c, v_y_c, v_z_c, q_x_c, q_y_c, q_z_c)

def process_frame(frame):
    if len(frame) >= 3 and frame[:3] == b'\xaa\xaa\x01':
        print(f"Received Status Data: {frame.hex()}")
        parse_status_frame(frame)
    elif len(frame) >= 3 and frame[:3] == b'\xaa\xaa\xf1':
        print(f"Received avp Data: {frame.hex()}")
        parse_avp_frame(frame)

def read_serial_data():
    global buffer
    while True:
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

def update_gui(roll, pitch, yaw, altitude):
    roll_label.config(text=f"Roll: {roll:.2f}")
    pitch_label.config(text=f"Pitch: {pitch:.2f}")
    yaw_label.config(text=f"Yaw: {yaw:.2f}")
    altitude_label.config(text=f"Altitude: {altitude:.2f}")
    root.update()

def update_gui_avp(a_x, a_y, a_z, v_x, v_y, v_z, q_x, q_y, q_z):
    a_x_label.config(text=f"a_x: {a_x}")
    a_y_label.config(text=f"a_y: {a_y}")
    a_z_label.config(text=f"a_z: {a_z}")
    v_x_label.config(text=f"v_x: {v_x}")
    v_y_label.config(text=f"v_y: {v_y}")
    v_z_label.config(text=f"v_z: {v_z}")
    q_x_label.config(text=f"q_x: {q_x}")
    q_y_label.config(text=f"q_y: {q_y}")
    q_z_label.config(text=f"q_z: {q_z}")
    root.update()

# 创建主窗口
root = tk.Tk()
root.title("Serial Data Viewer")

# 创建标签用于显示数据
roll_label = ttk.Label(root, text="Roll: 0.00")
roll_label.pack()

pitch_label = ttk.Label(root, text="Pitch: 0.00")
pitch_label.pack()

yaw_label = ttk.Label(root, text="Yaw: 0.00")
yaw_label.pack()

altitude_label = ttk.Label(root, text="Altitude: 0.00")
altitude_label.pack()

a_x_label = ttk.Label(root, text="a_x: 0")
a_x_label.pack()

a_y_label = ttk.Label(root, text="a_y: 0")
a_y_label.pack()

a_z_label = ttk.Label(root, text="a_z: 0")
a_z_label.pack()

v_x_label = ttk.Label(root, text="v_x: 0")
v_x_label.pack()

v_y_label = ttk.Label(root, text="v_y: 0")
v_y_label.pack()

v_z_label = ttk.Label(root, text="v_z: 0")
v_z_label.pack()

q_x_label = ttk.Label(root, text="q_x: 0")
q_x_label.pack()

q_y_label = ttk.Label(root, text="q_y: 0")
q_y_label.pack()

q_z_label = ttk.Label(root, text="q_z: 0")
q_z_label.pack()

# 启动串口数据读取线程
import threading
thread = threading.Thread(target=read_serial_data)
thread.daemon = True
thread.start()

# 启动主循环
root.mainloop()

# 关闭串口
ser.close()