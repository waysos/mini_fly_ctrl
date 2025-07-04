import serial
import struct

# 打开串口
ser = serial.Serial('COM10', 9600, timeout=1)

# 缓存不完整帧
buffer = b''


def hex_to_signed_int(hex_str, bit_length=16):
    """
    将十六进制字符串转换为有符号整数。

    :param hex_str: 十六进制字符串（如 "0xfecf"）
    :param bit_length: 数据的位长度（如 16 位、32 位等）
    :return: 有符号整数
    """
    value = int(hex_str, 16)  # 将十六进制字符串转换为无符号整数
    if value & (1 << (bit_length - 1)):  # 检查最高位是否为 1（负数）
        value -= 1 << bit_length  # 转换为负数
    return value

def hex_str(num_zu):
    hex_str = num_zu.hex()  # 将字节转换为十六进制字符串
    hex_value = f"0x{hex_str}"  # 输出 "0xfecf0a0b"
    
    return hex_value

def parse_status_frame(frame):
    """解析 UP_STATUS 帧"""
    if len(frame) < 13:  # 检查帧长度是否足够
        print("Invalid frame length")
        return

    # 解析具体数据
    # roll = int.from_bytes(frame[4:6], byteorder='little', signed=True)
    # pitch = int.from_bytes(frame[6:8], byteorder='little', signed=True)
    # yaw = int.from_bytes(frame[8:10], byteorder='little', signed=True)
    # altitude = int.from_bytes(frame[10:14], byteorder='little', signed=True)
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

    # 数据处理
    # altitude_c = struct.unpack('>f', altitude)[0] # 高度处理
    roll_z = roll_c / 100.0  # 横滚角处理
    pitch_z = pitch_c / 100.0  # 俯仰角处理
    yaw_z = yaw_c / 100.0  # 偏航角处理
    altitude_z = altitude_c / 100.0  # 高度处理
    
    # 显示解析结果
    # print(f"Roll: {frame[4:6].hex()} Pitch: {frame[6:8].hex()} Yaw: {frame[8:10].hex()} Altitude: {frame[10:14].hex()}")
    print(f"Roll: {roll_z} Pitch: {pitch_z} Yaw: {yaw_z} Altitude: {altitude_z}")
    print("-" * 30)

def parse_avp_frame(frame):
    """解析 UP_STATUS 帧"""
    if len(frame) < 13:  # 检查帧长度是否足够
        print("Invalid frame length")
        return
    
    # 解析具体数据
    # roll = int.from_bytes(frame[4:6], byteorder='little', signed=True)
    # pitch = int.from_bytes(frame[6:8], byteorder='little', signed=True)
    # yaw = int.from_bytes(frame[8:10], byteorder='little', signed=True)
    # altitude = int.from_bytes(frame[10:14], byteorder='little', signed=True)
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


    # 数据处理
    # altitude_c = struct.unpack('>f', altitude)[0] # 高度处理
    # roll_z = roll_c / 100.0  # 横滚角处理
    # pitch_z = pitch_c / 100.0  # 俯仰角处理
    # yaw_z = yaw_c / 100.0  # 偏航角处理
    # altitude_z = altitude_c / 100.0  # 高度处理
    
    # 显示解析结果
    # print(f"Roll: {frame[4:6].hex()} Pitch: {frame[6:8].hex()} Yaw: {frame[8:10].hex()} Altitude: {frame[10:14].hex()}")
    print(f"a_x: {a_x_c} a_y: {a_y_c} a_z: {a_z_c}")
    print(f"v_x: {v_x_c} v_y: {v_y_c} v_z: {v_z_c}")
    print(f"q_x: {q_x_c} q_y: {q_y_c} q_z: {q_z_c}")
    print("-" * 30)

def process_frame(frame):
    """处理单个数据帧"""
    if len(frame) >= 3 and frame[:3] == b'\xaa\xaa\x01':
        print(f"Received Status Data: {frame.hex()}")
        # print("Received UP_STATUS Frame:")
        parse_status_frame(frame)
    elif len(frame) >= 3 and frame[:3] == b'\xaa\xaa\xf1':
        print(f"Received avp Data: {frame.hex()}")
        parse_avp_frame(frame)
    # else:
    #     print(f"Received Data (Invalid Frame): {frame.hex()}")

def read_serial_data():
    global buffer
    while True:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            buffer += data

            while True:
                # 查找帧头 "aa aa"
                start_index = buffer.find(b'\xaa\xaa')
                if start_index == -1:
                    break

                # 丢弃帧头前的无效数据
                if start_index > 0:
                    buffer = buffer[start_index:]

                # 检查是否包含基础头部（帧头2B + 消息ID1B + 数据长度1B）
                if len(buffer) < 4:  # 至少需要4字节才能解析基础头部
                    break

                # 提取数据长度字段（第4字节，索引3）
                data_length = buffer[3]  # 数据部分的字节数
                total_length = 2 + 1 + 1 + data_length + 1  # 帧头2 + ID1 + 长度1 + 数据N + 校验1

                # 检查是否包含完整帧
                if len(buffer) < total_length:
                    break

                # 提取完整帧并处理
                frame = buffer[:total_length]
                process_frame(frame)
                buffer = buffer[total_length:]  # 移除已处理部分

if __name__ == "__main__":
    try:
        print("Starting to read data from serial...")
        read_serial_data()  # 持续读取并打印数据
    except KeyboardInterrupt:
        print("Program interrupted.")
    finally:
        ser.close()  # 关闭串口连接
        print("Serial connection closed.")
