import struct
def hex_to_signed_decimal(hex_str):
    # 将16进制字符串转换为无符号整数
    unsigned_value = int(hex_str, 16)
    # 判断是否为负数
    if unsigned_value >= 0x8000:
        signed_value = unsigned_value - 0x10000 
    else:
        signed_value = unsigned_value 
    
    return signed_value
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

hex_value = "0xfecf"
hex = hex_to_signed_int(hex_value)
# hex = int(hex_value,16)
# hex = int16_to_unsigned(hex_value)
print(hex)
