import struct

def hex_to_float(hex_str):
    # 检查输入是否为8个字符（32位浮点数需要4字节，8个十六进制字符）
    if len(hex_str) != 8:
        raise ValueError("输入必须是8个十六进制字符")
    
    # 将十六进制字符串转换为字节序列
    bytes_le = bytes.fromhex(hex_str)
    
    # 以小端序解包为32位浮点数
    value = struct.unpack('<f', bytes_le)[0]
    return value

# 测试输入 "0000a041"
hex_value = "0000a040"
result = hex_to_float(hex_value)
print(f"浮点数值: {result}")