# AIQuant 项目配置完成! 🎉

## ✅ 已完成的工作

### 1. AkShare 安装
- ✅ AkShare 1.17.87 已成功安装
- ✅ Python 3.12.1 环境正常

### 2. 项目结构创建
```
AIQuant/
├── README.md              # 项目说明文档
├── requirements.txt       # 项目依赖
├── .gitignore            # Git忽略文件
├── test_install.py       # 安装测试脚本
├── config/               # 配置文件目录
│   └── config.yaml       # 主配置文件
├── src/                  # 源代码目录
│   ├── __init__.py
│   ├── data_fetch/       # 数据获取模块
│   │   ├── __init__.py
│   │   └── stock_data.py # 股票数据获取
│   ├── analysis/         # 数据分析模块
│   │   ├── __init__.py
│   │   └── technical.py  # 技术指标计算
│   ├── visualization/    # 数据可视化模块
│   │   ├── __init__.py
│   │   └── charts.py     # 图表绘制
│   └── utils/           # 工具函数
│       ├── __init__.py
│       └── helpers.py    # 辅助函数
├── notebooks/           # Jupyter笔记本
│   └── 01_quick_start.ipynb  # 快速入门教程
├── examples/            # 示例代码
│   └── example_basic.py # 基础使用示例
├── data/               # 数据存储目录
└── output/             # 输出结果目录
```

## 🚀 快速开始

### 方法1: 运行测试脚本
```bash
python test_install.py
```

### 方法2: 运行示例代码
```bash
python examples/example_basic.py
```

### 方法3: 使用 Jupyter Notebook
```bash
# 启动 Jupyter Notebook
jupyter notebook

# 然后在浏览器中打开 notebooks/01_quick_start.ipynb
```

### 方法4: 在 Python 脚本中使用
```python
from src.data_fetch.stock_data import StockDataFetcher
from src.analysis.technical import TechnicalAnalyzer

# 获取数据
fetcher = StockDataFetcher()
df = fetcher.get_stock_hist("000001", start_date="20240101", end_date="20241122")

# 计算技术指标
analyzer = TechnicalAnalyzer()
df = analyzer.calculate_all_indicators(df)

print(df.tail())
```

## 📦 核心功能模块

### 1. 数据获取 (`src/data_fetch/`)
- `get_stock_list()` - 获取A股股票列表
- `get_stock_hist()` - 获取个股历史数据
- `get_stock_realtime()` - 获取实时行情
- `get_stock_info()` - 获取股票基本信息
- `get_financial_report()` - 获取财务报表

### 2. 技术分析 (`src/analysis/`)
- `calculate_ma()` - 移动平均线 (MA)
- `calculate_ema()` - 指数移动平均线 (EMA)
- `calculate_macd()` - MACD指标
- `calculate_rsi()` - RSI指标
- `calculate_kdj()` - KDJ指标
- `calculate_boll()` - 布林带指标
- `calculate_all_indicators()` - 计算所有指标

### 3. 数据可视化 (`src/visualization/`)
- `plot_candlestick()` - K线图
- `plot_line()` - 折线图
- `plot_macd()` - MACD指标图
- `plot_kdj()` - KDJ指标图
- `plot_stock_analysis()` - 综合分析图

### 4. 工具函数 (`src/utils/`)
- `save_to_csv()` - 保存数据到CSV
- `load_from_csv()` - 从CSV加载数据
- `format_date()` - 日期格式化
- `calculate_return()` - 计算收益率
- `calculate_volatility()` - 计算波动率

## 📝 待安装的可选依赖

如果需要使用可视化和Jupyter功能,请运行:
```bash
pip install matplotlib seaborn plotly jupyter notebook pyyaml
```

或直接安装所有依赖:
```bash
pip install -r requirements.txt
```

## 💡 使用技巧

1. **获取股票代码**: A股代码为6位数字,如 "000001"(平安银行), "600519"(贵州茅台)

2. **日期格式**: 使用 YYYYMMDD 格式,如 "20241122"

3. **复权设置**:
   - `qfq` - 前复权(推荐)
   - `hfq` - 后复权
   - `""` - 不复权

4. **数据保存**: 所有获取的数据可以保存到 `data/` 目录

5. **图表输出**: 生成的图表可以保存到 `output/` 目录

## 🔗 相关资源

- [AkShare 官方文档](https://akshare.akfamily.xyz/)
- [AkShare GitHub](https://github.com/akfamily/akshare)
- [AkShare 数据字典](https://akshare.akfamily.xyz/data/index.html)

## ⚠️ 注意事项

1. AkShare 的数据来自公开数据源,仅供学习研究使用
2. 数据更新频率取决于数据源,实时数据可能有延迟
3. 请遵守数据使用规范,不要过度频繁请求数据
4. 投资有风险,工具仅供参考,不构成投资建议

## 🎯 下一步

1. ✅ 运行 `test_install.py` 验证安装
2. 📓 打开 `notebooks/01_quick_start.ipynb` 学习基础使用
3. 💻 查看 `examples/example_basic.py` 了解完整示例
4. 🔧 根据需要修改 `config/config.yaml` 配置
5. 🚀 开始你的量化投资之旅!

祝使用愉快! 🎊
