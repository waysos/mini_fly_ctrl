# 浮点数格式转换代码，转换为IEEE754标准32位浮点数 （小端字节序）
import struct

def float_to_ieee754_32bit(value):
    # 使用 struct 将浮点数打包为 IEEE 754 32 位格式
    packed = struct.pack('<f', value)  # '<f'表示小端字节序的float类型
    # 转换为十六进制表示
    hex_value = ''.join(f'{byte:02x}' for byte in packed)
    return hex_value

# 测试代码
value = 75.0
result = float_to_ieee754_32bit(value)
print(f'{value} 转换为 IEEE 754 标准 32 位小端浮点数是: 0x{result}')
