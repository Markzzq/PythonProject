import akshare as ak
import pandas as pd
import datetime
import time

# plotly   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go

# matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# 股市行情数据获取和作图 -2
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT


START_DATE = '2025-03-13'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')
Cd = 1.02


if __name__ == '__main__':

    df_etf_list = pd.read_csv('sina_etf_list.csv')
    df_etf = df_etf_list[['代码', '名称']]

    anyData = {'stock': '00', 'name': 'name','OPEN': 'open', 'CLOSE': 'close'}
    dfResult = pd.DataFrame(anyData, index=[0])

    for row_index, row in df_etf.iterrows():
        try:
            #time.sleep(0.5)

            # 方法三
            etf_code = row['代码']
            etf_name = row['名称']


            # 日线数据
            # 抓取某一只ETF基金的趋势图
            hkmi = ak.fund_etf_hist_sina(symbol = etf_code)

            # 计算初级数据  均线策略因子
            CLOSE = hkmi['close']
            MA5 = MA(CLOSE, 5)  # 获取5日均线序列
            MA10 = MA(CLOSE, 10)  # 获取5日均线序列
            MA20 = MA(CLOSE, 20)  # 获取20日均线序列
            MA30 = MA(CLOSE, 30)  # 获取30日均线序列
            MA60 = MA(CLOSE, 60)  # 获取60日均线序列

            N = hkmi.shape[0]

            var1 = False
            var2 = False
            var3 = False
            var4 = False
            var5 = False

            # 获取macd指标
            dif, dea, macd = MACD(CLOSE)

            # macd 趋势向上
            if macd[N - 1] >= macd[N - 2] and macd[N - 2] >= macd[N - 3] and macd[N - 3] >= macd[N - 4]:
                var1 = True

            # 判断5日均线趋势递增 连续3日
            var2 = all(i < j for i, j in zip(MA5[N-4:N-1], MA5[N-4:N-1][1:]))


            varAll = var1 and var2

            if varAll:
                anyData = {'stock': etf_code, 'name': etf_name,'OPEN': hkmi['open'][N-1], 'CLOSE': hkmi['close'][N-1]}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
                print('success add one', etf_code, etf_name)

            # fig = px.line(hkmi, x="date", y="close", title = etf_name)
            # fig.add_trace(go.Scatter(x=[hkmi['date'].iloc[-1]],
            #                          y=[hkmi['close'].iloc[-1]],
            #                          text=[hkmi['date'].iloc[-1]],
            #                          mode='markers+text',
            #                          marker=dict(color='red', size=10),
            #                          textfont=dict(color='green', size=10),
            #                          textposition='top left',
            #                          showlegend=False))
            # fig.show()



        except:
            continue

    print(dfResult)
    #### 结果集输出到csv文件 ####
    file_name = f"{END_DATE}_etf_data.csv"
    #dfResult.to_csv(file_name, encoding="gbk", index=False)
    dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)