import akshare as ak
import pandas as pd
import datetime
import time

# plotly   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go



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
