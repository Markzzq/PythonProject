import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time
import schedule

# 股市行情数据获取和作图 -2
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT

import baostock as bs

START_DATE = '2025-03-13'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')
Cd = 1.0


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



if __name__ == '__main__':

    df_concept_list = pd.read_csv('concept_ths_list.csv')
    df_concept = df_concept_list[['name', 'code']]

    anyData = {'概念': '概念','OPEN': '开盘价', 'CLOSE': '收盘价'}
    dfResult = pd.DataFrame(anyData, index=[0])

    for row_index, row in df_concept_list.iterrows():
        try:
            time.sleep(1)
            # 方法三
            row_code = row['code']
            row_name = row['name']

            # 日线数据
            """
            用同花顺的概念列表 搜索出的历史数据 日线
            """

            # 同花顺的概念板块接口
            stock_board_concept_index_ths_df = ak.stock_board_concept_index_ths(symbol=row_name,
                                                                                start_date=START_DATE,
                                                                                end_date=END_DATE)
            #print(stock_board_concept_index_ths_df)


            N = stock_board_concept_index_ths_df.shape[0]

            # 计算初级数据  均线策略因子
            CLOSE = stock_board_concept_index_ths_df['收盘价']
            MA5 = MA(CLOSE, 5)  # 获取5日均线序列
            MA10 = MA(CLOSE, 10)  # 获取5日均线序列
            MA20 = MA(CLOSE, 20)  # 获取20日均线序列
            MA30 = MA(CLOSE, 30)  # 获取30日均线序列
            MA60 = MA(CLOSE, 60)  # 获取60日均线序列

            # 获取macd指标
            dif, dea, macd = MACD(CLOSE)

            ma5 = MA5[N - 1]
            ma10 = MA10[N - 1]
            ma20 = MA20[N - 1]
            ma30 = MA30[N - 1]
            ma60 = MA60[N - 1]
            macd20 = macd[N - 1]


            var1 = False
            var2 = False
            var3 = False
            var4 = False
            var5 = False
            var6 = False
            var7 = False
            var8 = False

            # if ma5 > Cd*ma10 and ma10 > Cd*ma20:
            if ma5 > Cd * ma10 and ma10 > Cd * ma20 and ma20 > Cd * ma30 and ma30 > ma60:
            # and ma30 > Cd * ma60:
                var1 = True

            # macd 趋势向上
            if macd20 > 0 and macd[N - 1] >= macd[N - 2] and macd[N - 2] >= macd[N - 3] and macd[N - 3] >= macd[N - 4]:
                var2 = True

            # dif 趋势向上
            if dif[N - 1] > 0 and dif[N - 1] > dif[N - 2] and dif[N - 2] > dif[N - 3] and dif[N - 3] > dif[N - 4]:
                var3 = True

            if dif[N - 1] > 0 and dea[N - 1] > 0:
                var4 = True

            # dea 趋势向上
            if dea[N - 1] > 0 and dea[N - 1] > dea[N - 2] and dea[N - 2] > dea[N - 3] and dea[N - 3] > dea[N - 4]:
                var5 = True


            varAll = var1 and var2 and var3 and var5


            if varAll:
                anyData = {'概念': row_name,'OPEN': stock_board_concept_index_ths_df['开盘价'][N-1], 'CLOSE': stock_board_concept_index_ths_df['收盘价'][N-1]}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
                print('success add one', row_name)


        except:
            continue

    print(dfResult)
    #### 结果集输出到csv文件 ####
    file_name = f"{END_DATE}_concept_ths.csv"
    #dfResult.to_csv(file_name, encoding="gbk", index=False)
    dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)

