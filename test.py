import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time
import utils


# plotly   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go
from numba.core.typing.typeof import typeof_numpy_random_bitgen

# 股市行情数据获取和作图 -2
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT

import baostock as bs



# 单股票测试策略
def getOneStock():
    start_time = time.time()

    START_DATE = '2025-03-13'
    # END_DATE = '2025-07-31'
    END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')

    C1 = 1.02
    C2 = 1.01
    #
    dfResult = pd.DataFrame(data=None, columns=['stock', 'name', 'OPEN', 'CLOSE', 'pctChg', 'turn', 'bias', 'obv1', 'obv2'])

    # 登陆baostock开源库
    lg = bs.login()

    row_code = "sz.000593"
    row_name = "深桑达A"

    # 日线数据
    """
    adjustflag：复权类型，默认不复权：3, 1：后复权, 2：前复权。已支持分钟线、日线、周线、月线前后复权
    """
    rs = bs.query_history_k_data_plus(row_code,
                                      "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                                      start_date = START_DATE, end_date = END_DATE,
                                      frequency = "d", adjustflag = "2")

    #### 打印结果集 ####
    data_list = []
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录合并在一起
        data_list.append(rs.get_row_data())
    result = pd.DataFrame(data_list, columns=rs.fields)

    N = result.shape[0]

    # 读取数据列
    OPEN = result['open'].astype(float)
    CLOSE = result['close'].astype(float)
    HIGH = result['high'].astype(float)
    LOW = result['low'].astype(float)

    # 计算初级数据  均线策略因子
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

    # 初级数据  布林中轨曲线
    up, mid, down = BOLL(CLOSE)

    # 计算kdj
    K, D, J = utils.calKDJ(result)

    # rsi 指标 6 日线
    rsi6 = RSI(CLOSE, N=6)
    rsi12 = RSI(CLOSE, N=12)
    rsi24 = RSI(CLOSE, N=24)

    # 量能指标MAVOL
    volume = result['volume'].astype(float)
    volume5 = MA(volume, 5)  # 获取5日均线序列
    volume10 = MA(volume, 10)  # 获取5日均线序列
    volume_diff = volume5 - volume10

    # OBV指标
    obv = utils.calOBV(result)

    # 短线指标CCI
    cci = CCI(CLOSE, HIGH, LOW)

    # BRAR  情绪指标
    ar, br = BRAR(OPEN, CLOSE, HIGH, LOW)

    # 三重指数平滑平均线
    trix, trma = TRIX(CLOSE, 12, 9)
    tr_diff = trix - trma



    ## 其他数据
    # 计算偏离5日线的百分比
    bias = (float(CLOSE[N - 1]) / ma5 - 1) * 100

    # 股票题材
    stock_hot_keyword_em_df = ak.stock_hot_keyword_em(symbol='SZ301580')
    keyword = stock_hot_keyword_em_df.iloc[-1]['概念名称']
    print(keyword)

    print(result)

    # print()

    #### 登出系统 ####
    bs.logout()

    end_time = time.time()
    print(f"getOneStock 运行时间：{end_time - start_time} 秒")








