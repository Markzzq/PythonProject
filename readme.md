# 项目文件结构与功能说明

---

## 1. 开源库管理

项目依赖的第三方开源库封装文件：

| 文件 | 功能说明 |
|------|----------|
| `Ashare.py` | 股票/ETF行情数据获取接口（优先用于ETF查询） |
| `bstock.py` | baostock开源库封装（需登录/退出，优先用于股票查询） |
| `MyTT.py` | MyTT技术指标计算工具库 |
| `PBroker.py` | pybroker策略回测框架封装 |

**外部依赖库**（需单独安装）：
- `akshare` - 核心数据接口
- `baostock` - 股票行情数据
- `pybroker` - 策略回测
- `plotly` / `matplotlib` - 可视化
- `pymysql` / `mysql-connector` - 数据库连接
- `sqlalchemy` - ORM数据库操作

---

## 2. 数据更新模块

负责定期更新基础数据列表和行情数据的模块，分为两大类别：

### 2.1 CSV文件更新（utils.py）

从各大财经网站抓取基础列表数据并保存为CSV文件，这是项目的核心数据更新入口：

| 函数 | 功能说明 | 输出文件 |
|------|----------|----------|
| `fetch_etf_sina()` | 抓取沪深场内ETF列表（新浪） | `etf_A_list.csv` |
| `fetch_etf_em()` | 抓取沪深ETF列表（东方财富） | `etf_em_list.csv` |
| `fetch_open_fund()` | 抓取开放式基金列表 | `etf_open_list.csv` |
| `fetch_stock_a()` | 抓取A股股票列表（同花顺） | `stock_A_list.csv` |
| `fetch_concept_ths()` | 抓取同花顺概念板块名单 | `concept_ths_list.csv` |
| `fetch_concept_em()` | 抓取东方财富概念板块名单 | `concept_em_list.csv` |
| `updateData()` | 多线程并行更新所有数据列表 | 上述所有CSV文件 |

### 2.2 数据库入库更新

将CSV列表中的行情数据更新到MySQL数据库，包含以下文件：

#### 主数据库模块

| 文件 | 功能说明 |
|------|----------|
| `updateDatabase.py` | 主数据库更新模块，包含 `update_etf_daily_data()` 和 `update_stock_daily_data()` 函数 |

#### 数据库更新目录

```
database_update/
├── database_config.py    # 数据库连接配置
├── stock_basic_update.py # 股票基本信息更新
├── stock_daily_process.py # 股票日线数据处理
└── stock_daily_update.py  # 股票日线数据入库更新
```

#### 独立入库脚本

| 文件 | 功能说明 |
|------|----------|
| `stock_to_mysql.py` | 股票数据单独入库脚本 |
| `etf_to_mysql.py` | ETF数据单独入库脚本 |

#### 运行入口

| 文件 | 功能说明 |
|------|----------|
| `run.py` | 多线程执行脚本，同时运行 `findETF.py`、`findTrend.py`、`main.py` |

---

## 3. 数据分析

数据分析模块分为三大类，按照文件命名规范区分：

| 前缀 | 类别 | 说明 |
|------|------|------|
| `find` | 今日股票ETF分析 | 直接连接开源库（akshare/Ashare/baostock）获取数据进行分析 |
| `analyze` | 数据库内数据分析 | 对接数据库已有数据进行分析 |
| `realtime` | 实时分析 | 实时监控和定时执行任务 |

### 3.1 数据库内数据分析（analyze 开头）

基于MySQL数据库中的历史行情数据进行分析，包含数据源配置、数据库入库和数据分析功能。

#### 数据源与文件读取

| 文件 | 数据内容 | 更新来源 |
|------|----------|----------|
| `etf_A_list.csv` | 场内ETF基金列表 | `utils.fetch_etf_sina()` |
| `etf_open_list.csv` | 开放式基金列表 | `utils.fetch_open_fund()` |
| `etf_core_list.csv` | 场内行业ETF核心列表 | 人工筛选或自动生成 |
| `stock_A_list.csv` | A股股票列表 | `utils.fetch_stock_a()` |
| `core_stock_list.csv` | A股核心股票列表 | 人工筛选或自动生成 |
| `concept_ths_list.csv` | 概念板块名单（同花顺） | `utils.fetch_concept_ths()` |
| `concept_em_list.csv` | 概念板块名单（东方财富） | `utils.fetch_concept_em()` |

#### 在线数据接口

| 接口来源 | 适用场景 | 调用方式 |
|----------|----------|----------|
| akshare (新浪) | ETF历史行情 | `ak.fund_etf_hist_sina()` |
| akshare (同花顺) | A股实时行情 | `ak.stock_zh_a_spot()` |
| Ashare | 股票/ETF行情 | `get_price()` |
| baostock | 股票历史行情（需登录） | `bs.query_history_k_data_plus()` |

#### 数据库配置与入库

项目包含两套独立的数据库系统：

**主数据库系统（updateDatabase.py）**

配置信息：
- ETF数据库：`localhost:3306/etf_daily`
- 股票数据库：`localhost:3306/stock_daily`

| 函数 | 功能说明 |
|------|----------|
| `update_etf_daily_data()` | 更新ETF日线数据到MySQL |
| `update_stock_daily_data()` | 更新股票日线数据到MySQL |
| `_get_etf_data()` | 获取ETF数据（akshare/Ashare双源） |
| `_get_stock_data()` | 获取股票数据（baostock） |
| `_import_data()` | 通用数据导入（支持增量更新） |
| `_create_table_if_not_exists()` | 自动建表 |

