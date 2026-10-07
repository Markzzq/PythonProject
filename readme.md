# 项目文件结构与功能说明

---

## 1. 开源库管理

项目依赖的第三方开源库封装文件：

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `Ashare.py` | 股票/ETF行情数据获取接口（优先用于ETF查询） | `get_price()`（统一入口）、`get_price_day_tx()`（腾讯日线）、`get_price_min_tx()`（腾讯分钟线）、`get_price_sina()`（新浪全周期） |
| `bstock.py` | baostock开源库封装（需登录/退出，优先用于股票查询） | `get(code, start_date, end_date)` |
| `MyTT.py` | MyTT技术指标计算工具库 | `MA()`、`EMA()`、`MACD()`、`KDJ()` 等技术指标函数 |
| `PBroker.py` | pybroker策略回测框架封装 | `ETFBacktester` 等回测框架函数 |

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

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `updateDatabase.py` | 主数据库更新模块，更新ETF/股票日线数据到MySQL | `update_etf_daily_data()`、`update_stock_daily_data()`（入口）、`_get_etf_data()`（akshare/Ashare双源）、`_get_stock_data()`（baostock）、`_ensure_tables()`（自动建表）、`_import_one()`（增量导入） |

#### 数据库更新目录

```
database_update/
├── database_config.py    # 数据库连接配置：get_db_engine() / fetch_data_from_api()
├── stock_basic_update.py # 股票基本信息更新：process_json_to_dataframe() / save_stock_basic_to_db()
├── stock_daily_process.py # 股票日线数据处理：fetch_stock_ohlc() / compute_and_process() / process_daily_stocks()
└── stock_daily_update.py  # 股票日线数据入库更新：fetch_and_iterate_stock_codes() / fetch_data_from_baostock() / insert_data_to_db()
```

#### 独立入库脚本

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `stock_to_mysql.py` | 股票数据单独入库脚本 | `load_stock_list()`、`get_stock_data()`、`import_stock_data()`、`create_table_if_not_exists()`、`get_last_date()` |
| `etf_to_mysql.py` | ETF数据单独入库脚本 | `load_etf_list()`、`get_etf_data()`、`import_etf_data()`、`create_table_if_not_exists()`、`get_last_date()` |

#### 运行入口

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `run.py` | 多线程执行脚本，同时运行 `findETF.py`、`findTrend.py`、`main.py` | `run_script(script_name)` |

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
| `_import_one()` | 通用数据导入（支持增量更新） |
| `_ensure_tables()` | 自动建表 |
| `_load_list()` | 读取CSV列表文件 |

**备用数据库系统（database_update/）**

使用 SQLAlchemy 操作，包含独立的配置文件和更新逻辑：

```
database_update/
├── database_config.py    # 数据库连接配置：get_db_engine() / fetch_data_from_api()
├── stock_daily_process.py # 股票日线数据处理：fetch_stock_ohlc() / compute_and_process() / process_daily_stocks()
└── stock_daily_update.py  # 股票日线数据入库更新：fetch_and_iterate_stock_codes() / fetch_data_from_baostock() / insert_data_to_db()
```

#### 数据库分析程序

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `analyzeCoreETF_DayScore.py` | 从数据库读取ETF数据进行指标分析和评分 | `analyze_all_etfs()`（入口）、`analyze_etf()`、`calculate_indicators()`、`get_etf_specific_indicators()`、`score_etf_specific()` |
| `analyzeCoreStock.py` | 核心板块股票深度分析（基于数据库数据） | `coreSearch(filename)` |

### 3.2 今日股票ETF分析（find 开头）

直接连接开源库获取数据进行分析：

#### ETF分析

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `findETF.py` | ETF每日分析，基金走势展示/条件筛选 | `findGoodETF(filename)`（所有策略的ETF列表） |
| `findTrend.py` | ETF趋势筛选（7日最佳、30日最佳、反转信号、创新高） | `findGoodTrend(filename)`（入口）、`get_etf_data()`、`calculate_all_indicators()`、`calculate_score()`、`get_signal()` |

#### 股票分析

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `findStock.py` | 股票每日分析，走势展示/条件筛选 | `stockSearch(filename)`（所有策略的股票列表） |
| `findBottomStock.py` | 筑底股策略验证，寻找0线以下筑底股票 | `findBottom()`（输出 `bottom_Stock`） |
| `findGoodStock.py` | 均线多头策略验证，寻找均线多头股票 | `findGoodTrend()`（输出 `good_Stock`） |

#### 板块与概念分析

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `findBankuai.py` | 板块热度分析，行业强度趋势分析 | `analyze_concept(filename)`、`main()` |
| `findMoneyflow.py` | 资金流向分析，概念板块指数历史数据 | `getConceptIndexHistory()`、`getConceptFundFlowHistory()` |
| `conceptreview.py` | 概念板块周评分析 | `calKDJ(df)` |
| `conceptdayreview.py` | 概念板块日评分析 | `calKDJ(df)` |

#### 股票财务分析

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `findStockFinancial.py` | 股票财务报表分析，筛选财务表现良好的公司 | `get_stock_financial_report(filename)`（入口）、`extract_financial_metrics()`、`is_financial_healthy()`、`calculate_growth_rates()`、`calculate_single_quarter_value()` |

#### 股票估值分析

直接调用 akshare 东财接口获取财报与行情数据进行分析，不依赖数据库。包含两套独立估值模型：
- PE(TTM) 百分位模型（`findPE_TTM.py`）：市盈率相对历史水平的高低判断
- 巴菲特 DCF 自由现金流模型（`findFCF.py`）：以所有者盈余/自由现金流为核心的正现金流筛选

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `findPE_TTM.py` | 基于PE的估值模型：A股动态市盈率TTM按日计算与历史百分位筛选，多线程并行，低于15%分位自动存图。输出 `pe_ttm_summary.xlsx` + `pe_ttm_low_percentile/`（低分位PE日线HTML图） | `calc_pe_ttm(code)`（按日计算PE_TTM）、`calc_pe_stats()`（历史高低+百分位）、`plot_pe_ttm()`（画图/存HTML）、`calc_and_plot_pe_ttm()`（单只一步到位）、`run_all_stocks()`（批量入口，多线程） |
| `findFCF.py` | 基于巴菲特DCF的估值模型：自由现金流连续5年为正的公司筛选，输出各年FCF与CAGR。FCF口径 = 经营现金流净额 − 资本支出 + 处置长期资产回收 − 并购净支出（单位万元）。输出 `stock_FCF_list.csv` | `_with_market(code)`（补市场前缀）、`calc_fcf_annual(code, n_years)`（年度FCF计算）、`check_fcf_positive()`（连续为正判断+CAGR）、`run_fcf_screen()`（批量入口，多线程） |

#### 综合分析入口

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `main.py` | 综合分析入口，整合多个分析模块 | 调用 `analyzeCoreStock.coreSearch()` |

### 3.3 实时分析（realtime 开头）

实时监控和定时执行任务：

| 文件 | 功能说明 | 核心函数 |
|------|----------|----------|
| `realtimeCoreETF.py` | ETF实时监控，基于均线偏差的预警系统 | `monitor_etf_deviation()`（监控主循环）、`get_realtime_prices()`、`get_etf_ma_values()`、`_check_deviation()` |
| `quicksearch.py` | 快速搜索工具，定时实时执行任务 | `task()`（定时任务入口） |

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