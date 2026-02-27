import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time
import schedule
import utils

# 股市行情数据获取
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT
import baostock as bs

START_DATE = '2025-09-13'
# END_DATE = '2025-07-23'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')
C1 = 1.02
C2 = 1.01

def stockSearch():
    start_time = time.time()

    # 读取股票列表   294以前是北交所
    df_stock_list = pd.read_csv('stock_zh_list.csv')
    df_stock = df_stock_list[['代码', '名称']]

    # dfResult = pd.DataFrame(data=None, columns=['stock', 'name', 'open', 'close', 'pctChg', 'turn', 'bias', '题材'])

    dfGoodTrendStock = pd.DataFrame(data=None, columns=['stock', 'name', 'open', 'close', 'pctChg', 'turn', 'bias', '题材'])
    dfReverseStock = pd.DataFrame(data=None, columns=['stock', 'name', 'open', 'close', 'pctChg', 'turn', 'bias', '题材'])
    dfFgStock = pd.DataFrame(data=None, columns=['stock', 'name', 'open', 'close', 'pctChg', 'turn', 'bias', '题材'])

    dfStockPool = pd.DataFrame(data=None, columns=['stock', 'name', 'open', 'close', 'pctChg', 'turn', 'bias', '题材'])

    # 登陆baostock开源库
    lg = bs.login()

    for row_index, row in df_stock.iterrows():
        try:
            # 方法三
            row_code = row['代码'][:2] + "." +  row['代码'][2:]
            row_name = row['名称']

            # 移除北交所股票
            if row['代码'][:2] == 'bj':
                print('北交所   out ')
                continue

            # 移除科创板股票
            if row['代码'][2:5] == '688':
                print('688   out ')
                continue

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
            DIF_, DEA_, MACD_ = MACD(CLOSE)

            ma5 = MA5[N - 1]
            ma10 = MA10[N - 1]
            ma20 = MA20[N - 1]
            ma30 = MA30[N - 1]
            ma60 = MA60[N - 1]

            # 初级数据  布林中轨曲线
            UP, MID, DOWN = BOLL(CLOSE)

            # 计算kdj
            K, D, J = utils.calKDJ(result)

            # 量能指标MAVOL
            VOLUME = result['volume']
            VOLUME5 = MA(VOLUME, 5)  # 获取5日均线序列
            VOLUME10 = MA(VOLUME, 10)  # 获取5日均线序列
            VOLUME_diff = VOLUME5 - VOLUME10

            # OBV指标
            OBV = utils.calOBV(result)

            # 短线指标CCI
            CCI_ = CCI(CLOSE, HIGH, LOW)

            # rsi 指标 6 日线
            RSI6 = RSI(CLOSE, N=6)
            RSI12 = RSI(CLOSE, N=12)
            RSI24 = RSI(CLOSE, N=24)

            # BRAR  情绪指标
            AR, BR = BRAR(OPEN, CLOSE, HIGH, LOW)

            # 三重指数平滑平均线
            TRIX_, TRMA_ =  TRIX(CLOSE)
            TR_diff = TRIX_ - TRMA_

            ## 其他参考数据
            # 计算偏离5日线的百分比
            bias = (float(CLOSE[N - 1]) / ma5 - 1) * 100


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

            var21 = False
            var22 = False
            var23 = False
            var24 = False
            var25 = False
            var26 = False
            var27 = False



            ######################## 策略1：均线多头
            # 均线多头展开
            if ma5 > C1 * ma10 and ma10 > C2 * ma20 and ma20 > C2 * ma30 and ma30 > ma60:
                var1 = True

            # macd 趋势向上
            if MACD_[N - 1] > 0 and MACD_[N - 1] >= MACD_[N - 2] and MACD_[N - 2] >= MACD_[N - 3] and MACD_[N - 3] >= MACD_[N - 4]:
                var2 = True

            # dif 趋势向上
            if DIF_[N - 1] > DIF_[N - 2] and DIF_[N - 2] > DIF_[N - 3] and DIF_[N - 3] > DIF_[N - 4]:
                var3 = True

            # dea 趋势向上
            if DEA_[N - 1] > DEA_[N - 2] and DEA_[N - 2] > DEA_[N - 3] and DEA_[N - 3] > DEA_[N - 4]:
                var4 = True

            if DIF_[N - 1] > 0 and DEA_[N - 1] > 0:
                var5 = True

            # Using zip() and all() to Check for strictly increasing list
            # 判断布林中轨趋势递增 连续5日
            var6 = all(i < j for i, j in zip(MID[N-6:N-1], MID[N-6:N-1][1:]))

            # 判断KDJ 指标变化
            if J[N-1] > K[N-1] and K[N-1] > D[N-1]:
                var7 = True

            # 换手率指标是否有用  ？？
            turnrate = float(result['turn'][N-1])
            if turnrate > 4:
                var8 = True

            # 量能指标
            if VOLUME5[N-1] > VOLUME5[N-2] and VOLUME5[N-2] > VOLUME5[N-3] and VOLUME_diff[N-1] > VOLUME_diff[N-2]:
                var9 = True

            # obv 指标
            # if OBV[N-1] > 0 and OBV[N-1] > OBV[N-2] and OBV[N-2] > OBV[N-3]:
            if OBV[N - 1] > 0 and OBV[N - 2] > 0 and OBV[N-1] > OBV[N-2]:
                var10 = True

            ## 其他数据
            # 计算偏离5日线的百分比
            bias = (float(CLOSE[N-1]) / ma5 - 1) * 100

            # 股票题材
            stock_hot_keyword_em_df = ak.stock_hot_keyword_em(symbol=row['代码'])
            keyword = stock_hot_keyword_em_df.iloc[-1]['概念名称']

            # 个股数据
            anyData = {'stock': row['代码'], 'name': row_name, 'open': result['open'][N - 1],'close': result['close'][N - 1],
                       'pctChg': result['pctChg'][N - 1], 'turn': result['turn'][N - 1], 'bias': bias, '题材': keyword}


            varAll = var1 and var2 and var3 and var4 and var5 and var6 and var7 and var8 and var9 and var10

            if varAll:

                good_index = row_index + 1
                dfGoodTrendStock.loc[good_index] = anyData
                print('success add one', row['代码'][2:], row_name)


            ################################### 策略2：触底反弹
            # 均线多头排列
            if ma5 > C1 * ma10 and ma10 > C2 * ma20 and ma20 > C2 * ma30:
                var21 = True

            # macd 趋势向上 且dif dea 大于0
            if MACD_[N - 1] > 0 and MACD_[N - 1] >= MACD_[N - 2] and MACD_[N - 2] >= MACD_[N - 3] and DIF_[N-2] > 0:
                var22 = True

            # 判断KDJ 指标变化
            if J[N-1] > K[N-1] and K[N-1] > D[N-1] and J[N-1]>60 and K[N-1]>50:
                var23 = True

            # obv 指标
            if OBV[N - 1] > 0 and OBV[N - 2] > 0 and OBV[N-1] > OBV[N-2]:
                var24 = True

            # BRAR 指标
            if AR[N-1] > 130 or BR[N-1] > 130:
                var25 = True

            # CCI 指标
            if CCI_[N-1] > 90:
                var26 = True

            # RSI 指标
            if RSI6[N-1] > RSI12[N-1] and RSI12[N-1] > RSI24[N-1]:
                var27 = True


            varR = var21 and var22 and var23 and var24 and var25 and var26 and var27

            if varR:

                reverse_index = row_index + 1
                dfReverseStock.loc[reverse_index] = anyData
                print('success add one', row['代码'][2:], row_name)


            # 策略：fg严选



            # 策略：股票池
            varP = var1 and var2 and var3 and var7 and var8 and var9 and var10

            if varP:

                pool_index = row_index + 1
                dfStockPool.loc[pool_index] = anyData
                print('success add one', row['代码'][2:], row_name)



        except:
            continue

    # print(dfResult)

    #### 结果集输出到csv文件 ####
    file_GoodTrend = f"{END_DATE}_Stock_Good.csv"
    file_Reverse = f"{END_DATE}_Stock_Reverse.csv"
    file_FG = f"{END_DATE}_Stock_FG.csv"

    file_StockPool = f"stock_pool.csv"




    #dfResult.to_csv(file_name, encoding="gbk", index=False)
    # dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)
    dfGoodTrendStock.to_csv(file_GoodTrend, encoding="utf-8-sig", index=False)
    dfReverseStock.to_csv(file_Reverse, encoding="utf-8-sig", index=False)
    dfFgStock.to_csv(file_FG, encoding="utf-8-sig", index=False)

    dfStockPool.to_csv(file_StockPool, encoding="utf-8-sig", index=False)


    #### 登出系统 ####
    bs.logout()

    end_time = time.time()
    print(f"findStock 运行时间：{end_time - start_time} 秒")


if __name__ == '__main__':

    stockSearch()