**备用数据库系统（database_update/）**

使用 SQLAlchemy 操作，包含独立的配置文件和更新逻辑：

```
database_update/
├── database_config.py    # 数据库连接配置
├── stock_daily_process.py # 股票日线数据处理
└── stock_daily_update.py  # 股票日线数据入库更新
```

#### 数据库分析程序

| 文件 | 功能说明 | 输出结果 |
|------|----------|----------|
| `analyzeCoreETF_DayScore.py` | 从数据库读取ETF数据进行指标分析和评分 | ETF综合评分结果 |
| `analyzeCoreStock.py` | 核心板块股票深度分析（基于数据库数据） | 核心股票分析结果 |

### 3.2 今日股票ETF分析（find 开头）

直接连接开源库获取数据进行分析：

#### ETF分析

| 文件 | 功能说明 | 输出结果 |
|------|----------|----------|
| `findETF.py` | ETF每日分析，基金走势展示/条件筛选 | 所有策略的ETF列表 |
| `findTrend.py` | ETF趋势筛选（7日最佳、30日最佳、反转信号、创新高） | 趋势良好的ETF列表 |

#### 股票分析

| 文件 | 功能说明 | 输出结果 |
|------|----------|----------|
| `findStock.py` | 股票每日分析，走势展示/条件筛选 | 所有策略的股票列表 |
| `findBottomStock.py` | 筑底股策略验证，寻找0线以下筑底股票 | `bottom_Stock` |
| `findGoodStock.py` | 均线多头策略验证，寻找均线多头股票 | `good_Stock` |

#### 板块与概念分析

| 文件 | 功能说明 |
|------|----------|
| `findBankuai.py` | 板块热度分析，行业强度趋势分析 |
| `findMoneyflow.py` | 资金流向分析，概念板块指数历史数据 |
| `conceptreview.py` | 概念板块周评分析 |
| `conceptdayreview.py` | 概念板块日评分析 |

#### 股票财务分析

| 文件 | 功能说明 | 输出结果 |
|------|----------|----------|
| `findStockFinancial.py` | 股票财务报表分析，筛选财务表现良好的公司 | 财务分析结果 |

#### 综合分析入口

| 文件 | 功能说明 |
|------|----------|
| `main.py` | 综合分析入口，整合多个分析模块 |

### 3.3 实时分析（realtime 开头）

实时监控和定时执行任务：

| 文件 | 功能说明 |
|------|----------|
| `realtimeCoreETF.py` | ETF实时监控，基于均线偏差的预警系统 |
| `quicksearch.py` | 快速搜索工具，定时实时执行任务 |

---

## 4. 通用工具集（utils.py）

### 4.1 技术指标计算

| 函数 | 功能说明 |
|------|----------|
| `cal_KDJ()` | 计算KDJ指标 |
| `cal_OBV()` | 计算OBV能量潮 |
| `cal_VR()` | 计算成交量变异率 |
| `cal_EMV()` | 计算能量潮指标 |
| `cal_VOLATILITY()` | 计算简易波动率 |
| `cal_CYC()` | 计算成本均线（筹码分布） |
| `cal_ADR()` | 计算涨跌比率 |

### 4.2 可视化工具

| 函数 | 功能说明 |
|------|----------|
| `showAllStock(filename)` | 读取股票列表并全部绘图展示 |
| `showOneETF(code)` | 抓取单只ETF趋势图（新浪模式） |
| `showAllETF(filename)` | 读取ETF列表并全部绘图展示 |

> **注意**：utils.py 中的数据更新函数（`updateData()`、`fetch_*()`）详见第2章「数据更新模块」。

---

## 项目运行流程

```
1. 数据准备阶段
   ├── utils.updateData() 更新基础列表数据
   └── updateDatabase.update_*_daily_data() 更新行情数据库

2. 分析执行阶段
   ├── run.py 启动多线程分析
   │   ├── findETF.py → ETF分析
   │   ├── findTrend.py → ETF趋势筛选
   │   └── main.py → 综合分析
   ├── findStock.py → 股票分析
   └── findBankuai.py → 板块分析

3. 结果输出阶段
   ├── CSV文件输出（筛选后的股票/ETF列表）
   └── 可视化图表展示
```

---

## 关键配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| ETF_START_DATE | 2025-01-01 | ETF数据起始日期 |
| STOCK_START_DATE | 2026-01-01 | 股票数据起始日期 |
| ETF_LIST_FILE | etf_core_list.csv | ETF列表文件 |
| STOCK_LIST_FILE | stock_A_list.csv | 股票列表文件 |

---

## 其他文件

| 文件 | 说明 |
|------|------|
| `test.py` | 临时测试文件，用于验证新功能或调试，不属于正式模块 |

---

## 一般工作流

| 工作流 | 执行时机 | 说明 |
|--------|----------|------|
| `analyze` | 盘后执行 | 先更新数据库（`updateDatabase.update_*_daily_data()`），再执行分析 |
| `find` | 每天执行 | 直接连接开源库获取最新数据进行分析，无需依赖数据库 |
| `realtime` | 开盘时执行 | 实时监控行情数据，基于均线偏差等指标触发预警 |