# 实现串口通信传输控制指令
import serial
import time

# 定义消息结构
DOWN_BYTE1 = 0xAA
DOWN_BYTE2 = 0xAF

# 下行命令
DOWN_REMOTOR = 0x50  # 控制电机

# 控制命令类型
REMOTOR_CMD = 0x00  # 控制命令标识符

# 控制命令（起飞/降落）
#define  CMD_GET_MSG        0x01    /*获取四轴信息（自检）*/
#define  CMD_GET_CANFLY        0x02    /*获取四轴是否能飞*/
#define  CMD_FLIGHT_LAND    0x03    /*起飞、降落*/
#define  CMD_EMER_STOP        0x04    /*紧急停机*/
#define  CMD_FLIP            0x05    /*4D翻滚*/
#define  CMD_POWER_MODULE    0x06    /*打开关闭扩展模块电源*/
#define  CMD_LEDRING_EFFECT    0x07    /*设置RGB灯环效果*/
#define  CMD_POWER_VL53LXX    0x08    /*打开关闭激光*/
CMD_FLIGHT_LAND = 0x03

# 校验和计算函数
def calculate_checksum(data):
    # 步骤 1: 计算逐字节的和
    total_sum = sum(data)
    
    # 步骤 2: 对总和进行模 256 运算
    checksum = total_sum % 256
    
    # 步骤 3: 将校验和转换为十六进制
    checksum_hex = checksum
    return checksum_hex

# 构建数据包
def create_packet_flight_down():
    # 数据部分: [命令ID, 数据长度, 数据...]
    data = [
        DOWN_BYTE1,  # 帧头1
        DOWN_BYTE2,  # 帧头2
        DOWN_REMOTOR,  # 控制命令ID
        0x02,  # 数据长度: len(data) + 1（控制命令标识符）
        REMOTOR_CMD,  # 数据[0]: 控制命令标识符
        CMD_FLIGHT_LAND  # 数据[1]: 控制命令，起飞/降落
    ]
    
    # 计算校验和
    checksum = calculate_checksum(data)
    
    # 添加校验和到数据包末尾
    data.append(checksum)
    
    # 转换为字节格式发送
    return bytes(data)

# 发送数据包到设备
def send_packet_flight_down(serial_port):
    # 获取构建的控制命令数据包
    packet = create_packet_flight_down()
    
    # 发送数据包
    serial_port.write(packet)
    print(f"数据包已发送: {packet.hex()}")

# 主函数
def main():
    # 配置串口连接
    ser = serial.Serial('COM10', 9600, timeout=1)  # 根据实际串口号设置 COM 端口和波特率
    
    # 发送数据包-起飞
    send_packet_flight_down(ser)
    
    # time.sleep(1)  # 等待一段时间
    
    # 发送数据包-降落
    # send_packet_flight_down(ser)
    # 关闭串口
    ser.close()

if __name__ == '__main__':
    main()
