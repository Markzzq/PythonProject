import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time

# 股市行情数据获取和作图 -2
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT

import baostock as bs


def calKDJ(df):
    # 要把close 中的字符转数字格式 才能进行计算
    low_list = df['low'].rolling(9, min_periods=9).min()
    low_list.fillna(value=df['low'].expanding().min(), inplace=True)
    high_list = df['high'].rolling(9, min_periods=9).max()
    high_list.fillna(value = df['high'].expanding().max(), inplace=True)
    close = df['close'].astype(float)
    rsv = (close - low_list) / (high_list - low_list) *100

    df['k'] = pd.DataFrame(rsv).ewm(com=2).mean()
    df['d'] = df['k'].ewm(com=2).mean()
    df['j'] = 3 * df['k'] - 2 * df['d']

    return df['k'], df['d'], df['j']


def calOBV(df):
    # 假设 df 是股票数据，包含 'close'（收盘价）和 'volume'（成交量）
    # 计算 VA 列
    M = 30
    # 强制类型转换
    close = df['close'].astype(float)
    volume = df['volume'].astype(float)
    low = df['low'].astype(float)
    high = df['high'].astype(float)

    df['obv'] = (2 * close - low - high) / (high - low) * volume / 10000

    return df['obv']




