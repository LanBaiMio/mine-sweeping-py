# 游戏配置参数

# bg_region:游戏所在的屏幕位置(x,y,w,h)，x,y：区域左上角坐标，w,h：区域的宽和高
# 如果习惯用(x1,y1,x2,y2)的方式表示屏幕上的区域，请输入(x1,y1,x2-x1,y2-y1)

# 当前模式：0-基础, 1-中级, 2-专家, 3-自定义
CURRENT_MODE = 1

# 基础模式 (9x9)
BG_REGION_EASY = (1098, 388, 342, 340)
ROWS_EASY = 9
COLS_EASY = 9

# 中级模式 (16x16)
BG_REGION_MEDIUM = (967, 388, 603, 604)
ROWS_MEDIUM = 16
COLS_MEDIUM = 16

# 专家模式 (16x30)
BG_REGION_HARD = (707, 390, 1127, 602)
ROWS_HARD = 16
COLS_HARD = 30

# 自定义模式
BG_REGION_CUSTOM = ()
ROWS_CUSTOM = 9
COLS_CUSTOM = 9

# 当前模式的配置（根据CURRENT_MODE自动切换）
MODE_CONFIGS = [
    {'name': '基础模式', 'bg_region': BG_REGION_EASY, 'rows': ROWS_EASY, 'cols': COLS_EASY},
    {'name': '中级模式', 'bg_region': BG_REGION_MEDIUM, 'rows': ROWS_MEDIUM, 'cols': COLS_MEDIUM},
    {'name': '专家模式', 'bg_region': BG_REGION_HARD, 'rows': ROWS_HARD, 'cols': COLS_HARD},
    {'name': '自定义模式', 'bg_region': BG_REGION_CUSTOM, 'rows': ROWS_CUSTOM, 'cols': COLS_CUSTOM},
]

BG_REGION = MODE_CONFIGS[CURRENT_MODE]['bg_region'] if MODE_CONFIGS[CURRENT_MODE]['bg_region'] else (0, 0, 0, 0)
ROWS = MODE_CONFIGS[CURRENT_MODE]['rows']
COLS = MODE_CONFIGS[CURRENT_MODE]['cols']

# 计算出每个格子的大小
row_size = BG_REGION[3] / ROWS if ROWS > 0 else 0
cols_size = BG_REGION[2] / COLS if COLS > 0 else 0

# 编码和解码神经网络的输出。本程序中，-1表示这个格子是旗子，-2表示未翻开的格子，9表示翻开的地雷，0-8表示周围八个格子地雷数量，
net_encoder = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, -1: 10, -2: 11}
net_decoder = {v: k for k, v in net_encoder.items()}


# 图片保存路径
PATH = r'.\imgs'

# 大模型API配置（用户请自行填写）
LLM_API_BASE = ''
LLM_API_KEY = ''
LLM_MODEL_NAME = ''