# 均线多因子策略
def findTestTrend():
    start_time = time.time()

    # 读取股票列表
    df_stock_list = pd.read_csv('stock_zh_list.csv')
    df_stock = df_stock_list[['代码', '名称']][282:]

    dfResult = pd.DataFrame(data=None, columns=['stock', 'name', 'OPEN', 'CLOSE', 'pctChg', 'turn', 'bias'])
    dfTest = pd.DataFrame(data=None, columns=['stock', 'name', 'OPEN', 'CLOSE', 'pctChg', 'turn', 'bias'])


    # 登陆baostock开源库
    lg = bs.login()

    START_DATE = '2025-06-13'
    # END_DATE = '2025-08-01'
    END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')

    C1 = 1.01
    C2 = 1.01

    for row_index, row in df_stock.iterrows():
        try:
            # 方法三
            row_code = row['代码'][:2] + "." +  row['代码'][2:]
            row_name = row['名称']

            # 日线数据
            """
            adjustflag：复权类型，默认不复权：3, 1：后复权, 2：前复权。已支持分钟线、日线、周线、月线前后复权
            """
            rs = bs.query_history_k_data_plus(row_code,
                                              "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                                              start_date = START_DATE, end_date = END_DATE,
                                              frequency = "d", adjustflag = "2")

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

            # 多因子标识
            sector = 0

            # 读取数据列
            OPEN = result['open'].astype(float)
            CLOSE = result['close'].astype(float)
            HIGH = result['high'].astype(float)
            LOW = result['low'].astype(float)

            # 计算初级数据  均线策略因子
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

            # 初级数据  布林中轨曲线
            up, mid, down = BOLL(CLOSE)

            # 计算kdj
            K, D, J = utils.calKDJ(result)

            # rsi 指标 6 日线
            rsi6 = RSI(CLOSE, N=6)
            rsi12 = RSI(CLOSE, N=12)
            rsi24 = RSI(CLOSE, N=24)

            # 量能指标MAVOL
            volume = result['volume'].astype(float)
            volume5 = MA(volume, 5)  # 获取5日均线序列
            volume10 = MA(volume, 10)  # 获取5日均线序列
            volume_diff = volume5 - volume10

            # OBV指标
            obv = utils.calOBV(result)

            # 短线指标CCI
            cci = CCI(CLOSE, HIGH, LOW)

            # BRAR  情绪指标
            ar, br = BRAR(OPEN, CLOSE, HIGH, LOW)

            # 三重指数平滑平均线
            trix, trma =  TRIX(CLOSE, 12, 9)
            tr_diff = trix - trma


            var1 = False
            var2 = False
            var3 = False
            var4 = False
            var5 = False
            var6 = False
            var7 = False
            var8 = False
            var9 = False
            var10 = False


            # 均线多头排列
            if ma5 > C1 * ma10 and ma10 > C2 * ma20 and ma20 > C2 * ma30:
                var1 = True

            # macd 趋势向上 且dif dea 大于0
            if macd[N - 1] > 0 and macd[N - 2] > 0 and macd[N - 3] > 0:
                var2 = True

            # if macd[N - 1] > 0 and macd[N - 1] >= macd[N - 2] and macd[N - 2] >= macd[N - 3] and dif[N-2] > 0:
            #     var2 = True

            # 判断KDJ 指标变化
            if J[N-1] > K[N-1] and K[N-1] > D[N-1] and J[N-1]>60 and K[N-1]>50:
                var3 = True
                # sector += 1

            if J[N-3] < K[N-3] and K[N-3] < D[N-3]:
                var4 = True

            # obv 指标
            if obv[N - 1] > 0 and obv[N - 2] > 0 and obv[N-1] > obv[N-2]:
                var7 = True
                # sector += 1

            # BRAR 指标
            if ar[N-1] > 120 or br[N-1] > 120:
                var8 = True
                sector += 1

            # CCI 指标
            if cci[N-1] > 90:
                var9 = True

            # RSI 指标
            if rsi6[N-1] > rsi12[N-1] and rsi12[N-1] > rsi24[N-1]:
                var10 = True

            # # 量能指标
            # if volume5[N-1] > volume5[N-2] and volume5[N-2] > volume5[N-3] and volume_diff[N-2] > 0:
            #     var5 = True
            #     # sector += 1
            #
            # if volume_diff[N - 1] > volume_diff[N-2] and volume_diff[N - 2] > volume_diff[N-3]:
            #     var6 = True
            #     # sector += 1
            #
            # # TRIX 指标
            # if tr_diff[N-1] > 0 and tr_diff[N-1] > tr_diff[N-2] and tr_diff[N-2] > tr_diff[N-3]:
            #     var10 = True
            #     sector += 1    and var3 and var7 and var8 and var9 and var10

            varAll = var1 and var2 and var7 and var8 and var9


            vartest = var7 and var8 and var9

            ## 其他数据
            # 计算偏离5日线的百分比
            bias = (float(CLOSE[N - 1]) / ma5 - 1) * 100


            if vartest:

                # 股票题材
                stock_hot_keyword_em_df = ak.stock_hot_keyword_em(symbol=row['代码'])
                keyword = stock_hot_keyword_em_df['概念名称']

                anyData = {'stock': row['代码'], 'name': row_name, 'OPEN': result['open'][N - 1], 'CLOSE': result['close'][N - 1],
                           'pctChg': result['pctChg'][N - 1], 'turn': result['turn'][N-1], 'bias': bias}
                df_index = row_index + 1
                dfTest.loc[df_index] = anyData
                print('success add one', row['代码'][2:], row_name)

            # varAll = var1 and var2 and var3 and var4 and var5 and var6 and var7 and var8 and var9 and var10

            if varAll:

                # 股票题材
                stock_hot_keyword_em_df = ak.stock_hot_keyword_em(symbol=row['代码'])
                keyword = stock_hot_keyword_em_df['概念名称']

                anyData = {'stock': row['代码'], 'name': row_name, 'OPEN': result['open'][N - 1], 'CLOSE': result['close'][N - 1],
                           'pctChg': result['pctChg'][N - 1], 'turn': result['turn'][N-1], 'bias': bias}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
                print('success add one', row['代码'][2:], row_name)


        except:
            continue

    print(dfResult)

    #### 结果集输出到csv文件 ####
    file_name1 = f"{END_DATE}_wse.csv"
    file_name = f"{END_DATE}_test.csv"


    dfTest.to_csv(file_name1, encoding="utf-8-sig", index=False)
    dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)

    #### 登出系统 ####
    bs.logout()

    end_time = time.time()
    print(f" 运行时间：{end_time - start_time} 秒")








