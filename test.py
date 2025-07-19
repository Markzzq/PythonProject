import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time

# plotly   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go
from numba.core.typing.typeof import typeof_numpy_random_bitgen

# 股市行情数据获取和作图 -2
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT

import baostock as bs

START_DATE = '2025-03-13'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')

Cd = 1.0


"""
东方财富网-行情首页-沪深京 A 股-每日行情
https://quote.eastmoney.com/concept/sh603777.html?from=classic
:param symbol: 股票代码
:type symbol: str
:param period: choice of {'daily', 'weekly', 'monthly'}
:type period: str
:param start_date: 开始日期
:type start_date: str
:param end_date: 结束日期
:type end_date: str
:param adjust: choice of {"qfq": "前复权", "hfq": "后复权", "": "不复权"}
:type adjust: str
:param timeout: choice of None or a positive float number
:type timeout: float
:return: 每日行情
:rtype: pandas.DataFrame
"""
# 获取股票的历史日线 周线 月线 行情数据  注意 这里的symbol 不需要字母sz sh
# 单个股票历史数据 后复权用于量化分析
# stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol="600519",
#                                         period="daily",
#                                         start_date="20250101",
#                                         end_date='20250530',
#                                         adjust="hfq")
#print(stock_zh_a_hist_df)


"""
新浪财经-A 股-个股的历史行情数据, 大量抓取容易封 IP
https://finance.sina.com.cn/realstock/company/sh603843/nc.shtml
:param symbol: sh600000
:type symbol: str
:param start_date: 20201103; 开始日期
:type start_date: str
:param end_date: 20201103; 结束日期
:type end_date: str
:param adjust: 默认为空: 返回不复权的数据; qfq: 返回前复权后的数据; hfq: 返回后复权后的数据; hfq-factor: 返回后复权因子; qfq-factor: 返回前复权因子
:type adjust: str
:return: 行情数据
:rtype: pandas.DataFrame
"""
# 获取个股日线数据
# df_day = ak.stock_zh_a_daily(symbol='sz300468',
#                     start_date='20250101',
#                     end_date='20250530',
#                     adjust = "")



"""
股票及股票指数历史行情数据-分钟数据
https://finance.sina.com.cn/realstock/company/sh600519/nc.shtml
:param symbol: sh000300
:type symbol: str
:param period: 1, 5, 15, 30, 60 分钟的数据
:type period: str
:param adjust: 默认为空: 返回不复权的数据; qfq: 返回前复权后的数据; hfq: 返回后复权后的数据;
:type adjust: str
:return: specific data
:rtype: pandas.DataFrame
"""
# 获取个股的 分钟线 5分钟线等数据
# df_minute = ak.stock_zh_a_minute(symbol = "sh600519",
#                      period = "1",
#                      adjust = "")





