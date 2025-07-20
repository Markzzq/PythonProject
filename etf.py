import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time

# 股市行情数据获取和作图 -2
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT

# plotly express   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

START_DATE = '2025-03-13'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')


# fig.add_trace(go.Scatter(x=[hkmi['date'].iloc[-1]],
#                          y=[hkmi['close'].iloc[-1]],
#                          text=[hkmi['close'].iloc[-1]],
#                          mode='markers+text',
#                          marker=dict(color='red', size=10),
#                          textfont=dict(color='green', size=10),
#                          textposition='bottom center',
#                          showlegend=False))

# plt.figure(figsize=(15, 8))
# plt.plot(hkmi['date'], hkmi['close'], label='SHZS')
# # plt.plot(up, label='UP');  # 画图显示
# # plt.plot(mid, label='MID');
# # plt.plot(lower, label='LOW');
# # plt.plot(MA10, label='MA10', linewidth=0.5, alpha=0.7);
# plt.legend()
# plt.grid(linewidth=0.5, alpha=0.7)
# plt.gcf().autofmt_xdate(rotation=45)
# plt.gca().xaxis.set_major_locator(MultipleLocator(len(hkmi['close']) / 30))  # 日期最多显示30个
# plt.title('data SHOW', fontsize=20)
# file_name = f"{END_DATE}_{'sh512530'}.png"
# plt.savefig(file_name)
#
# plt.show()

## 抓取某一只ETF基金的趋势图
def showOneETF(code, name):
    hkmi = ak.fund_etf_hist_sina(symbol=code)
    fig = px.line(hkmi, x="date", y="close", title=name, subtitle=code)
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


# 读取备选列表里的基金并展示出来
def showAllETF():
    # 读取ETF列表
    df_etf_list = pd.read_csv('2025-07-19_topETF.csv')
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


## 抓取被低估但最近表现好的基金
def findGoodETF():
    start_time = time.time()

    df_etf_list = pd.read_csv('sina_etf_list.csv')
    df_etf = df_etf_list[['代码', '名称']]

    # anyData = {'stock': '00', 'name': 'name', 'OPEN': 'open', 'CLOSE': 'close', 'pctChg': 'pctChg', 'turn': 'turn', 'bias': 'ma5bias'}
    # dfResult = pd.DataFrame(anyData, index=[0])
    dfResult = pd.DataFrame(data=None, columns=['代码', '名称', '30日涨幅' '历史百分位'])
    dftop =  pd.DataFrame(data=None, columns=['代码', '名称', '30日涨幅', '历史百分位'])

    for row_index, row in df_etf.iterrows():
        try:
            time.sleep(0.5)

            etf_code = row['代码']  # 是因为抓到的数据带了字母 只取数字
            etf_name = row['名称']

            # fund_etf_hist_df = ak.fund_etf_hist_em(symbol=etf_code, period="daily", start_date="20000101",
            #                                           end_date="20230201", adjust="")

            etf_hist_df = ak.fund_etf_hist_sina(symbol=etf_code)

            n = etf_hist_df.shape[0]

            allHigh = np.max(etf_hist_df['close'])
            alllow = np.min(etf_hist_df['close'])

            today_close = float(etf_hist_df['close'][n-1])
            day30_before_close = float(etf_hist_df['close'][n-30])

            # 30日波动大于10个点
            dif = (today_close - day30_before_close) / day30_before_close

            # 历史百分位
            bias_low = (today_close - alllow) / (allHigh - alllow)

            # 筛选合适的基金
            if dif > 0.1:
                anyData = {'代码': etf_code, '名称': etf_name, '30日涨幅':dif, '历史百分位': bias_low}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
                print("add one ", etf_code, etf_name)

                if bias_low == 1:
                    anyData = {'代码': etf_code, '名称': etf_name, '30日涨幅': dif, '历史百分位': bias_low}
                    df_index = row_index + 1
                    dftop.loc[df_index] = anyData

                    fig = px.line(etf_hist_df, x="date", y="close", title=etf_name, subtitle=etf_code)
                    fig.add_trace(go.Scatter(x=[etf_hist_df['date'].iloc[-1]],
                                             y=[etf_hist_df['close'].iloc[-1]],
                                             text=[etf_hist_df['date'].iloc[-1]],
                                             mode='markers+text',
                                             marker=dict(color='red', size=10),
                                             textfont=dict(color='green', size=10),
                                             textposition='top left',
                                             showlegend=False))
                    fig.show()
                    fig.to_image()


        except:
            continue


    end_time = time.time()
    print(f"findGoodETF运行时间：{end_time - start_time}秒")

    #### 结果集输出到csv文件 ####
    file_name = f"{END_DATE}_findGoodETF.csv"
    top_name = f"{END_DATE}_topETF.csv"

    dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)
    dftop.to_csv(top_name, encoding="utf-8-sig", index=False)






if __name__ == '__main__':

    # showOneETF("sz159695","通信ETF")

    showAllETF()

    # findGoodETF()






