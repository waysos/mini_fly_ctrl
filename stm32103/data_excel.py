import serial
import pandas as pd
import time
import threading
import signal
import sys
from datetime import datetime
import os

# 全局退出标志
exit_event = threading.Event()
data_lock = threading.Lock()

# 串口配置
SERIAL_PORT = 'COM7'
BAUD_RATE = 50000

# 打开串口
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

# 缓存不完整帧
buffer = b''

# 文件路径
FILE_RPY_ALTITUDE = "rpy_altitude_data.xlsx"
FILE_OTHER = "other_data.xlsx"

# 初始化文件
if not os.path.exists(FILE_RPY_ALTITUDE):
    pd.DataFrame(columns=['Timestamp', 'Roll', 'Pitch', 'Yaw', 'Altitude']).to_excel(FILE_RPY_ALTITUDE, index=False)
if not os.path.exists(FILE_OTHER):
    pd.DataFrame(columns=['Timestamp', 'a_x', 'a_y', 'a_z', 'v_x', 'v_y', 'v_z', 'q_x', 'q_y', 'q_z']).to_excel(FILE_OTHER, index=False)

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    print("\n接收到终止信号，正在保存数据...")
    exit_event.set()
    # 等待串口线程结束
    if read_thread.is_alive():
        read_thread.join(timeout=2)
    # 关闭串口
    ser.close()
    print("程序安全退出")
    sys.exit(0)

def save_data(data, file_path, columns):
    """实时保存数据到Excel文件"""
    try:
        # 读取现有数据
        existing_df = pd.read_excel(file_path)
        # 追加新数据
        new_df = pd.DataFrame([data], columns=columns)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        # 保存数据
        combined_df.to_excel(file_path, index=False)
        print(f"已保存数据到 {file_path}")
    except Exception as e:
        print(f"保存文件 {file_path} 失败:", e)

def hex_to_signed_int(hex_str, bit_length=16):
    value = int(hex_str, 16)
    if value & (1 << (bit_length - 1)):
        value -= 1 << bit_length
    return value

def hex_str(num_zu):
    return f"0x{num_zu.hex()}"

def parse_status_frame(frame):
    if len(frame) < 13:
        print("Invalid frame length")
        return

    try:
        # 解析数据
        roll = hex_str(frame[4:6])
        pitch = hex_str(frame[6:8])
        yaw = hex_str(frame[8:10])
        altitude = hex_str(frame[10:14])
        
        # 转换为有符号整数
        roll_c = hex_to_signed_int(roll, 16)
        pitch_c = hex_to_signed_int(pitch, 16)
        yaw_c = hex_to_signed_int(yaw, 16)
        altitude_c = hex_to_signed_int(altitude, 32)
        
        # 转换单位
        roll_z = roll_c / 100.0
        pitch_z = pitch_c / 100.0
        yaw_z = yaw_c / 100.0
        altitude_z = altitude_c / 100.0
        
        # 记录数据
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        data = [timestamp, roll_z, pitch_z, yaw_z, altitude_z]
        
        # 实时保存数据
        save_data(data, FILE_RPY_ALTITUDE, columns_rpy_altitude)
    except Exception as e:
        print("状态帧解析错误:", e)

def parse_avp_frame(frame):
    if len(frame) < 13:
        print("Invalid frame length")
        return
    
    try:
        # 解析数据
        a_x = hex_str(frame[4:6])
        a_y = hex_str(frame[6:8])
        a_z = hex_str(frame[8:10])
        v_x = hex_str(frame[10:12])
        v_y = hex_str(frame[12:14])
        v_z = hex_str(frame[14:16])
        q_x = hex_str(frame[16:18])
        q_y = hex_str(frame[18:20])
        q_z = hex_str(frame[20:22])
        
        # 转换为有符号整数
        a_x_c = hex_to_signed_int(a_x, 16)
        a_y_c = hex_to_signed_int(a_y, 16)
        a_z_c = hex_to_signed_int(a_z, 16)
        v_x_c = hex_to_signed_int(v_x, 16)
        v_y_c = hex_to_signed_int(v_y, 16)
        v_z_c = hex_to_signed_int(v_z, 16)
        q_x_c = hex_to_signed_int(q_x, 16)
        q_y_c = hex_to_signed_int(q_y, 16)
        q_z_c = hex_to_signed_int(q_z, 16)
        
        # 记录数据
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        data = [timestamp, a_x_c, a_y_c, a_z_c, v_x_c, v_y_c, v_z_c, q_x_c, q_y_c, q_z_c]
        
        # 实时保存数据
        save_data(data, FILE_OTHER, columns_other)
    except Exception as e:
        print("AVP帧解析错误:", e)

def process_frame(frame):
    if len(frame) >= 3 and frame[:3] == b'\xaa\xaa\x01':
        print(f"Received Status Data: {frame.hex()}")
        parse_status_frame(frame)
    elif len(frame) >= 3 and frame[:3] == b'\xaa\xaa\xf1':
        print(f"Received avp Data: {frame.hex()}")
        parse_avp_frame(frame)

def read_serial_data():
    """改进的串口读取线程"""
    global buffer
    while not exit_event.is_set():
        try:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                buffer += data

                while not exit_event.is_set():
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
        except serial.SerialException as e:
            print("串口异常:", e)
            exit_event.set()
        except Exception as e:
            print("读取异常:", e)

# 数据列定义
columns_rpy_altitude = ['Timestamp', 'Roll', 'Pitch', 'Yaw', 'Altitude']
columns_other = ['Timestamp', 'a_x', 'a_y', 'a_z', 'v_x', 'v_y', 'v_z', 'q_x', 'q_y', 'q_z']

# 注册信号处理
signal.signal(signal.SIGINT, signal_handler)

# 启动串口读取线程
read_thread = threading.Thread(target=read_serial_data)
read_thread.daemon = True
read_thread.start()

# 主循环
try:
    while not exit_event.is_set():
        time.sleep(0.1)  # 降低CPU占用
except Exception as e:
    print("主线程异常:", e)
finally:
    exit_event.set()
    if ser.is_open:
        ser.close()