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
Cd = 1.05


if __name__ == '__main__':

    lg = bs.login()

    df_stock_list = pd.read_csv('stock_zh_list.csv')
    df_stock = df_stock_list[['代码', '名称']][266:]

    anyData = {'stock': '00', 'name': 'name','OPEN': 'open', 'CLOSE': 'close', 'pctChg': 'pctChg'}
    dfResult = pd.DataFrame(anyData, index=[0])

    for row_index, row in df_stock.iterrows():
        try:
            #time.sleep(0.5)

            # 方法一
            #row_code = row['代码']  # get_price 也是带字母
            # 方法二
            # row_code = row['代码'][2:]  # 是因为抓到的数据带了字母 只取数字

            # 方法三
            row_code = row['代码'][:2] + "." +  row['代码'][2:]
            row_name = row['名称']

            # 周线数据
            """
            frequency：数据类型，默认为d，日k线；d=日k线、w=周、m=月、5=5分钟、15=15分钟、30=30分钟、60=60分钟k线数据，不区分大小写；指数没有分钟线数据；周线每周最后一个交易日才可以获取，月线每月最后一个交易日才可以获取。
            adjustflag：复权类型，默认不复权：3；1：后复权；2：前复权。已支持分钟线、日线、周线、月线前后复权。
            """
            rs = bs.query_history_k_data_plus(row_code,
                                              "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                                              start_date=START_DATE, end_date=END_DATE,
                                              frequency="w", adjustflag="2")
            #### 打印结果集 ####
            data_list = []
            while (rs.error_code == '0') & rs.next():
                # 获取一条记录，将记录合并在一起
                data_list.append(rs.get_row_data())
            result = pd.DataFrame(data_list, columns=rs.fields)

            N = result.shape[0]

            # 移除停牌股票
            if result['tradestatus'][N-1] == '0':
                print('停牌   out ')
                continue

            # 移除st 股票
            if result['isST'][N-1] == '1':
                print('ST   out ')
                continue

            # 移除科创板股票
            if row['代码'][2:5] == '688':
                #print('688   out ')
                continue



            # 计算初级数据
            CLOSE = result['close']
            MA5 = MA(CLOSE, 5)  # 获取5日均线序列
            MA10 = MA(CLOSE, 10)  # 获取10日均线序列
            # up, mid, lower = BOLL(CLOSE)  # 获取布林带指标数据
            dif, dea, macd = MACD(CLOSE)  # 获取macd指标

            ma5 = MA5[N - 1]
            ma10 = MA10[N - 1]
            macd10 = macd[N - 1]

            var1 = False
            var2 = False
            var3 = False
            var4 = False
            var5 = False
            # var6 = False

            if ma5 > macd10:
                var1 = True

            # macd 趋势向上
            if macd10 > 0 and macd[N - 1] > macd[N - 2] and macd[N - 2] > macd[N - 3] and macd[N - 3] > macd[N - 4]:
                var2 = True

            # dif 趋势向上
            if dif[N - 1] > dif[N - 2] and dif[N - 2] > dif[N - 3] and dif[N - 3] > dif[N - 4]:
                var3 = True

            if dif[N - 1] < 0 and dea[N - 1] < 0:
                var4 = True

            # dea 趋势向上
            if dea[N - 1] > dea[N - 2] and dea[N - 2] > dea[N - 3] and dea[N - 3] > dea[N - 4]:
                var5 = True



            varAll = var1
            # v1 = calMACD(result, N)
            #
            # vt = v1

            if varAll:
                anyData = {'stock': row['代码'], 'name': row_name,'OPEN': result['open'][N-1], 'CLOSE': result['close'][N-1], 'pctChg': result['pctChg'][N-1]}
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









