"""
光模块(CPO)板块配置信息
"""

# 核心龙头
CORE_STOCKS = {
    "300308": "中际旭创",
    "300502": "新易盛",
    "300394": "天孚通信",
}

# 二线/相关标的
RELATED_STOCKS = {
    "002281": "光迅科技",
    "300548": "博创科技",
    "600487": "亨通光电",
    "300442": "润泽科技", # CPO相关液冷
    "600745": "闻泰科技",
    "000988": "华工科技",
    "300136": "信维通信",
    "688052": "纳芯微",
}

# 合并所有关注列表
ALL_STOCKS = {**CORE_STOCKS, **RELATED_STOCKS}

# 分析配置
START_DATE = "20240101"  # 默认分析起始日期
DATA_DIR = "data/optical_module"  # 数据保存路径
OUTPUT_DIR = "examples/Optical_Module/output"  # 结果输出路径
