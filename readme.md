# 常用文件库及功能说明

## 运行脚本
- **每日分析**  
  `run.py`多线程脚本运行每日分析

## 开源库
- **Ashare**  
  `Ashare.py`开源库调用接口  查etf比较好 因为股票日内会限制次数
- **baostock**  
  `bstock.py`开源库调用（需登录/退出操作）  查股票比较好
- **myTT**  
  `MyTT.py`技术指标计算工具（基于MyTT）

## 回测模块
- **pybroker回测模块**  
  `PBroker.py`策略回测框架（PBroker）

## 基础功能
- **趋势股筛选**  
  `dailyReview.py` → 输出结果: `stock` 
- **板块热度分析**  
  `bankuaifenxi.py` → 行业强度趋势分析



- **单个股票反弹策略验证**  
  `findBottomStock.py` → 输出结果: `bottom_Stock`（寻找0线以下筑底股）
- **单个股票均线多头策略验证**  
  `findGoodStock.py` → 输出结果: `good_Stock`（寻找均线多头股票）
- **核心股票分析**  
  `coreAnalysis.py` → 核心股票分析

- **ETF每日分析**  
  `findETF.py` → 基金走势展示/条件筛选 → 输出结果: `所有策略的etf按照列表输出`
- **股票每日分析**  
  `findStock.py` → 股票走势展示/条件筛选 → 输出结果: `所有策略的股票按照列表输出`
- 
## 集成功能utils


- **特殊指标计算**  
  `calKDJ()` → 计算kdj
- **特殊指标计算**  
  `calOBV()` → 计算obv
- **特殊指标计算**  
  `cal_VR()` → 计算成交量变异率
- **特殊指标计算**  
  `cal_EMV()` → 计算能量潮指标
- **特殊指标计算**  
  `cal_VOLATILITY()` → 计算简易波动率
- **特殊指标计算**  
  `cal_CYC()` → 计算筹码分布相关
- **特殊指标计算**  
  `cal_ADR()` → 计算涨跌比率

- **显示**  
  `utils.showAllStock('2026-03-08_Stock_Core.csv')` → 显示筛选后文件内股票
- **显示**  
  `utils.showOneETF("sz159994")` → 抓取某一只etf的图像
- **显示**  
  `utils.showAllETF('2025-10-22_topETF.csv')` → 抓取某一组etf的图像

- **数据更新**  
  `updataData()` → 数据集更新

## 数据集
- **etf_sina_list**  
  基金列表数据
- **stock_A_list**  
  A股股票列表数据