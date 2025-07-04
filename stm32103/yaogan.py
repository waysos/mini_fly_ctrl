# 双摇杆控制器
import tkinter as tk
import csv
from pynput import keyboard
import time

# 初始化全局变量存储摇杆值
left_stick = {'x': 0, 'y': 0}
right_stick = {'x': 0, 'y': 0}
xs_dis = 0.1  # 每次移动的像素

# 创建csv文件并写入表头
csv_file = open('joystick_values.csv', mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Time (s)', 'Left Stick X', 'Left Stick Y', 'Right Stick X', 'Right Stick Y'])
csv_file.flush()  # 刷新缓冲区

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
    except AttributeError:
        pass
    update_joystick_positions()

def on_release(key):
    if key == keyboard.Key.esc:
        return False  # 退出监听

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

    left_stick_label.config(text=f'Left Stick: X={left_stick["x"]/2:.2f}, Y={left_stick["y"]/2:.2f}')
    right_stick_label.config(text=f'Right Stick: X={right_stick["x"]/2:.2f}, Y={right_stick["y"]/2:.2f}')

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
window.geometry("600x350")

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
left_stick_label = tk.Label(window, text=f'Left Stick: X={left_stick["x"]/2:.2f}, Y={left_stick["y"]/2:.2f}')
left_stick_label.grid(row=1, column=0)

right_stick_label = tk.Label(window, text=f'Right Stick: X={right_stick["x"]/2:.2f}, Y={right_stick["y"]/2:.2f}')
right_stick_label.grid(row=1, column=1)

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

# 启动主窗口
window.mainloop()

# 关闭文件
csv_file.close()