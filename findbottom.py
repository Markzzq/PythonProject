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

# plotly express   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

# matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

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



if __name__ == '__main__':

    lg = bs.login()

    df_stock_list = pd.read_csv('stock_zh_list.csv')
    df_stock = df_stock_list[['代码', '名称']][266:]

    anyData = {'stock': '00', 'name': 'name','OPEN': 'open', 'CLOSE': 'close', 'pctChg': 'pctChg'}
    dfResult = pd.DataFrame(anyData, index=[0])

    for row_index, row in df_stock.iterrows():
        try:
            #time.sleep(0.5)

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


            K, D , J = calKDJ(result)


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

            # macd 在0线下 但趋势向上
            if macd20 < 0 and macd[N - 1] >= macd[N - 2] and macd[N - 2] >= macd[N - 3] and macd[N - 3] >= macd[N - 4]:
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
            var6 = all(i < j for i, j in zip(mid[N-6:N-1], mid[N-6:N-1][1:]))

            # 判断KDJ 指标变化
            if J[N-1] > K[N-1] and K[N-1] > D[N-1]:
                var7 = True

            if J[N-1] > J[N-2] and J[N-2] > J[N-3]:
                var8 = True


            varAll = var2 and var7

            if varAll:
                anyData = {'stock': row['代码'], 'name': row_name,'OPEN': result['open'][N-1], 'CLOSE': result['close'][N-1], 'pctChg': result['pctChg'][N-1]}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
                print('success add one', row['代码'][2:], row_name)

                hkmi = ak.fund_etf_hist_sina(symbol=row['代码'])

                # # 打开在网页端
                # fig = px.line(result, x="date", y="close", title=row['代码'][2:])
                # fig.add_trace(go.Scatter(x=[result['date'].iloc[-1]],
                #                          y=[result['close'].iloc[-1]],
                #                          text=[result['date'].iloc[-1]],
                #                          mode='markers+text',
                #                          marker=dict(color='red', size=10),
                #                          textfont=dict(color='green', size=10),
                #                          textposition='top left',
                #                          showlegend=False))
                # fig.show()


                # 保存日k图
                # plt.figure(figsize=(10, 10))
                # plt.plot(hkmi['date'], hkmi['close'])
                # plt.grid(linewidth=0.5, alpha=0.7)
                # plt.gcf().autofmt_xdate(rotation=45)
                # #plt.gca().xaxis.set_major_locator(MultipleLocator(len(hkmi['close']) / 500))  # 日期最多显示500个
                # plt.title(row['代码'][2:], fontsize=20)
                # plt.show()
                #
                #
                # file_name = f"{END_DATE}_{row['代码'][2:]}.png"
                # plt.savefig(file_name)



        except:
            continue

    print(dfResult)
    #### 结果集输出到csv文件 ####
    file_name = f"{END_DATE}_bottom_stock.csv"
    #dfResult.to_csv(file_name, encoding="gbk", index=False)
    dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)

    #### 登出系统 ####
    bs.logout()