import requests
url = "https://pchq.kaipanla.com/w1/api/index.php"
payload = ""
headers = {
  'Accept': 'application/json, text/javascript, */*; q=0.01',
  'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6',
  'Cache-Control': 'no-cache',
  'Connection': 'keep-alive',
  'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
  'Origin': 'https://www.kaipanla.com',
  'Pragma': 'no-cache',
  'Referer': 'https://www.kaipanla.com/',
  'Sec-Fetch-Dest': 'empty',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Site': 'same-site',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
  'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"macOS"'
}



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

    lg = bs.login()

    start_time = time.time()

    df_stock_list = pd.read_csv('stock_zh_list.csv')
    df_stock = df_stock_list[['代码', '名称']][266:]

    anyData = {'stock': '00', 'name': 'name', 'OPEN': 'open', 'CLOSE': 'close', 'pctChg': 'pctChg', 'turn': 'turn'}
    dfResult = pd.DataFrame(anyData, index=[0])

    for row_index, row in df_stock.iterrows():
        try:
            # time.sleep(0.5)

            # 方法一
            # row_code = row['代码']  # get_price 也是带字母
            # 方法二
            # row_code = row['代码'][2:]  # 是因为抓到的数据带了字母 只取数字

            # 方法三
            row_code = row['代码'][:2] + "." + row['代码'][2:]
            row_name = row['名称']

            # 日线数据
            """
            adjustflag：复权类型，默认不复权：3, 1：后复权, 2：前复权。已支持分钟线、日线、周线、月线前后复权
            """
            rs = bs.query_history_k_data_plus(row_code,
                                              "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                                              start_date=START_DATE, end_date=END_DATE,
                                              frequency="d", adjustflag="2")

            #### 打印结果集 ####
            data_list = []
            while (rs.error_code == '0') & rs.next():
                # 获取一条记录，将记录合并在一起
                data_list.append(rs.get_row_data())
            result = pd.DataFrame(data_list, columns=rs.fields)

            N = result.shape[0]

            # 移除停牌股票
            if result['tradestatus'][N - 1] == '0':
                print('停牌   out ')
                continue

            # 移除st 股票
            if result['isST'][N - 1] == '1':
                print('ST   out ')
                continue

            # 移除科创板股票
            if row['代码'][2:5] == '688':
                # print('688   out ')
                continue

            K, D, J = calKDJ(result)

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

            # # 初级数据  布林中轨曲线
            # up, mid, down = BOLL(CLOSE)
            #
            # x = np.array([1, 2, 3, 4, 5])
            # y = np.array(mid[N - 6:N - 1])
            # slope, intercept = np.polyfit(x, y, 1)
            # # print(slope)

            var1 = False
            var2 = False
            var3 = False
            var4 = False
            var5 = False
            var6 = False
            var7 = False
            var8 = False
            var9 = False


            # if ma5 > Cd*ma10 and ma10 > Cd*ma20:
            if ma5 > Cd * ma10 and ma10 > Cd * ma20 and ma20 > Cd * ma30:
                # and ma30 > Cd * ma60:
                var1 = True

            # macd 趋势向上
            if macd20 > 0 and macd[N - 1] >= macd[N - 2] and macd[N - 2] >= macd[N - 3]:
                var2 = True

            # dif 趋势向上
            if dif[N - 1] > 0 and dif[N - 1] > dif[N - 2] and dif[N - 2] > dif[N - 3] and dif[N - 3] > dif[N - 4]:
                var3 = True

            if dif[N - 1] > 0 and dea[N - 1] > 0:
                var4 = True

            # dea 趋势向上
            if dea[N - 1] > 0 and dea[N - 1] > dea[N - 2] and dea[N - 2] > dea[N - 3] and dea[N - 3] > dea[N - 4]:
                var5 = True

            # if mid[N-1] > mid[N-2] and  mid[N-2] > mid[N-2]

            # Using zip() and all() to Check for strictly increasing list
            # 判断布林中轨趋势递增 连续5日
            # var6 = all(i < j for i, j in zip(mid[N - 6:N - 1], mid[N - 6:N - 1][1:]))
            #
            # 判断KDJ 指标变化
            if D[N - 1] > D[N - 2] and D[N - 2] > D[N - 3]:
                var7 = True

            if CLOSE[N-1] > CLOSE[N-2] and CLOSE[N-2] > CLOSE[N-3]:
                var9 = True

            turnrate = float(result['turn'][N-1])
            if turnrate > 5:
                var8 = True

            varAll = var1 and var7 and var8 and var9

            # varAll = var1 and var2 and var3 and var5 and var4

            # varAll = var1

            if varAll:
                anyData = {'stock': row['代码'], 'name': row_name, 'OPEN': result['open'][N - 1],
                           'CLOSE': result['close'][N - 1], 'pctChg': result['pctChg'][N - 1], 'turn': turnrate}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
                print('success add one', row['代码'][2:], row_name)
                # print(mid)
                # print(slope)


        except:
            continue

    print(dfResult)
    #### 结果集输出到csv文件 ####
    file_name = f"{END_DATE}_test_hj.csv"
    # dfResult.to_csv(file_name, encoding="gbk", index=False)
    dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)

    #### 登出系统 ####
    bs.logout()

    end_time = time.time()
    print(f"test运行时间：{end_time - start_time}秒")