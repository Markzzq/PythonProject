import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time
import schedule

# 股市行情数据获取
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT
import baostock as bs

START_DATE = '2025-01-13'
# END_DATE = '2025-07-11'

END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')
C1 = 1.02
C2 = 1.01

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

# 均线多头策略
def findWeekTrend():
    start_time = time.time()

    # 读取股票列表
    df_stock_list = pd.read_csv('stock_zh_list.csv')
    df_stock = df_stock_list[['代码', '名称']][266:]

    dfResult = pd.DataFrame(data=None, columns=['stock', 'name', 'OPEN', 'CLOSE', 'pctChg', 'turn'])

    # 登陆baostock开源库
    lg = bs.login()

    for row_index, row in df_stock.iterrows():
        try:
            # 方法三
            row_code = row['代码'][:2] + "." +  row['代码'][2:]
            row_name = row['名称']

            # 周线数据
            """
            frequency：数据类型，默认为d，日k线；d=日k线、w=周、m=月、5=5分钟、15=15分钟、30=30分钟、60=60分钟k线数据，不区分大小写；指数没有分钟线数据；周线每周最后一个交易日才可以获取，月线每月最后一个交易日才可以获取。
            adjustflag：复权类型，默认不复权：3；1：后复权；2：前复权。已支持分钟线、日线、周线、月线前后复权。
            """
            rs = bs.query_history_k_data_plus(row_code,
                                              "date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg",
                                              start_date=START_DATE, end_date=END_DATE,
                                              frequency="w", adjustflag="2")

            #### 打印结果集 ####
            data_list = []
            while (rs.error_code == '0') & rs.next():
                # 获取一条记录，将记录合并在一起
                data_list.append(rs.get_row_data())
            result = pd.DataFrame(data_list, columns=rs.fields)

            N = result.shape[0]

            print(row_index)

            # # 移除停牌股票
            # if result['tradestatus'][N-1] == '0':
            #     print('停牌   out ')
            #     continue
            #
            # # 移除st 股票
            # if result['isST'][N-1] == '1':
            #     print('ST   out ')
            #     continue

            # 移除科创板股票
            if row['代码'][2:5] == '688':
                #print('688   out ')
                continue

            # 计算初级数据
            CLOSE = result['close']
            MA5 = MA(CLOSE, 5)  # 获取5日均线序列
            MA10 = MA(CLOSE, 10)  # 获取10日均线序列
            MA20 = MA(CLOSE, 20)  # 获取20日均线序列
            # up, mid, lower = BOLL(CLOSE)  # 获取布林带指标数据
            dif, dea, macd = MACD(CLOSE)  # 获取macd指标

            ma5 = MA5[N - 1]
            ma10 = MA10[N - 1]
            ma20 = MA20[N - 1]


            # 计算kdj
            K, D, J = calKDJ(result)

            var1 = False
            var2 = False
            var3 = False
            var4 = False
            var5 = False
            var6 = False

            if ma5 > ma10 and ma5 > ma20:
                var1 = True

            # macd 趋势向上
            if macd[N - 1] > -0.1 and macd[N - 1] > macd[N - 2] and macd[N - 2] > macd[N - 3]:
                var2 = True

            # 周线收阳线
            percentChange = float(result['pctChg'][N-1])
            if percentChange > 2:
                var3 = True

            # # dif 趋势向上
            # if dif[N - 1] > dif[N - 2] and dif[N - 2] > dif[N - 3] and dif[N - 3] > dif[N - 4]:
            #     var3 = True
            #
            # # dea 趋势向上
            # if dea[N - 1] > dea[N - 2] and dea[N - 2] > dea[N - 3] and dea[N - 3] > dea[N - 4]:
            #     var4 = True

            if dif[N - 1] > 0 and dea[N - 1] > 0:
                var5 = True

            # 判断KDJ 指标变化
            if J[N-1] > K[N-1] and K[N-1] > D[N-1]:
                var6 = True

            varAll = var1 and var2 and var3 and var5 and var6

            # varAll = var1 and var2 and var5

            if varAll:
                anyData = {'stock': row['代码'], 'name': row_name, 'OPEN': result['open'][N - 1], 'CLOSE': result['close'][N - 1],
                           'pctChg': result['pctChg'][N - 1], 'turn': result['turn'][N-1]}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
                print('success add one', "代码", row['代码'][2:])



        except:
                continue

    print(dfResult)

    #### 结果集输出到csv文件 ####
    file_name = f"{END_DATE}_week_data.csv"
    #dfResult.to_csv(file_name, encoding="gbk", index=False)
    dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)

    #### 登出系统 ####
    bs.logout()

    end_time = time.time()
    print(f"findWeekTrend 运行时间：{end_time - start_time} 秒")






if __name__ == '__main__':

    findWeekTrend()









