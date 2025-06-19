import akshare as ak
import pandas as pd
import datetime
import time

# plotly express   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio


import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')


# fig.add_trace(go.Scatter(x=[hkmi['date'].iloc[-1]],
#                          y=[hkmi['close'].iloc[-1]],
#                          text=[hkmi['close'].iloc[-1]],
#                          mode='markers+text',
#                          marker=dict(color='red', size=10),
#                          textfont=dict(color='green', size=10),
#                          textposition='bottom center',
#                          showlegend=False))


if __name__ == '__main__':

    # 抓取某一只ETF基金的趋势图
    hkmi = ak.fund_etf_hist_sina(symbol="sh512530")
    fig = px.line(hkmi, x="date", y="close", title='沪深300红利ETF')
    fig.add_trace(go.Scatter(x=[hkmi['date'].iloc[-1]],
                             y=[hkmi['close'].iloc[-1]],
                             text=[hkmi['date'].iloc[-1]],
                             mode='markers+text',
                             marker=dict(color='red', size=10),
                             textfont=dict(color='green', size=10),
                             textposition='top left',
                             showlegend=False))
    fig.show()



    plt.figure(figsize=(15, 8))
    plt.plot(hkmi['date'], hkmi['close'], label='SHZS')
    # plt.plot(up, label='UP');  # 画图显示
    # plt.plot(mid, label='MID');
    # plt.plot(lower, label='LOW');
    # plt.plot(MA10, label='MA10', linewidth=0.5, alpha=0.7);
    plt.legend()
    plt.grid(linewidth=0.5, alpha=0.7)
    plt.gcf().autofmt_xdate(rotation=45)
    plt.gca().xaxis.set_major_locator(MultipleLocator(len(hkmi['close']) / 30))  # 日期最多显示30个
    plt.title('data SHOW', fontsize=20)
    file_name = f"{END_DATE}_{'sh512530'}.png"
    plt.savefig(file_name)

    plt.show()



