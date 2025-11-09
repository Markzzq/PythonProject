import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time

# 股市行情数据获取和作图 -2
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT
import akshare as ak

import baostock as bs

# plotly express   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio


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


def showAllStock(filename):
    # 读取ETF列表
    df_list = pd.read_csv(filename)
    df_stock = df_list[['stock', 'name']]

    START_DATE = '20250313'
    END_DATE = datetime.datetime.now().strftime('%Y%m%d')


    for row_index, row in df_stock.iterrows():
        try:
            stock_code = row['stock'][2:] # 是因为抓到的数据带了字母 只取数字
            stock_name = row['name']

            hkmi = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=START_DATE, end_date=END_DATE, adjust="")
            fig = px.line(hkmi, x="日期", y="收盘", title=stock_name, subtitle=stock_code)
            fig.add_trace(go.Scatter(x=[hkmi['日期'].iloc[-1]],
                                     y=[hkmi['收盘'].iloc[-1]],
                                     text=[hkmi['日期'].iloc[-1]],
                                     mode='markers+text',
                                     marker=dict(color='red', size=10),
                                     textfont=dict(color='green', size=10),
                                     textposition='top left',
                                     showlegend=False))
            fig.show()
        except:
            continue



def updateData():
    # 抓取沪深基金并保存在表格中
    etf = ak.fund_etf_category_sina(symbol="ETF基金")
    etf.to_csv("sina_etf_list.csv", encoding='utf-8-sig')

    # A 股上市公司的实时行情数据，抓取股票列表
    # 新浪财经-所有 A 股的实时行情数据;
    stock_zh_a_spot_df = ak.stock_zh_a_spot()
    stock_zh_a_spot_df.to_csv("stock_zh_list.csv", encoding='utf-8-sig')

    # 同花顺-所有 A 股的板块概念名单 题材概念
    concept_zh_a_spot_df = ak.stock_board_concept_name_ths()
    concept_zh_a_spot_df.to_csv("concept_ths_list.csv", encoding='utf-8-sig')

    # 东方财富-所有 A 股的板块概念名单 题材概念
    concept_em_df = ak.stock_board_concept_name_em()
    concept_em_df.to_csv("concept_em_list.csv", encoding='utf-8-sig')
