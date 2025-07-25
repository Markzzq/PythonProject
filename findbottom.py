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


START_DATE = '2025-03-13'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')
Cd = 1.02


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
    close = df['close'].astype(float)
    volume = df['volume'].astype(float)
    low = df['low'].astype(float)
    high = df['high'].astype(float)

    df['obv'] = (2 * close - low - high) / (high - low) * volume / 10000

    return df['obv']


# 底部反弹筛选
def findBottom():
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


            # 计算初级数据  均线策略因子
            CLOSE = result['close']
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

            # 初级数据  布林中轨曲线
            up, mid, down = BOLL(CLOSE)

            x = np.array([1, 2, 3, 4, 5])
            y = np.array(mid[N-6:N-1])
            slope, intercept = np.polyfit(x, y, 1)
            #print(slope)

            # 计算kdj
            K, D , J = calKDJ(result)

            # 短线指标CCI

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
            if ma5 > ma10:
                var1 = True

            # macd 在0线下 但趋势向上
            if macd[N - 1] > macd[N - 2] and macd[N - 2] > macd[N - 3] and macd[N - 3] > macd[N - 4]:
                var2 = True

            # dif 趋势向上
            if dif[N - 1] > dif[N - 2] and dif[N - 2] > dif[N - 3] and dif[N - 3] > dif[N - 4]:
                var3 = True

            # dea 趋势向上
            if dea[N - 1] > dea[N - 2] and dea[N - 2] > dea[N - 3] and dea[N - 3] > dea[N - 4]:
                var4 = True

            if dif[N - 1] > 0:   ##dif 已经向上穿越了
                var5 = True

            # Using zip() and all() to Check for strictly increasing list
            # 判断布林中轨趋势递增 连续5日
            var6 = all(i < j for i, j in zip(mid[N-6:N-1], mid[N-6:N-1][1:]))

            # 判断KDJ 指标变化
            if J[N-1] > K[N-1] and K[N-1] > D[N-1]:
                var7 = True

            if J[N-1] > J[N-2] and J[N-2] > J[N-3] and J[N-3] > J[N-4]:
                var8 = True

            if J[N-1] < 85:
                var9 = True

            turnrate = float(result['turn'][N-1])
            if turnrate > 3:
                var10 = True


            varAll = var1 and var2 and var3 and var4 and var7 and var8 and var9 and var10

            if varAll:
                anyData = {'stock': row['代码'], 'name': row_name, 'OPEN': result['open'][N - 1],
                           'CLOSE': result['close'][N - 1], 'pctChg': result['pctChg'][N - 1], 'turn': result['turn'][N-1]}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
                print('success add one', row['代码'][2:], row_name)

        except:
            continue

    print(dfResult)

    #### 结果集输出到csv文件 ####
    file_name = f"{END_DATE}_bottom_stock.csv"
    #dfResult.to_csv(file_name, encoding="gbk", index=False)
    dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)

    #### 登出系统 ####
    bs.logout()

    end_time = time.time()
    print(f"findBottom 运行时间：{end_time - start_time} 秒")


if __name__ == '__main__':

    findBottom()