# 均线多因子策略
def findTrend():
    start_time = time.time()

    # 读取股票列表
    df_stock_list = pd.read_csv('stock_zh_list.csv')
    df_stock = df_stock_list[['代码', '名称']][266:]

    dfResult = pd.DataFrame(data=None, columns=['stock', 'name', 'OPEN', 'CLOSE', 'pctChg', 'turn', 'bias', 'obv1', 'obv2'])

    # 登陆baostock开源库
    lg = bs.login()

    START_DATE = '2025-03-13'
    # END_DATE = '2025-07-25'
    END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')

    C1 = 1.02
    C2 = 1.01

    for row_index, row in df_stock.iterrows():
        try:
            # 方法三
            row_code = row['代码'][:2] + "." +  row['代码'][2:]
            row_name = row['名称']

            # 日线数据
            """
            adjustflag：复权类型，默认不复权：3, 1：后复权, 2：前复权。已支持分钟线、日线、周线、月线前后复权
            """
            rs = bs.query_history_k_data_plus(row_code,
                                              "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                                              start_date = START_DATE, end_date = END_DATE,
                                              frequency = "d", adjustflag = "2")

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

            # 多因子标识
            sector = 0

            # 读取数据列
            OPEN = result['open'].astype(float)
            CLOSE = result['close'].astype(float)
            HIGH = result['high'].astype(float)
            LOW = result['low'].astype(float)

            # 计算初级数据  均线策略因子
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

            # 初级数据  布林中轨曲线
            up, mid, down = BOLL(CLOSE)

            # 计算kdj
            K, D, J = utils.calKDJ(result)

            # 量能指标MAVOL
            volume = result['volume']
            volume5 = MA(volume, 5)  # 获取5日均线序列
            volume10 = MA(volume, 10)  # 获取5日均线序列
            volume_diff = volume5 - volume10

            # OBV指标
            obv = utils.calOBV(result)

            # 短线指标CCI
            cci = CCI(CLOSE, HIGH, LOW)

            # rsi 指标 6 日线
            rsi6 = RSI(CLOSE, N=6)
            rsi12 = RSI(CLOSE, N=12)
            rsi24 = RSI(CLOSE, N=24)


            # BRAR  情绪指标
            ar, br = BRAR(OPEN, CLOSE, HIGH, LOW)

            # 三重指数平滑平均线
            trix, trma =  TRIX(CLOSE)
            tr_diff = trix - trma


            var1 = False
            var2 = False
            var3 = False
            var4 = False
            var5 = False
            var6 = False
            var7 = False
            var8 = False
            var9 = False
            var10 = False


            # if ma5 > Cd*ma10 and ma10 > Cd*ma20:
            if ma5 > C1 * ma10 and ma10 > C2 * ma20 and ma20 > C2 * ma30:
                var1 = True

            # macd 趋势向上
            if macd[N - 3] > 0 and macd[N - 1] >= macd[N - 2] and macd[N - 2] >= macd[N - 3] and macd[N - 3] >= macd[N - 4]:
                var2 = True

            # # dif 趋势向上
            # if dif[N - 1] > dif[N - 2] and dif[N - 2] > dif[N - 3] and dif[N - 3] > dif[N - 4]:
            #     var3 = True
            #
            # # dea 趋势向上
            # if dea[N - 1] > dea[N - 2] and dea[N - 2] > dea[N - 3] and dea[N - 3] > dea[N - 4]:
            #     var4 = True
            #
            # if dif[N - 1] > 0 and dea[N - 1] > 0:
            #     var5 = True

            # Using zip() and all() to Check for strictly increasing list
            # 判断布林中轨趋势递增 连续5日
            var6 = all(i < j for i, j in zip(mid[N-6:N-1], mid[N-6:N-1][1:]))


            # 多因子评测
            # 30日均线上穿
            if ma30 > ma60:
                sector += 1

            # 判断KDJ 指标变化
            if J[N-1] > K[N-1] and K[N-1] > D[N-1]:
                var1 = True

            if J[N-1] > J[N-2] and J[N-2] > J[N-3]:
                var2 = True

            if cci[N-1] > 100:
                var3 = True

            if rsi6[N-1] > 55 and rsi6[N-1] > rsi12[N-1] and rsi12[N-1] > rsi24[N-1]:
                var4 = True

            if obv[N - 1] > 0 and obv[N - 2] > 0 and obv[N-1] > obv[N-2]:
                var5 = True

            # turnrate = float(result['turn'][N-1])
            # if turnrate > 5:
            #     sector += 1

            # 量能指标
            if volume5[N-1] > volume5[N-2] and volume5[N-2] > volume5[N-3] and volume_diff[N-1] > volume_diff[N-2]:
                sector += 1

            if volume_diff[N - 1] > volume_diff[N-2] and volume_diff[N - 2] > volume_diff[N-3]:
                sector += 1

            # obv 指标
            # if OBV[N-1] > 0 and OBV[N-1] > OBV[N-2] and OBV[N-2] > OBV[N-3]:
            if obv[N - 1] > 0 and obv[N - 2] > 0:
                sector += 1

            # BRAR 指标
            if ar[N-1] > 150 or br[N-1] > 150:
                sector += 1

            # TRIX 指标
            if tr_diff[N-1] > 0 and tr_diff[N-1] > tr_diff[N-2] and tr_diff[N-2] > tr_diff[N-3]:
                sector += 1


            if sector >= 7:
                var7 = True


            # varAll = var1 and var2 and var3 and var4 and var5 and var6 and var7
            varAll = var1 and var2 and var3 and var4 and var5

            if varAll:

                ## 其他数据
                # 计算偏离5日线的百分比
                bias = (float(CLOSE[N-1]) / ma5 - 1) * 100

                # 股票题材
                stock_hot_keyword_em_df = ak.stock_hot_keyword_em(symbol=row['代码'])
                keyword = stock_hot_keyword_em_df['概念名称']

                anyData = {'stock': row['代码'], 'name': row_name, 'OPEN': result['open'][N - 1], 'CLOSE': result['close'][N - 1],
                           'pctChg': result['pctChg'][N - 1], 'turn': result['turn'][N-1], 'bias': bias, 'obv1':obv[N - 1], 'obv2':obv[N - 2]}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
                print('success add one', row['代码'][2:], row_name)


        except:
            continue

    print(dfResult)

    #### 结果集输出到csv文件 ####
    file_name = f"{END_DATE}_fffff.csv"

    #dfResult.to_csv(file_name, encoding="gbk", index=False)
    dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)

    #### 登出系统 ####
    bs.logout()

    end_time = time.time()
    print(f" 运行时间：{end_time - start_time} 秒")





