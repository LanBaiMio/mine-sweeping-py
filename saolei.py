import matplotlib.pyplot as plt
import numpy as np
import pyautogui
from PIL import Image
from keras.models import load_model
from multiprocess import Pool
from pynput.keyboard import KeyCode, Listener
import random
import os
from openai import OpenAI
from config import *
from time import time

model = load_model('recognize_new')  # 已训练的CNN

current_mode = CURRENT_MODE

def switch_mode():
    global current_mode, BG_REGION, ROWS, COLS, row_size, cols_size
    
    current_mode = (current_mode + 1) % 4
    config = MODE_CONFIGS[current_mode]
    
    BG_REGION = config['bg_region'] if config['bg_region'] else (0, 0, 0, 0)
    ROWS = config['rows']
    COLS = config['cols']
    row_size = BG_REGION[3] / ROWS if ROWS > 0 else 0
    cols_size = BG_REGION[2] / COLS if COLS > 0 else 0
    
    import os
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    import re
    content = re.sub(r'CURRENT_MODE = \d', f'CURRENT_MODE = {current_mode}', content)
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'已切换到{config["name"]}，区域: {BG_REGION}，{ROWS}x{COLS}')


# 获取截图
def screen_shoot(rows=ROWS, cols=COLS, region=BG_REGION):
    resize_shape = (32, 32)
    board = []
    back_ground = np.array(pyautogui.screenshot(region=region))
    for j in range(rows):
        board_r = []
        for i in range(cols):
            l, u, r, d = [int(o) for o in
                          (i * cols_size, j * row_size, i * cols_size + cols_size, j * row_size + row_size)]
            crop = back_ground[u:d + 1, l:r + 1]
            crop = Image.fromarray(crop).resize(resize_shape)  # 将数组转成图像，resize之后再转成数组
            crop = np.array(crop)
            board_r.append(crop)
        board.append(board_r)
    return board


# 使用cnn识别图像
def get_cnn_board(model, rows=ROWS, cols=COLS, region=BG_REGION):
    # 将所有格子层叠排列，一起输入到cnn，比一个一个输入cnn计算速度快很多
    board = screen_shoot(rows, cols, region)
    sq_board = []
    for i in range(len(board)):
        sq_board += board[i]
    sq_board = np.array(sq_board) / 255.

    sq_pred = np.argmax(model.predict(sq_board), axis=1)  # 获取cnn的预测值
    sq_pred = np.array([net_decoder[i] for i in sq_pred])  # 解码cnn的预测值
    sq_pred = sq_pred.reshape((rows, cols))
    return sq_pred


# 显示截图结果
def show_screen_shoot(board=None):
    if board is None:
        board = screen_shoot()
    b = np.zeros((ROWS * 32, COLS * 32, 3))
    for i in range(ROWS):
        for j in range(COLS):
            b[i * 32:i * 32 + 32, j * 32:j * 32 + 32] = board[i][j]
    b = b / 255
    print(b)
    plt.imshow(b)
    plt.show()


# 显示识别结果
def show_recognized(board):
    plt.imshow(board)
    plt.show()


