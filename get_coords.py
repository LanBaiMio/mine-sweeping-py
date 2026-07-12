import pyautogui
from pynput.keyboard import KeyCode, Listener

coords = []

def on_press(key):
    if isinstance(key, KeyCode):
        if key.char == '1':
            x, y = pyautogui.position()
            coords.append((x, y))
            print(f'已记录坐标 {len(coords)}: ({x}, {y})')
            if len(coords) == 2:
                return False

print('=' * 50)
print('坐标获取工具')
print('=' * 50)
print('1. 打开扫雷游戏: https://www.minesweeper.cn/')
print('2. 将鼠标移动到游戏区域的左上角')
print('3. 按键盘上的数字键 "1" 记录左上角坐标')
print('4. 将鼠标移动到游戏区域的右下角')
print('5. 按键盘上的数字键 "1" 记录右下角坐标')
print('=' * 50)
print('等待按键...')

with Listener(on_press=on_press) as listener:
    listener.join()

x1, y1 = coords[0]
x2, y2 = coords[1]
width = x2 - x1
height = y2 - y1

print('\n' + '=' * 50)
print('计算结果:')
print(f'左上角: ({x1}, {y1})')
print(f'右下角: ({x2}, {y2})')
print(f'宽度: {width}')
print(f'高度: {height}')
print('-' * 50)
print(f'请将以下内容复制到 config.py 中:')
print(f'BG_REGION = ({x1}, {y1}, {width}, {height})')
print('=' * 50)