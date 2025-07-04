import serial
import struct
import time

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
    'ctrlMode': 0,       # 控制模式（0为手动模式，1为定高模式，3为定点模式）
    'flightMode': 0,     # 飞行模式（0为X-mode 1为无头模式）
    'RCLock': 0          # 遥控器锁定状态（解锁）
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

# 发送数据包到设备 输入为串口对象和命令类型
def send_packet_CMD(serial_port, CMD_MODE = CMD_FLIGHT_LAND):
    # 获取构建的控制命令数据包
    packet = create_packet_CMD(CMD_MODE)
    
    # 发送数据包
    serial_port.write(packet)
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
def send_data_for_duration(serial_port, duration=3, interval=0.001):
    # 计算循环的次数，duration / interval 即为需要的循环次数
    iterations = int(duration / interval)
    
    for _ in range(iterations):
        # 发送数据包
        send_packet_DATA(serial_port)
        
        # 接收数据并打印（可选）
        receive_packet(serial_port)
        
        # 延迟 interval 秒
        time.sleep(interval)

# 主函数
def main():
    
    # 设置控制数据
    remoterData['roll'] = 10.0 # 设置roll为5°
    remoterData['thrust'] = 50.0 # 设置thrust为50
    remoterData['ctrlMode'] = 1 # 设置控制模式为定高模式

    
    packet = create_packet_DATA()  
    # 发送数据
    print(f"数据包已发送: {packet.hex()}")


if __name__ == '__main__':
    main()