## 复盘一段时间的基金走势看后续是否如计划涨
def reviewETF(filename):
    start_time = time.time()

    # START_DATE = '20250101'
    # END_DATE = '20250625'

    START_DATE = '2025-01-01'
    END_DATE = '2025-06-25'
    # END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')


    df_etf_list = pd.read_csv(filename)
    df_etf = df_etf_list[['代码', '名称']]

    # anyData = {'stock': '00', 'name': 'name', 'OPEN': 'open', 'CLOSE': 'close', 'pctChg': 'pctChg', 'turn': 'turn', 'bias': 'ma5bias'}
    # dfResult = pd.DataFrame(anyData, index=[0])
    dfResult = pd.DataFrame(data=None, columns=['代码', '名称', '7日涨幅', '历史百分位'])
    dfTop = pd.DataFrame(data=None, columns=['代码', '名称', '7日涨幅', '历史百分位'])
    dfReverse = pd.DataFrame(data=None, columns=['代码', '名称', '7日涨幅', '历史百分位'])



    for row_index, row in df_etf.iterrows():
        try:
            time.sleep(0.5)

            etf_code = row['代码']  # 是因为抓到的数据带了字母 只取数字
            etf_name = row['名称']

            # etf_hist_df = ak.fund_etf_hist_em(symbol=etf_code, period="daily", start_date=START_DATE,
            #                                           end_date=END_DATE, adjust="")

            etf_hist_df = ak.fund_etf_hist_sina(symbol=etf_code)

            nt = etf_hist_df.shape[0]
            n = nt -100

            CLOSE = etf_hist_df['close'].astype(float)


            allHigh = np.max(CLOSE)
            alllow = np.min(CLOSE)

            today_close = CLOSE[n-1]
            day30_before_close = CLOSE[n-30]
            day7_before_close = CLOSE[n-7]

            # 计算30日波动率
            dif30 = (today_close - day30_before_close) / day30_before_close

            # 计算7日波动率
            dif7 = (today_close - day7_before_close) / day7_before_close

            # 历史百分位
            bias_low = (today_close - alllow) / (allHigh - alllow)

            # 筛选合适的基金
            # 短线反转的etf
            # 计算kdj
            K, D, J = utils.calKDJ(etf_hist_df)

            var1 = False
            var2 = False
            var3 = False
            var4 = False


            # 判断KDJ 指标变化
            if J[n-1] > K[n-1] and K[n-1] > D[n-1]:
                var1 = True

            if J[n-1] > J[n-2] and J[n-2] > J[n-3]:
                var2 = True

            # rsi 指标 6 日线
            rsi6 = RSI(CLOSE, N=6)
            rsi12 = RSI(CLOSE, N=12)
            rsi24 = RSI(CLOSE, N=24)
            if rsi6[n-1] > rsi12[n-1] and rsi12[n-1] > rsi24[n-1]:
                var3 = True

            # 收盘价连续增加
            if CLOSE[n-1] >= CLOSE[n-2] and CLOSE[n-2] >= CLOSE[n-3]:
                var4 = True

            # 获取macd指标
            dif, dea, macd = MACD(CLOSE)

            # 计算初级数据  均线策略因子
            MA5 = MA(CLOSE, 5)  # 获取5日均线序列
            MA10 = MA(CLOSE, 10)  # 获取5日均线序列
            MA20 = MA(CLOSE, 20)  # 获取20日均线序列
            MA30 = MA(CLOSE, 30)  # 获取30日均线序列
            MA60 = MA(CLOSE, 60)  # 获取60日均线序列


            # if var1 and var2 and var3 and var4:
            #     anyData = {'代码': etf_code, '名称': etf_name, '7日涨幅':dif7, '历史百分位': bias_low}
            #     df_index = row_index + 1
            #     dfReverse.loc[df_index] = anyData
            #     print("add one in reverse", etf_code, etf_name)



            # 7日波动大于10个点 同时macd 转正 dif 为正 dea 为正

            tr1 = False
            tr2 = False
            tr3 = False
            tr4 = False

            if MA5[n-1] > MA5[n-2] and MA5[n-2] > MA5[n-3]:
                tr1 = True

            if MA5[n-1] > MA10[n-1] and MA10[n-1] > MA20[n-1] and MA20[n-1] > MA30[n-1]:
                tr2 = True

            if macd[n-1] > 0:
                tr3 = True


            if tr1 and tr2 and tr3:
                anyData = {'代码': etf_code, '名称': etf_name, '7日涨幅':dif7, '历史百分位': bias_low}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
                print("add one ", etf_code, etf_name)

            # # 创了新高的股票
            # if bias_low == 1:
            #     anyData = {'代码': etf_code, '名称': etf_name, '7日涨幅':dif7, '历史百分位': bias_low}
            #     df_index = row_index + 1
            #     dfTop.loc[df_index] = anyData


        except:
            continue


    end_time = time.time()
    print(f"reviewETF运行时间：{end_time - start_time}秒")

    #### 结果集输出到csv文件 ####
    file_name = f"{END_DATE}_reviewETF.csv"
    # top_name = f"{END_DATE}_TopETF.csv"
    # reverse_name = f"{END_DATE}_ReverseETF.csv"


    dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)
    # dfTop.to_csv(top_name, encoding="utf-8-sig", index=False)
    # dfReverse.to_csv(reverse_name, encoding="utf-8-sig", index=False)










if __name__ == '__main__':

    # getOneStock()
    findTestTrend()

    # findTrend()
    #
    # utils.showAllStock('2025-10-22_bottom_stock.csv')

    # reviewETF('sina_etf_list.csv')

