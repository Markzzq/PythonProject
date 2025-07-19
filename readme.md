# 常用文件库及功能说明

## 运行脚本
- **每日分析**  
  `run.py`多线程脚本运行每日分析

## 开源库
- **Ashare**  
  `Ashare.py`开源库调用接口
- **baostock**  
  `bstock.py`开源库调用（需登录/退出操作）
- **myTT**  
  `MyTT.py`技术指标计算工具（基于MyTT）

## 回测模块
- **pybroker回测模块**  
  `PBroker.py`策略回测框架（PBroker）

## 基础功能
- **趋势股筛选**  
  `dailyreview.py` → 输出结果: `k_data`
- **反弹筑底股票筛选**  
  `findbottom.py` → 输出结果: `bottom_data`（寻找0线以下筑底股）
- **数据更新**  
  `updataData.py` → 数据集更新
- **板块热度分析**  
  `bankuaifenxi.py` → 行业强度趋势分析
- **ETF分析**  
  `etf.py` → 基金走势展示/条件筛选 → 输出结果: `findGoodETF`(优质etf)

## 数据集
- **sina_etf_list**  
  基金列表数据
- **stock_zh_list**  
  A股股票列表数据