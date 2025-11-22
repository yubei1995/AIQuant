# AIQuant - 基于 AkShare 的金融分析工具

## 项目简介
基于 AkShare 的金融数据分析工具,提供股票、基金、期货等金融数据的获取、分析和可视化功能。

## 环境要求
- Python 3.8+ (64位)
- 已安装 AkShare 1.17+

## 安装依赖
```bash
pip install -r requirements.txt
```

## 项目结构
```
AIQuant/
├── data/              # 数据存储目录
├── notebooks/         # Jupyter 分析笔记本
├── src/              # 源代码
│   ├── data_fetch/   # 数据获取模块
│   ├── analysis/     # 数据分析模块
│   ├── visualization/ # 数据可视化模块
│   └── utils/        # 工具函数
├── tests/            # 测试文件
├── config/           # 配置文件
└── output/           # 输出结果
```

## 快速开始

### 1. 获取股票数据
```python
import akshare as ak
from src.data_fetch.stock_data import get_stock_hist

# 获取平安银行历史数据
df = get_stock_hist('000001', start_date='20240101', end_date='20241122')
print(df.head())
```

### 2. 数据分析
```python
from src.analysis.technical import calculate_ma

# 计算移动平均线
df_with_ma = calculate_ma(df, periods=[5, 10, 20])
```

### 3. 数据可视化
```python
from src.visualization.charts import plot_candlestick

# 绘制K线图
plot_candlestick(df, title='平安银行日K线')
```

## 功能模块

### 数据获取
- ✅ A股实时行情
- ✅ 个股历史数据
- ✅ 财务报表数据
- ✅ 基金数据
- ✅ 期货数据
- ✅ 宏观经济数据

### 数据分析
- 📊 技术指标计算(MA, MACD, RSI, KDJ等)
- 📈 趋势分析
- 💹 量价分析
- 📉 风险评估

### 数据可视化
- 📊 K线图
- 📈 趋势图
- 💹 成交量分析图
- 🎯 技术指标图

## 使用示例
查看 `notebooks/` 目录下的示例笔记本

## 贡献
欢迎提交 Issue 和 Pull Request

## 许可
MIT License

## 相关资源
- [AkShare 官方文档](https://akshare.akfamily.xyz/)
- [AkShare GitHub](https://github.com/akfamily/akshare)
