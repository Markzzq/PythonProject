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

START_DATE = '2026-01-01'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')
# END_DATE = '2026-05-31'


## ETF筛选分析 - 抓取表现好的ETF（7日最佳、30日最佳、反转信号、创新高）
## 整合了打分机制，一次遍历完成所有计算
def findGoodTrend(filename):
    start_time = time.time()

    # 读取ETF列表文件
    df_etf_list = pd.read_csv(filename)
    df_etf = df_etf_list[['代码', '名称']]

    # 用于保存当天所有ETF的评分（只保留必要列）
    dfDailyScore = pd.DataFrame(data=None, columns=['代码', '名称', '综合评分'])

    for row_index, row in df_etf.iterrows():
        try:
            time.sleep(0.5)

            etf_code = row['代码']
            etf_name = row['名称']

            etf_hist_df = ak.fund_etf_hist_sina(symbol=etf_code)
            n = etf_hist_df.shape[0]

            if n < 30:
                print(f"ETF: {etf_code} 数据不足异常")
                continue

            CLOSE = etf_hist_df['close'].astype(float)

            allHigh = np.max(CLOSE)
            alllow = np.min(CLOSE)

            today_close = CLOSE[n-1]
            day30_before_close = CLOSE[n-30]
            day7_before_close = CLOSE[n-6]

            # 计算涨幅
            dif30 = (today_close - day30_before_close) / day30_before_close
            dif7 = (today_close - day7_before_close) / day7_before_close
            bias_low = (today_close - alllow) / (allHigh - alllow)

            # 计算技术指标
            K, D, J = utils.cal_KDJ(etf_hist_df)
            dif_macd, dea, macd = MACD(CLOSE)
            MA5 = MA(CLOSE, 5)
            MA10 = MA(CLOSE, 10)
            MA20 = MA(CLOSE, 20)
            MA30 = MA(CLOSE, 30)
            rsi6 = RSI(CLOSE, N=6)
            rsi12 = RSI(CLOSE, N=12)
            rsi24 = RSI(CLOSE, N=24)

            # ========== 灵活打分机制 ==========

            # KDJ评分 - 基于趋势强度和排列程度
            score_kdj = 0
            
            # 多头排列强度评分（J > K > D）
            if J[n-1] > K[n-1] and K[n-1] > D[n-1]:
                jk_diff = J[n-1] - K[n-1]
                kd_diff = K[n-1] - D[n-1]
                score_kdj += (jk_diff + kd_diff) * 0.5  # 差值越大，评分越高
            
            # J线趋势斜率评分（连续上涨）
            if n >= 5:
                j_slope = (J[n-1] - J[n-5]) / 5
                score_kdj += j_slope * 2  # 斜率越大，评分越高
            
            # K线趋势斜率评分
            if n >= 5:
                k_slope = (K[n-1] - K[n-5]) / 5
                score_kdj += k_slope * 1.5
            
            # D线趋势斜率评分
            if n >= 5:
                d_slope = (D[n-1] - D[n-5]) / 5
                score_kdj += d_slope * 1
            
            # J值位置评分（超买得分高，超卖得分低）
            score_kdj += J[n-1] * 0.5  # J值越高，评分越高（反映短线热度）

            # RSI评分 - 基于趋势强度和短线热度
            score_rsi = 0
            
            # RSI值位置评分（超买得分高，超卖得分低）
            score_rsi += rsi6[n-1] * 0.3  # RSI6越高，评分越高
            
            # RSI12趋势斜率评分
            if n >= 5:
                rsi12_slope = (rsi12[n-1] - rsi12[n-5]) / 5
                score_rsi += rsi12_slope * 1

            # MACD评分 - 基于金叉强度和趋势
            score_macd = 0
            
            # DIF与DEA关系评分（金叉强度）
            if dif_macd[n-1] > dea[n-1]:
                dif_dea_diff = dif_macd[n-1] - dea[n-1]
                score_macd += dif_dea_diff * 10  # 差值越大，金叉越强
            
            # DIF和DEA在零轴上方加分
            if dif_macd[n-1] > 0 and dea[n-1] > 0:
                score_macd += dif_macd[n-1] * 5 + dea[n-1] * 3
            
            # MACD柱状图评分 - 反映趋势强度和触底反转
            if n >= 10:
                # MACD柱状图当前值评分
                # 正值时：值越大越好（多头趋势强劲）
                # 负值时：负值越小（绝对值越大）越差，但向上反转潜力加分
                if macd[n-1] > 0:
                    score_macd += macd[n-1] * 5  # 正值越大加分越多
                else:
                    # 负值区域，绝对值越大扣分越多
                    score_macd += macd[n-1] * 2  # 负数会自动扣分
                
                # MACD柱状图触底反转评分
                # 寻找最近的最低点，计算反转力度
                recent_macd = macd[n-10:n]
                min_macd = np.min(recent_macd)
                min_index = np.argmin(recent_macd)
                
                # 如果最低点出现在近期且正在向上反转
                if min_index >= len(recent_macd) - 5:  # 最低点在最近5天内
                    # 从最低点到当前的涨幅
                    reversal_strength = (macd[n-1] - min_macd) / np.abs(min_macd + 0.0001) * 100
                    if reversal_strength > 0:
                        score_macd += reversal_strength * 0.3  # 反转力度加分
                
                # MACD柱状图由负转正交叉评分
                cross_count = 0
                for i in range(n-5, n-1):
                    if macd[i] < 0 and macd[i+1] >= 0:
                        cross_count += 1
                score_macd += cross_count * 10  # 金叉交叉加分
                
                # MACD柱状图连续增长天数评分（区分正负区域）
                growth_days = 0
                for i in range(n-5, n-1):
                    if macd[i+1] > macd[i]:
                        growth_days += 1
                # 如果在负值区域向上增长（反转迹象），额外加分
                if macd[n-1] < 0 and macd[n-6] < 0:
                    if macd[n-1] > macd[n-6]:  # 负值在减小（向上增长）
                        score_macd += growth_days * 5
                else:
                    score_macd += growth_days * 2

            # 均线评分 - 基于多头排列程度和趋势斜率
            score_ma = 0
            
            # 完美多头排列评分（MA5 > MA10 > MA20 > MA30）
            if MA5[n-1] > MA10[n-1] and MA10[n-1] > MA20[n-1] and MA20[n-1] > MA30[n-1]:
                ma5_10_diff = (MA5[n-1] - MA10[n-1]) / MA10[n-1] * 100
                ma10_20_diff = (MA10[n-1] - MA20[n-1]) / MA20[n-1] * 100
                ma20_30_diff = (MA20[n-1] - MA30[n-1]) / MA30[n-1] * 100
                score_ma += (ma5_10_diff + ma10_20_diff + ma20_30_diff) * 2
            
            # 部分多头排列评分
            elif MA5[n-1] > MA10[n-1] and MA10[n-1] > MA20[n-1]:
                ma5_10_diff = (MA5[n-1] - MA10[n-1]) / MA10[n-1] * 100
                ma10_20_diff = (MA10[n-1] - MA20[n-1]) / MA20[n-1] * 100
                score_ma += (ma5_10_diff + ma10_20_diff) * 1
            
            # 均线斜率评分
            if n >= 5:
                ma5_slope = (MA5[n-1] - MA5[n-5]) / MA5[n-5] * 100
                score_ma += ma5_slope * 2
            
            if n >= 10:
                ma10_slope = (MA10[n-1] - MA10[n-10]) / MA10[n-10] * 100
                score_ma += ma10_slope * 1.5
            
            if n >= 20:
                ma20_slope = (MA20[n-1] - MA20[n-20]) / MA20[n-20] * 100
                score_ma += ma20_slope * 1
            
            # 价格在均线上方加分
            if CLOSE[n-1] > MA5[n-1]:
                score_ma += 3
            if CLOSE[n-1] > MA10[n-1]:
                score_ma += 2
            if CLOSE[n-1] > MA20[n-1]:
                score_ma += 2

            # 价格趋势评分 - 基于连续性和涨幅
            score_price = 0
            
            # 连续上涨天数评分
            if n >= 5:
                up_days = 0
                for i in range(n-5, n):
                    if CLOSE[i] > CLOSE[i-1]:
                        up_days += 1
                score_price += up_days * 2
            
            # 近期涨幅评分
            if n >= 7:
                recent_change = (CLOSE[n-1] - CLOSE[n-7]) / CLOSE[n-7] * 100
                score_price += recent_change * 3
            
            # 30日涨幅评分
            score_price += dif30 * 100 * 2
            
            # 波动率评分（低波动加分）
            if n >= 10:
                volatility = np.std(CLOSE[n-10:n]) / np.mean(CLOSE[n-10:n]) * 100
                if volatility < 2:
                    score_price += 5
                elif volatility < 5:
                    score_price += 3
            
            # 历史百分位评分
            if bias_low > 0.8:
                score_price += 10  # 接近历史高位加分
            elif bias_low > 0.5:
                score_price += 5
            elif bias_low < 0.2:
                score_price -= 5  # 接近历史低位扣分

            # 综合评分（加权汇总）
            total_score = score_kdj + score_rsi + score_macd + score_ma + score_price

            # 保存当天评分（只保留综合评分）
            dailyData = {
                '代码': etf_code,
                '名称': etf_name,
                '综合评分': round(total_score, 2)
            }
            dfDailyScore.loc[row_index] = dailyData
            print(f"ETF: {etf_code} {etf_name} 综合评分: {round(total_score, 2)}")

        except Exception as e:
            print(f"处理 {etf_code} 时出错: {e}")
            continue

    end_time = time.time()
    print(f"findGoodTrend运行时间：{end_time - start_time}秒")

    # 将当天评分追加到etf_core_list.csv文件
    updateETFScoreFile(dfDailyScore, filename)


