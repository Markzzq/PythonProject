import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time
import utils


# 股市行情数据获取和作图 -2
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT

# plotly express   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

START_DATE = '2025-06-13'
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
def showAllETF(filename):
    # 读取ETF列表
    df_etf_list = pd.read_csv(filename)
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


## 抓取最近表现好的基金（7日最佳 30日最佳） 以及出现反转的基金  以及突破新高的基金
def findGoodETF(filename):
    start_time = time.time()

    df_etf_list = pd.read_csv(filename)
    df_etf = df_etf_list[['代码', '名称']]

    # anyData = {'stock': '00', 'name': 'name', 'OPEN': 'open', 'CLOSE': 'close', 'pctChg': 'pctChg', 'turn': 'turn', 'bias': 'ma5bias'}
    # dfResult = pd.DataFrame(anyData, index=[0])
    dfBest7 = pd.DataFrame(data=None, columns=['代码', '名称', '7日涨幅', '历史百分位'])
    dfBest30 = pd.DataFrame(data=None, columns=['代码', '名称', '30日涨幅', '历史百分位'])
    dfTop = pd.DataFrame(data=None, columns=['代码', '名称', '7日涨幅', '历史百分位'])
    dfReverse = pd.DataFrame(data=None, columns=['代码', '名称', '7日涨幅', '历史百分位'])



    for row_index, row in df_etf.iterrows():
        try:
            time.sleep(0.5)

            etf_code = row['代码']  # 是因为抓到的数据带了字母 只取数字
            etf_name = row['名称']

            # fund_etf_hist_df = ak.fund_etf_hist_em(symbol=etf_code, period="daily", start_date="20000101",
            #                                           end_date="20230201", adjust="")

            etf_hist_df = ak.fund_etf_hist_sina(symbol=etf_code)

            n = etf_hist_df.shape[0]

            CLOSE = etf_hist_df['close'].astype(float)

            allHigh = np.max(CLOSE)
            alllow = np.min(CLOSE)

            today_close = CLOSE[n-1]
            day30_before_close = CLOSE[n-30]
            day7_before_close = CLOSE[n-6]

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

            # 获取macd指标
            dif, dea, macd = MACD(CLOSE)

            # 计算初级数据  均线策略因子
            MA5 = MA(CLOSE, 5)  # 获取5日均线序列
            MA10 = MA(CLOSE, 10)  # 获取5日均线序列
            MA20 = MA(CLOSE, 20)  # 获取20日均线序列
            MA30 = MA(CLOSE, 30)  # 获取30日均线序列
            MA60 = MA(CLOSE, 60)  # 获取60日均线序列

            var1 = False
            var2 = False
            var3 = False
            var4 = False
            var5 = False
            var6 = False

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

            # macd指标开始上移
            if macd[n-1] > macd[n-2] and macd[n-2] > macd[n-3]:
                var5 = True

            # 5日均线出现上移
            if MA5[n-1] > MA5[n-2] and MA5[n-2] > MA5[n-3]:
                var6 = True

            if var4 and var5 and var6:
                anyData = {'代码': etf_code, '名称': etf_name, '7日涨幅':dif7, '历史百分位': bias_low}
                df_index = row_index + 1
                dfReverse.loc[df_index] = anyData
                print("add one in reverse", etf_code, etf_name)



            # 7日波动大于10个点 30日波动大于10个点
            # 同时macd 转正 dif 为正 dea 为正

            tr1 = False
            tr2 = False
            tr3 = False
            tr4 = False

            if MA5[n-1] > MA5[n-2] and MA5[n-2] > MA5[n-3]:
                tr1 = True

            if MA5[n-1] > MA10[n-1] and MA10[n-1] > MA20[n-1]:
                tr2 = True

            if dif[n-1] > 0 and dea[n-1] > 0:
                tr3 = True


            if dif7 > 0.05:
                anyData = {'代码': etf_code, '名称': etf_name, '7日涨幅':dif7, '历史百分位': bias_low}
                df_index = row_index + 1
                dfBest7.loc[df_index] = anyData
                print("add one in best7", etf_code, etf_name)

            if dif30 > 0.10:
                anyData = {'代码': etf_code, '名称': etf_name, '30日涨幅':dif30, '历史百分位': bias_low}
                df_index = row_index + 1
                dfBest30.loc[df_index] = anyData
                print("add one in best30 ", etf_code, etf_name)

            # 创了新高的股票 进 dfTop
            if bias_low == 1:
                anyData = {'代码': etf_code, '名称': etf_name, '7日涨幅':dif7, '历史百分位': bias_low}
                df_index = row_index + 1
                dfTop.loc[df_index] = anyData


        except:
            continue


    end_time = time.time()
    print(f"findGoodETF运行时间：{end_time - start_time}秒")

    #### 结果集输出到csv文件 ####
    file_Reverse = f"{END_DATE}_ETF_Reverse.csv"
    file_Best7 = f"{END_DATE}_ETF_Best7.csv"
    file_Best30 = f"{END_DATE}_ETF_Best30.csv"
    file_Top = f"{END_DATE}_ETF_Top.csv"


    dfReverse.to_csv(file_Reverse, encoding="utf-8-sig", index=False)
    dfBest7.to_csv(file_Best7, encoding="utf-8-sig", index=False)
    dfBest30.to_csv(file_Best30, encoding="utf-8-sig", index=False)
    dfTop.to_csv(file_Top, encoding="utf-8-sig", index=False)






if __name__ == '__main__':

    findGoodETF('sina_etf_list.csv')