# 使用pyautogui识别图像
def get_board(rows=ROWS, cols=COLS, bg_region=BG_REGION, imags=None):
    # 旧版本使用pyautogui 识别图片，虽然调用的是opencv的接口但耗时太长
    board = -2 * np.ones((rows, cols), dtype='i2')
    back_ground = pyautogui.screenshot(region=bg_region)
    for num in imags:
        num_locations = pyautogui.locateAll(imags[num], back_ground, confidence=0.99)
        for loc in num_locations:
            center = pyautogui.center(loc)
            board[int(center[1] / row_size), int(center[0] // cols_size)] = num
    return board


# 将识别出来的图片保存到对应文件夹，可以增加训练样本
def record_board(model, path=PATH):
    resize_shape = (32, 32)
    sq_board = []
    back_ground = pyautogui.screenshot(region=BG_REGION)
    back_ground = np.array(back_ground)
    crops = []
    for j in range(ROWS):
        crops_r = []
        for i in range(COLS):
            l, u, r, d = [int(o) for o in
                          (i * cols_size, j * row_size, i * cols_size + cols_size, j * row_size + row_size)]
            crop = back_ground[u:d + 1, l:r + 1]
            crops_r.append(Image.fromarray(crop))

            crop = Image.fromarray(crop).resize(resize_shape)
            crop = np.array(crop)
            sq_board.append(crop)
        crops.append(crops_r)
    sq_board = np.array(sq_board)
    sq_pred = np.argmax(model.predict(sq_board), axis=1)
    sq_pred = np.array([net_decoder[i] for i in sq_pred])
    sq_pred = sq_pred.reshape((ROWS, COLS))
    for i in range(ROWS):
        for j in range(COLS):
            save_path = path + '\\' + str(sq_pred[i][j]) + '\\' + str(sq_pred[i][j]) + '_' + str(
                int(time() % 10000)) + '.png'
            crops[i][j].save(save_path)


# AI算法
def deal_board(board):
    to_flag = set()
    to_click = set()
    not_sure = dict()
    pad_board = np.pad(board, 1)
    row, col = board.shape
    while 1:
        action_nums = to_flag.__len__() + to_click.__len__()
        # 第一步，标记可以标记的旗子，把位置保存到to_flag
        for i in range(1, row + 1):
            for j in range(1, col + 1):
                if pad_board[i, j] > 0:
                    n9 = pad_board[i - 1:i + 2, j - 1:j + 2]
                    unknown_mask = (n9 == -2)
                    maybe_bomb = (n9 == -2) | (n9 == -10) | (n9 == -1)
                    if maybe_bomb.sum() == pad_board[i, j]:
                        n9[unknown_mask] = -1
                        for iii in range(3):
                            for jjj in range(3):
                                if unknown_mask[iii, jjj]:
                                    to_flag.add((iii + i - 1, jjj + j - 1))

        # 第二步消去旗子 用-10表示消去的旗子
        for i in range(1, row + 1):
            for j in range(1, col + 1):
                if pad_board[i, j] == -1:
                    pad_board[i, j] = -10
                    for ii in range(3):
                        for jj in range(3):
                            if pad_board[ii + i - 1, jj + j - 1] > 0:
                                pad_board[ii + i - 1, jj + j - 1] -= 1

        # 第三步，寻找可翻开的格子
        for i in range(1, row + 1):
            for j in range(1, col + 1):
                if pad_board[i, j] == 0:
                    for ii in range(3):
                        for jj in range(3):
                            if pad_board[ii + i - 1, jj + j - 1] == -2:
                                to_click.add((ii + i - 1, jj + j - 1))
                                pad_board[ii + i - 1, jj + j - 1] = -23

        # 第四步，正常办法解决不了，开启推理模式
        if action_nums == to_flag.__len__() + to_click.__len__():
            # 对每个没有翻开的格子a，如果周围有翻开的格子b1，那么将b1周围的所有未翻开的格子list1和b1的大小保存到一个列表，
            #                    如果周围有翻开的格子b2，那么将b2周围的所有未翻开的格子list2和b2的大小保存到一个列表，...
            # 最后得到一个关联关系  a的位置：与a有关的未翻开的格子的位置及隐藏地雷数量，保存到not_sure中
            for i in range(1, row + 1):
                for j in range(1, col + 1):
                    if pad_board[i, j] > 0:
                        not_sure_set = set()
                        for ii in range(3):
                            for jj in range(3):
                                if pad_board[ii + i - 1, jj + j - 1] == -2:
                                    not_sure_set.add((ii + i - 1, jj + j - 1))
                        for co_pos in not_sure_set:
                            not_sure[co_pos] = not_sure.get(co_pos, []) + ([[not_sure_set, pad_board[i, j]]])
            #        * * *             *   *  *   *   *
            #        * 1 ？            ？   4  ？  1   ？
            #        * 1 ？            ？   *  ？  *   ？
            #        * * ？            ？   *  *   *   ？
            # 用*代表墙壁，？代表未翻开的格子，上图左边可以推理出最下面的问号不是地雷，
            # 上图右边可以推理出左边三个问号是地雷，最右边三个问号不是地雷
            for k, v in not_sure.items():
                for i in range(len(v)):
                    for j in range(1, len(v)):
                        s1, n1 = v[i]
                        s2, n2 = v[j]
                        if s1 == s2: continue
                        if s1.issubset(s2):
                            minus_s = s2 - s1
                            if n2 - n1 == minus_s.__len__():
                                for p in minus_s:
                                    to_flag.add(p)
                            elif n2 == n1:
                                for p in minus_s:
                                    to_click.add(p)
                        if s2.issubset(s1):
                            minus_s = s1 - s2
                            if n1 - n2 == minus_s.__len__():
                                for p in minus_s:
                                    to_flag.add(p)
                            elif n2 == n1:
                                for p in minus_s:
                                    to_click.add(p)

                        # 推理模式增强版
                        mixed = s1 & s2
                        if n1 > n2 and s1.__len__() - mixed.__len__() == n1 - n2:
                            for p in s1 - mixed:
                                to_flag.add(p)
                            for p in s2 - mixed:
                                to_click.add(p)
                        if n1 < n2 and s2.__len__() - mixed.__len__() == n2 - n1:
                            for p in s2 - mixed:
                                to_flag.add(p)
                            for p in s1 - mixed:
                                to_click.add(p)

            if action_nums == to_flag.__len__() + to_click.__len__():
                break
    return to_click, to_flag


def game_once(duration=0.01, interval=0.01):
    board = get_cnn_board(model)
    to_click, to_flag = deal_board(board)

    print('click_pos', to_click)
    print('flag_pos', to_flag)
    for lc in sorted(to_click):
        r, c = lc
        pos = (BG_REGION[0] + (c - 0.5) * cols_size, BG_REGION[1] + (r - 0.5) * row_size)
        pyautogui.click(pos, duration=duration)
        pyautogui.sleep(interval)
    for lc in sorted(to_flag):
        r, c = lc
        pos = (BG_REGION[0] + (c - 0.5) * cols_size, BG_REGION[1] + (r - 0.5) * row_size)
        pyautogui.rightClick(pos, duration=duration)
        pyautogui.sleep(interval)
    
    while not to_click and not to_flag:
        board = get_cnn_board(model)
        if np.any(board == 9):
            print('检测到炸弹，游戏结束')
            pyautogui.moveTo(1, 1)
            return False
        
        unopened_cells = []
        for r in range(ROWS):
            for c in range(COLS):
                if board[r][c] == -2:
                    unopened_cells.append((r, c))
        
        unopened_count = len(unopened_cells)
        print(f'死局扫描完成，未翻开格子数: {unopened_count}')
        
        if unopened_count == 0:
            print('所有格子已翻开，游戏完成')
            pyautogui.moveTo(1, 1)
            return False
        
        r, c = random.choice(unopened_cells)
        pos = (BG_REGION[0] + (c - 0.5) * cols_size, BG_REGION[1] + (r - 0.5) * row_size)
        pyautogui.click(pos, duration=duration)
        pyautogui.sleep(0.1)
        print('死局，随机点击', (r, c))
        
        pyautogui.sleep(0.2)
        board = get_cnn_board(model)
        to_click, to_flag = deal_board(board)
        print('click_pos', to_click)
        print('flag_pos', to_flag)
    
    return True


def game_all():
    board = get_cnn_board(model)
    if np.all(board == -2):
        center_r, center_c = ROWS // 2, COLS // 2
        pos = (BG_REGION[0] + (center_c - 0.5) * cols_size, BG_REGION[1] + (center_r - 0.5) * row_size)
        pyautogui.click(pos, duration=0.01)
        pyautogui.sleep(0.1)
    while game_once():
        board = get_cnn_board(model)
        if 9 in board:
            print('检测到炸弹，游戏结束')
            break


def log_operation(action, detail=''):
    from datetime import datetime
    with open('log.txt', 'a', encoding='utf-8') as f:
        f.write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {action} - {detail}\n')

def on_press(key):
    # print(key,str(key))
    if isinstance(key, KeyCode):
        if key.char == 'a':
            game_once()

        elif key.char == 'b':
            log_operation('AI自动扫雷', '用户按下B键')
            game_all()

        elif key.char == 'h':
            switch_mode()

        elif key.char == 'r':
            record_board(model)

        elif key.char == 's':  # 显示识别结果
            pool = Pool(1)
            pool.apply_async(show_recognized, args=(get_cnn_board(model),))
            pool.close()
            pool.join()

        elif key.char == 'c':  # 显示截图结果
            pool = Pool(1)
            pool.apply_async(show_screen_shoot)
            pool.close()
            pool.join()

        elif key.char == 'l':  # 将预测结果保存到situation.txt并调用大模型求解
            log_operation('大模型分析', '用户按下L键')
            board = get_cnn_board(model)
            with open('situation.txt', 'w') as f:
                for row in board:
                    f.write(' '.join(map(str, row)) + '\n')
            print('预测结果已保存到situation.txt')
            
            if LLM_API_BASE and LLM_API_KEY and LLM_MODEL_NAME:
                board_str = '\n'.join(' '.join(map(str, row)) for row in board)
                prompt = f"""这是一个扫雷游戏的棋盘状态，共{ROWS}行{COLS}列。
数字含义：
- -2：未翻开的格子
- -1：标记为旗子的格子
- 0-8：周围地雷数量
- 9：已翻开的地雷
当前棋盘状态：
{board_str}
请分析这个扫雷局面，给出可以确定是地雷的格子位置（行号,列号，从1开始）"""

                    # headers = {
                    #     'Content-Type': 'application/json',
                    #     'Authorization': f'Bearer {LLM_API_KEY}'
                    # }
                    # data = {
                    #     'model': LLM_MODEL_NAME,
                    #     'messages': [f'{{"role": "user", "content": "{prompt}"}}'],
                    #     'temperature': 0.1
                    # }
                    # response = requests.post(f'{LLM_API_BASE}/chat/completions', headers=headers, json=data)
                    # response.raise_for_status()
                    # result = response.json()
                    # answer = result['choices'][0]['message']['content']
                    
                    # print('大模型分析结果：')
                    # print(answer)
                try:
                    client = OpenAI(api_key=os.getenv(f"{LLM_API_KEY}"),
                                    base_url=LLM_API_BASE)
                    completion = client.chat.completions.create(
                    model=LLM_MODEL_NAME,
                    messages=[f'{{"role": "user", "content": "{prompt}"}}'])
                    print(completion.choices[0].message.content)
                except Exception as e:
                    print(f'调用大模型失败：{e}')
            else:
                print('未配置大模型API参数，请在config.py中填写LLM_API_BASE、LLM_API_KEY和LLM_MODEL_NAME')

        elif key.char == 'q':
            return False


def start_listen():
    with Listener(on_press=on_press) as listener:
        listener.join()


if __name__ == '__main__':
    print("AI扫雷程序已启动")
    start_listen()