def updateETFScoreFile(dfDailyScore, etf_list_file):
    """
    将当天的综合评分追加到ETF列表文件中
    如果当天日期列已存在则更新数据，否则添加新列
    :param dfDailyScore: 当天的ETF评分DataFrame
    :param etf_list_file: ETF列表文件路径
    """
    try:
        # 读取原始ETF列表文件
        df_original = pd.read_csv(etf_list_file)
        
        # 创建评分字典，方便查找
        score_dict = dfDailyScore.set_index('代码')['综合评分'].to_dict()
        
        # 检查当天日期列是否已存在
        if END_DATE in df_original.columns:
            # 如果已存在，更新该列数据
            df_original[END_DATE] = df_original['代码'].map(score_dict)
            print(f"已更新 {etf_list_file} 中 {END_DATE} 列的数据")
        else:
            # 如果不存在，添加新列
            df_original[END_DATE] = df_original['代码'].map(score_dict)
            print(f"已将 {END_DATE} 列追加到 {etf_list_file}")
        
        # 保存更新后的文件
        df_original.to_csv(etf_list_file, encoding="utf-8-sig", index=False)
        
    except Exception as e:
        print(f"更新ETF评分文件时出错: {e}")


if __name__ == '__main__':
    # 调用ETF筛选函数，使用etf_core_list.csv作为输入
    findGoodTrend('etf_core_list.csv')