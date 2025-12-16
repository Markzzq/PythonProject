# 这是第一个python程序
# os：操作系统接口
# sys：系统特定参数和函数
# datetime：日期和时间处理
# json：JSON数据处理
# re：正则表达式

import math
import sys
import requests
import schedule
import datetime
import time

import akshare as ak
import numpy as np
import pandas as pd
import baostock as bs

import utils
# 股市行情数据获取和作图 -2
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT


# plotly   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go
from numba.core.typing.typeof import typeof_numpy_random_bitgen

# -------------------------作图显示-----------------------------------------------------------------
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator



START_DATE = '2025-03-13'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')
Cd = 1.0


# url = "http://api.mairui.club/hsrl/ssjy/000002/b997d4403688d5e66a"
# response = requests.get(url)
# data = response.json()
# print(data)
# """
# fm代表：五分钟涨跌幅（%），h代表：最高价（元），hs代表：换手（%），lb代表：量比（%），l代表：最低价（元），lt代表：流通市值（元），
# o代表：开盘价（元），pe代表：市盈率（动态，总市值除以预估全年净利润，例如当前公布一季度净利润1000万，则预估全年净利润4000万），
# pc代表：涨跌幅（%），p代表：当前价格（元），sz代表：总市值（元），cje代表：成交额（元），ud代表：涨跌额（元），v代表：成交量（手），
# yc代表：昨日收盘价（元），zf代表：振幅（%），zs代表：涨速（%），sjl代表：市净率，zdf60代表：60日涨跌幅（%），zdfnc代表：年初至今涨跌幅（%），t代表：更新时间YYYY-MM-DD HH:MM
# """

# 证券代码兼容多种格式 通达信，同花顺，聚宽
# sh000001 (000001.XSHG)    sz399006 (399006.XSHE)   sh600519 ( 600519.XSHG )

# df = get_price('000001.XSHG', frequency='1d', count=120)  # 默认获取今天往前120天的日线行情
# print('上证指数日线行情\n', df.tail(10))
#
# # -------有数据了，下面开始正题 -------------
# CLOSE = df.close.values  # 收盘序列
# OPEN = df.open.values  # 基础数据定义，只要传入的是序列都可以  Close=df.close.values
# HIGH = df.high.values
# LOW = df.low.values  # 例如  CLOSE=list(df.close) 都是一样
#
# MA5 = MA(CLOSE, 5)  # 获取5日均线序列
# MA10 = MA(CLOSE, 10)  # 获取10日均线序列
# up, mid, lower = BOLL(CLOSE)  # 获取布林带指标数据
# dif, dea, macd = MACD(CLOSE)  # 获取macd指标
#
#
#
# plt.figure(figsize=(15, 8))
# plt.plot(CLOSE, label='SHZS');
# plt.plot(up, label='UP');  # 画图显示
# plt.plot(mid, label='MID');
# plt.plot(lower, label='LOW');
# plt.plot(MA10, label='MA10', linewidth=0.5, alpha=0.7);
# plt.legend();
# plt.grid(linewidth=0.5, alpha=0.7);
# plt.gcf().autofmt_xdate(rotation=45);
# plt.gca().xaxis.set_major_locator(MultipleLocator(len(CLOSE) / 30))  # 日期最多显示30个
# plt.title('SH-INDEX   &   BOLL SHOW', fontsize=20);
# plt.show()

if __name__ == '__main__':
    # df = get_price('sh000001', frequency='1d', count=10)  # 支持'1d'日, '1w'周, '1M'月
    # print('上证指数日线行情\n', df)

    # df = get_price('000001.XSHG', frequency='15m', count=10)  # 支持'1m','5m','15m','30m','60m'
    # print('上证指数分钟线\n', df)



    # 更新股票 etf备选列表
    # utils.updateData()

    # 读取股票列表 并在网页中全部显示出来
    utils.showAllStock('2025-12-13_test.csv')

    # 抓取某一只etf的图像
    # utils.showOneETF("sz159695")

    # 抓取某一组etf的图像
    # utils.showAllETF('2025-10-22_topETF.csv')


