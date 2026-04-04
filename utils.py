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

# 多线程
import threading
import os


def cal_KDJ(df):
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


def cal_OBV(df):
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

# 1. 成交量变异率（VR）—— 量能趋势指标，判断量能与价格的匹配度
# 公式：VR = (上涨日成交量总和) / (下跌日成交量总和) * 100
def cal_VR(close, volume, N=24):
    """计算VR指标（默认24日周期）"""
    df = pd.DataFrame({'close': close, 'volume': volume})
    df['prev_close'] = df['close'].shift(1)
    df['up_vol'] = np.where(df['close'] > df['prev_close'], df['volume'], 0)
    df['down_vol'] = np.where(df['close'] < df['prev_close'], df['volume'], 0)
    df['vr'] = df['up_vol'].rolling(N).sum() / (df['down_vol'].rolling(N).sum() + 0.0001) * 100  # 避免除0
    return df['vr'].values


# 7. 能量潮指标（EMV）—— 衡量成交量与价格波动的关系，判断趋势
def cal_EMV(high, low, volume, N=14):
    """计算EMV指标（简易版，14日周期）"""
    # 步骤1：计算中间价振幅
    mid_amp = (high + low) / 2 - (high.shift(1) + low.shift(1)) / 2
    # 步骤2：计算成交量比率
    vol_ratio = volume / (high - low)
    # 步骤3：EMV核心值
    emv = mid_amp / vol_ratio
    # 步骤4：EMV均线（平滑）
    emv_ma = emv.rolling(N).mean()
    return emv.values, emv_ma.values

# 8. 简易波动率（VOLATILITY）—— 收盘价的年化波动率
def cal_VOLATILITY(close, N=20):
    """计算20日年化波动率（对数收益率的标准差）"""
    log_return = np.log(close / close.shift(1))  # 对数收益率
    volatility = log_return.rolling(N).std() * np.sqrt(252) * 100  # 年化
    return volatility.values

# 9. 筹码分布相关（成本均线CYC）—— 简化版，按成交量加权的均线
def cal_CYC(close, volume, N=20):
    """计算20日成本均线（CYC），成交量加权平均价"""
    vol_sum = volume.rolling(N).sum()
    cyc = (close * volume).rolling(N).sum() / (vol_sum + 0.0001)  # 避免除0
    return cyc.values

# 10. 涨跌比率（ADR）—— 市场整体强弱指标（单只股票简化版）
def cal_ADR(close, N=10):
    """单只股票ADR简化版:上涨天数/下跌天数"""
    df = pd.DataFrame({'close': close})
    df['change'] = df['close'] - df['close'].shift(1)
    df['up_day'] = np.where(df['change'] > 0, 1, 0)
    df['down_day'] = np.where(df['change'] < 0, 1, 0)
    adr = df['up_day'].rolling(N).sum() / (df['down_day'].rolling(N).sum() + 0.0001)
    return adr.values




# 读取股票列表 并在网页中全部显示出来
def showAllStock(filename):
    # 读取股票列表
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


## 抓取某一只ETF基金的趋势图  新浪模式
def showOneETF(code):
    hkmi = ak.fund_etf_hist_sina(symbol=code)
    # fig = px.line(hkmi, x="date", y="close", title=name, subtitle=code)
    fig = px.line(hkmi, x="date", y="close", title=code)
    fig.add_trace(go.Scatter(x=[hkmi['date'].iloc[-1]],
                             y=[hkmi['close'].iloc[-1]],
                             text=[hkmi['date'].iloc[-1]],
                             mode='markers+text',
                             marker=dict(color='red', size=10),
                             textfont=dict(color='green', size=10),
                             textposition='top left',
                             showlegend=False))
    fig.show()
    pio.write_image(fig, "fig.png")

    return None


# 读取备选列表里的基金并展示出来
def showAllETF(filename):
    # 读取ETF列表
    df_etf_list = pd.read_csv(filename)
    df_etf = df_etf_list[['代码', '名称']]

    for row_index, row in df_etf.iterrows():
        try:
            etf_code = row['代码']  # 是因为抓到的数据带了字母 只取数字
            etf_name = row['名称']
            hkmi = ak.fund_etf_hist_sina(symbol=etf_code)
            fig = px.line(hkmi, x="date", y="close", title=etf_name, subtitle=etf_code)
            fig.add_trace(go.Scatter(x=[hkmi['date'].iloc[-1]],
                                     y=[hkmi['close'].iloc[-1]],
                                     text=[hkmi['date'].iloc[-1]],
                                     mode='markers+text',
                                     marker=dict(color='red', size=10),
                                     textfont=dict(color='green', size=10),
                                     textposition='top left',
                                     showlegend=False))
            fig.show()
        except:
            continue

    return None






def fetch_etf_sina():
    """抓取沪深基金etf并保存在表格中  新浪"""
    etf = ak.fund_etf_category_sina(symbol="ETF基金")
    etf.to_csv("etf_sina_list.csv", encoding='utf-8-sig')

def fetch_etf_em():
    """抓取沪深基金etf并保存在表格中  东财"""
    # 东材接口好像暂时连不上了
    etf = ak.fund_etf_spot_em()
    etf.to_csv("etf_em_list.csv", encoding='utf-8-sig')

def fetch_open_fund():
    """抓取所有开放式基金数据 并保存在表格中  东财"""
    fund_open_fund_rank_em_df = ak.fund_open_fund_rank_em(symbol="全部")
    fund_open_fund_rank_em_df.to_csv("etf_open_list.csv", encoding='utf-8-sig')

def fetch_stock_a():
    """A 股上市公司的实时行情数据，抓取股票列表  同花顺"""
    stock_zh_a_spot_df = ak.stock_zh_a_spot()
    stock_zh_a_spot_df.to_csv("stock_A_list.csv", encoding='utf-8-sig')

def fetch_concept_ths():
    """同花顺-所有 A 股的板块概念名单 题材概念  同花顺"""
    concept_zh_a_spot_df = ak.stock_board_concept_name_ths()
    concept_zh_a_spot_df.to_csv("concept_ths_list.csv", encoding='utf-8-sig')

def fetch_concept_em():
    """东方财富-所有 A 股的板块概念名单 题材概念"""
    # 东材接口好像暂时连不上了
    concept_em_df = ak.stock_board_concept_name_em()
    concept_em_df.to_csv("concept_em_list.csv", encoding='utf-8-sig')

def updateData():
    # 创建线程
    threads = [
        threading.Thread(target=fetch_etf_sina),
        threading.Thread(target=fetch_open_fund),
        threading.Thread(target=fetch_stock_a),
        threading.Thread(target=fetch_concept_ths),
    ]
    
    # 启动所有线程
    for thread in threads:
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()


