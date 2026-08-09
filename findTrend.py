import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time
import utils

from Ashare import *
from MyTT import *

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')


def get_etf_data(etf_code):
    try:
        etf_hist_df = ak.fund_etf_hist_sina(symbol=etf_code)
        return etf_hist_df
    except Exception as e:
        print(f"获取 ETF {etf_code} 数据失败: {e}")
        return None


def to_numpy(arr):
    if hasattr(arr, 'values'):
        return arr.values
    return np.array(arr)

def calculate_all_indicators(df):
    close = df['close'].astype(float).values
    high = df['high'].astype(float).values if 'high' in df.columns else close
    low = df['low'].astype(float).values if 'low' in df.columns else close
    volume = df['volume'].astype(float).values if 'volume' in df.columns else np.ones(len(close))
    open_price = df['open'].astype(float).values if 'open' in df.columns else close

    indicators = {}

    dif_macd, dea, macd = MACD(close)
    indicators['dif_macd'] = to_numpy(dif_macd)
    indicators['dea'] = to_numpy(dea)
    indicators['macd'] = to_numpy(macd)

    K, D, J = utils.cal_KDJ(df)
    indicators['kdj_k'] = K.values
    indicators['kdj_d'] = D.values
    indicators['kdj_j'] = J.values

    rsi6 = RSI(close, N=6)
    rsi12 = RSI(close, N=12)
    rsi24 = RSI(close, N=24)
    indicators['rsi6'] = to_numpy(rsi6)
    indicators['rsi12'] = to_numpy(rsi12)
    indicators['rsi24'] = to_numpy(rsi24)

    upper, mid, lower = BOLL(close)
    indicators['boll_upper'] = to_numpy(upper)
    indicators['boll_mid'] = to_numpy(mid)
    indicators['boll_lower'] = to_numpy(lower)

    bias6, bias12, bias24 = BIAS(close)
    indicators['bias6'] = to_numpy(bias6)
    indicators['bias12'] = to_numpy(bias12)
    indicators['bias24'] = to_numpy(bias24)

    ma5 = MA(close, 5)
    ma10 = MA(close, 10)
    ma20 = MA(close, 20)
    ma30 = MA(close, 30)
    ma60 = MA(close, 60)
    indicators['ma5'] = to_numpy(ma5)
    indicators['ma10'] = to_numpy(ma10)
    indicators['ma20'] = to_numpy(ma20)
    indicators['ma30'] = to_numpy(ma30)
    indicators['ma60'] = to_numpy(ma60)

    cci = CCI(close, high, low)
    indicators['cci'] = to_numpy(cci)

    wr, wr1 = WR(close, high, low)
    indicators['wr'] = to_numpy(wr)
    indicators['wr1'] = to_numpy(wr1)

    pdi, mdi, adx, adxr = DMI(close, high, low)
    indicators['pdi'] = to_numpy(pdi)
    indicators['mdi'] = to_numpy(mdi)
    indicators['adx'] = to_numpy(adx)
    indicators['adxr'] = to_numpy(adxr)

    atr = ATR(close, high, low)
    indicators['atr'] = to_numpy(atr)

    psy, psyma = PSY(close)
    indicators['psy'] = to_numpy(psy)
    indicators['psyma'] = to_numpy(psyma)

    vr = VR(close, volume)
    indicators['vr'] = to_numpy(vr)

    mfi = MFI(close, high, low, volume)
    indicators['mfi'] = to_numpy(mfi)

    obv = OBV(close, volume)
    indicators['obv'] = to_numpy(obv)

    sar = SAR(high, low)
    indicators['sar'] = to_numpy(sar)

    cr, _, _, _, _ = CR(high, low, open_price)
    indicators['cr'] = to_numpy(cr)

    tema = TEMA(close)
    indicators['tema'] = to_numpy(tema)

    cmf = CMF(high, low, close, volume)
    indicators['cmf'] = to_numpy(cmf)

    volratio = VOLRATIO(volume)
    indicators['volratio'] = to_numpy(volratio)

    pricevolume = PRICEVOLUME(close, volume)
    indicators['pricevolume'] = to_numpy(pricevolume)

    trix, trma = TRIX(close)
    indicators['trix'] = to_numpy(trix)
    indicators['trma'] = to_numpy(trma)

    brar_ar, brar_br = BRAR(open_price, close, high, low)
    indicators['brar_ar'] = to_numpy(brar_ar)
    indicators['brar_br'] = to_numpy(brar_br)

    emv, maemv = EMV(high, low, volume)
    indicators['emv'] = to_numpy(emv)
    indicators['maemv'] = to_numpy(maemv)

    mtm, mtmma = MTM(close)
    indicators['mtm'] = to_numpy(mtm)
    indicators['mtmma'] = to_numpy(mtmma)

    roc, maroc = ROC(close)
    indicators['roc'] = to_numpy(roc)
    indicators['maroc'] = to_numpy(maroc)

    return indicators, close, high, low, volume


def calculate_slope(values, n=5):
    if len(values) < n:
        return 0
    if np.isnan(values[-1]) or np.isnan(values[-n]):
        return 0
    return (values[-1] - values[-n]) / n


def calculate_continuous_days(values, compare_func):
    count = 0
    for i in range(len(values) - 1, max(0, len(values) - 10), -1):
        if compare_func(values[i], values[i - 1]):
            count += 1
        else:
            break
    return count


def calculate_score(n, indicators, close, volume):
    scores = {}

    # ============== KDJ 评分 ==============
    # 正向因子：J/K/D值越低，处于超卖区，股票价格越低，得分越低，信号偏向买入
    score_kdj = 0
    j = indicators['kdj_j'][-1]
    k = indicators['kdj_k'][-1]
    d = indicators['kdj_d'][-1]

    if j > k and k > d:
        jk_diff = j - k
        kd_diff = k - d
        score_kdj += (jk_diff + kd_diff) * 0.5

    j_slope = calculate_slope(indicators['kdj_j'], n=5)
    k_slope = calculate_slope(indicators['kdj_k'], n=5)
    d_slope = calculate_slope(indicators['kdj_d'], n=5)
    score_kdj += j_slope * 2
    score_kdj += k_slope * 1.5
    score_kdj += d_slope * 1

    score_kdj += j * 0.3

    if j > 80:
        score_kdj += (j - 80) * 0.5
    elif j < 20:
        score_kdj += (j - 20) * 0.5

    scores['KDJ'] = score_kdj

    # ============== RSI 评分 ==============
    # 正向因子：RSI值越低，处于超卖区，股票价格越低，得分越低，信号偏向买入
    score_rsi = 0
    rsi6_val = indicators['rsi6'][-1]
    rsi12_val = indicators['rsi12'][-1]
    rsi24_val = indicators['rsi24'][-1]

    score_rsi += rsi6_val * 0.3

    rsi12_slope = calculate_slope(indicators['rsi12'], n=5)
    score_rsi += rsi12_slope * 1

    if rsi6_val > rsi12_val and rsi12_val > rsi24_val:
        score_rsi += 5

    if rsi6_val > 70:
        score_rsi += (rsi6_val - 70) * 0.3
    elif rsi6_val < 30:
        score_rsi += (rsi6_val - 30) * 0.3

    scores['RSI'] = score_rsi

    # ============== MACD 评分 ==============
    # 正向因子：DIF/DEA/MACD值越低，下跌趋势越强，股票价格越低，得分越低，信号偏向买入
    score_macd = 0
    dif = indicators['dif_macd'][-1]
    dea_val = indicators['dea'][-1]
    macd_val = indicators['macd'][-1]

    if dif > dea_val:
        dif_dea_diff = dif - dea_val
        score_macd += dif_dea_diff * 10

    if dif > 0 and dea_val > 0:
        score_macd += dif * 5 + dea_val * 3
    elif dif < 0 and dea_val < 0:
        score_macd += dif * 2 + dea_val * 1

    if n >= 10:
        score_macd += macd_val * 5

        recent_macd = indicators['macd'][-10:]
        min_macd = np.min(recent_macd)
        min_index = np.argmin(recent_macd)

        if min_index >= len(recent_macd) - 5 and min_macd != 0:
            reversal_strength = (macd_val - min_macd) / np.abs(min_macd) * 100
            score_macd += reversal_strength * 0.3

        cross_count = 0
        for i in range(n - 5, n - 1):
            if indicators['macd'][i] < 0 and indicators['macd'][i + 1] >= 0:
                cross_count += 1
        score_macd += cross_count * 10

        growth_days = 0
        for i in range(n - 5, n - 1):
            if indicators['macd'][i + 1] > indicators['macd'][i]:
                growth_days += 1

        if macd_val < 0 and indicators['macd'][n - 6] < 0:
            if macd_val > indicators['macd'][n - 6]:
                score_macd += growth_days * 5
        else:
            score_macd += growth_days * 2

    scores['MACD'] = score_macd

    # ============== 均线评分 ==============
    # 趋势因子：均线多头排列（ma5>ma10>ma20>ma30）表示上涨趋势，得分越高，信号偏向买入
    # 均线空头排列表示下跌趋势，得分越低，信号偏向卖出
    score_ma = 0
    ma5_val = indicators['ma5'][-1]
    ma10_val = indicators['ma10'][-1]
    ma20_val = indicators['ma20'][-1]
    ma30_val = indicators['ma30'][-1]
    ma60_val = indicators['ma60'][-1]
    close_val = close[-1]

    if ma5_val > ma10_val and ma10_val > ma20_val and ma20_val > ma30_val:
        ma5_10_diff = (ma5_val - ma10_val) / ma10_val * 100
        ma10_20_diff = (ma10_val - ma20_val) / ma20_val * 100
        ma20_30_diff = (ma20_val - ma30_val) / ma30_val * 100
        score_ma += (ma5_10_diff + ma10_20_diff + ma20_30_diff) * 2

        if ma30_val > ma60_val:
            ma30_60_diff = (ma30_val - ma60_val) / ma60_val * 100
            score_ma += ma30_60_diff * 2
    elif ma5_val > ma10_val and ma10_val > ma20_val:
        ma5_10_diff = (ma5_val - ma10_val) / ma10_val * 100
        ma10_20_diff = (ma10_val - ma20_val) / ma20_val * 100
        score_ma += (ma5_10_diff + ma10_20_diff) * 1

    ma5_slope = calculate_slope(indicators['ma5'], n=5) / (ma5_val + 0.0001) * 100
    ma10_slope = calculate_slope(indicators['ma10'], n=10) / (ma10_val + 0.0001) * 100
    ma20_slope = calculate_slope(indicators['ma20'], n=20) / (ma20_val + 0.0001) * 100
    score_ma += ma5_slope * 2
    score_ma += ma10_slope * 1.5
    score_ma += ma20_slope * 1

    if close_val > ma5_val:
        score_ma += 3
    if close_val > ma10_val:
        score_ma += 2
    if close_val > ma20_val:
        score_ma += 2

    scores['均线'] = score_ma

    # ============== 布林带评分 ==============
    # 正向因子：价格在布林带下轨附近（price_position低），股票价格越低，得分越低，信号偏向买入
    # 价格在布林带上轨附近（price_position高），股票价格越高，得分越高，信号偏向卖出
    score_boll = 0
    boll_width = indicators['boll_upper'][-1] - indicators['boll_lower'][-1]
    if boll_width > 0:
        price_position = (close_val - indicators['boll_lower'][-1]) / boll_width
        score_boll += (price_position - 0.5) * 20

        boll_mid_slope = calculate_slope(indicators['boll_mid'], n=5)
        score_boll += boll_mid_slope * 10

    scores['布林带'] = score_boll

    # ============== CCI 评分 ==============
    # 正向因子：CCI值越低（<-100），处于超卖区，股票价格越低，得分越低，信号偏向买入
    score_cci = 0
    cci_val = indicators['cci'][-1]
    score_cci += cci_val * 0.05

    cci_slope = calculate_slope(indicators['cci'], n=5)
    score_cci += cci_slope * 0.1

    if cci_val > 100:
        score_cci += (cci_val - 100) * 0.03
    elif cci_val < -100:
        score_cci += (cci_val + 100) * 0.03

    scores['CCI'] = score_cci

    # ============== WR 评分 ==============
    # 反向因子：WR值越低（接近-100，超卖区），股票价格越低，但得分越高，信号偏向卖出
    # 注：代码使用(50-wr_val)*0.1计算，wr_val越低得分越高，与正向因子逻辑相反
    score_wr = 0
    wr_val = indicators['wr'][-1]
    score_wr += (50 - wr_val) * 0.1

    wr_slope = calculate_slope(indicators['wr'], n=5)
    score_wr += wr_slope * 0.2

    if wr_val > 80:
        score_wr += (wr_val - 80) * 0.15
    elif wr_val < 20:
        score_wr += (wr_val - 20) * 0.15

    scores['WR'] = score_wr

    # ============== DMI 评分 ==============
    # 趋势因子：PDI>MDI表示上涨趋势，得分越高，信号偏向买入；MDI>PDI表示下跌趋势，得分越低，信号偏向卖出
    # ADX值越高趋势越强，ADX<20表示趋势较弱
    score_dmi = 0
    pdi_val = indicators['pdi'][-1]
    mdi_val = indicators['mdi'][-1]
    adx_val = indicators['adx'][-1]

    if adx_val > 20:
        if pdi_val > mdi_val:
            score_dmi += (pdi_val - mdi_val) * 0.3
        else:
            score_dmi += (pdi_val - mdi_val) * 0.2

    adx_slope = calculate_slope(indicators['adx'], n=5)
    score_dmi += adx_slope * 0.5

    scores['DMI'] = score_dmi

    # ============== ATR 评分 ==============
    # 波动性因子：ATR值反映价格波动幅度，非直接多空因子
    # ATR高于均值表示波动加大，可能伴随趋势加速或反转
    score_atr = 0
    atr_val = indicators['atr'][-1]
    if n >= 20:
        recent_atr_mean = np.mean(indicators['atr'][-20:])
        if recent_atr_mean > 0:
            atr_ratio = atr_val / recent_atr_mean
            score_atr += (atr_ratio - 1) * 10

    scores['ATR'] = score_atr

    # ============== 量能评分 ==============
    # 正向因子：成交量/OBV/MFI值越低，量能萎缩，股票价格越低，得分越低，信号偏向买入
    # MFI低于30为超卖，高于70为超买
    score_volume = 0
    if n >= 5:
        vol5 = to_numpy(MA(volume, 5))
        vol10 = to_numpy(MA(volume, 10))

        vol5_slope = calculate_slope(vol5, n=5)
        vol5_valid = vol5[-20:][~np.isnan(vol5[-20:])]
        vol5_mean = np.mean(vol5_valid) if len(vol5_valid) > 0 else 1
        if vol5_mean > 0:
            score_volume += (vol5_slope / vol5_mean) * 50

        if vol5[-1] > vol10[-1]:
            score_volume += 5

    obv_values = indicators['obv']
    obv_slope = calculate_slope(obv_values, n=5)
    obv_valid = obv_values[-20:][~np.isnan(obv_values[-20:])]
    obv_mean = np.mean(obv_valid) if len(obv_valid) > 0 else 1
    if obv_mean != 0:
        score_volume += (obv_slope / obv_mean) * 50

    mfi_val = indicators['mfi'][-1]
    score_volume += (mfi_val - 50) * 0.2

    scores['量能'] = score_volume

    # ============== 情绪评分 ==============
    # 正向因子：PSY/VR/AR/BR值越低，市场情绪低迷，股票价格越低，得分越低，信号偏向买入
    # PSY低于25为超卖，高于75为超买；VR低于40为超卖，高于350为超买
    score_sentiment = 0
    psy_val = indicators['psy'][-1]
    score_sentiment += (psy_val - 50) * 0.2

    vr_val = indicators['vr'][-1]
    score_sentiment += (vr_val - 100) * 0.05

    brar_ar_val = indicators['brar_ar'][-1]
    brar_br_val = indicators['brar_br'][-1]
    score_sentiment += (brar_ar_val - 100) * 0.02
    score_sentiment += (brar_br_val - 100) * 0.02

    scores['情绪'] = score_sentiment

    # ============== 动量评分 ==============
    # 正向因子：MTM/ROC/TRIX值越低，下跌动量越强，股票价格越低，得分越低，信号偏向买入
    # TRIX金叉（TRIX>TRMA）表示上涨信号，死叉表示下跌信号
    score_momentum = 0
    mtm_val = indicators['mtm'][-1]
    score_momentum += mtm_val * 0.1

    roc_val = indicators['roc'][-1]
    score_momentum += roc_val * 0.1

    trix_val = indicators['trix'][-1]
    trma_val = indicators['trma'][-1]
    score_momentum += (trix_val - trma_val) * 2

    scores['动量'] = score_momentum

    # ============== 价格趋势评分 ==============
    # 趋势因子：综合价格走势判断趋势方向，上涨天数越多、涨幅越大，得分越高，信号偏向卖出
    # 价格接近历史低点（bias_low<0.2），得分越低，信号偏向买入
    score_price = 0

    up_days = calculate_continuous_days(close, lambda x, y: x > y)
    score_price += up_days * 2

    if n >= 7:
        recent_change = (close_val - close[-7]) / close[-7] * 100
        score_price += recent_change * 3

    if n >= 30:
        change_30 = (close_val - close[-30]) / close[-30] * 100
        score_price += change_30 * 2

    if n >= 10:
        volatility = np.std(close[-10:]) / np.mean(close[-10:]) * 100
        if volatility < 2:
            score_price += 3
        elif volatility < 5:
            score_price += 1

    all_high = np.max(close)
    all_low = np.min(close)
    if all_high > all_low:
        bias_low = (close_val - all_low) / (all_high - all_low)
        if bias_low > 0.8:
            score_price += 10
        elif bias_low > 0.5:
            score_price += 5
        elif bias_low < 0.2:
            score_price -= 10

    scores['价格趋势'] = score_price

    return scores


def get_signal(total_score):
    if total_score >= 50:
        return '加仓'
    elif total_score >= 20:
        return '逐步建仓'
    elif total_score >= -10:
        return '持有不动'
    elif total_score >= -30:
        return '逐步减仓'
    else:
        return '减仓'


## ETF筛选分析 - 抓取表现好的ETF（7日最佳、30日最佳、反转信号、创新高）
## 整合了打分机制，一次遍历完成所有计算
def findGoodTrend(filename):
    start_time = time.time()

    df_etf_list = pd.read_csv(filename)
    df_etf = df_etf_list[['代码', '名称']]

    dfDailyScore = pd.DataFrame(data=None, columns=['代码', '名称', '综合评分', '综合信号'])

    all_scores = []
    signal_counts = {}

    for row_index, row in df_etf.iterrows():
        try:
            time.sleep(0.3)

            etf_code = row['代码']
            etf_name = row['名称']

            etf_hist_df = get_etf_data(etf_code)
            if etf_hist_df is None:
                print(f"ETF: {etf_code} 获取数据失败")
                continue

            n = etf_hist_df.shape[0]

            if n < 60:
                print(f"ETF: {etf_code} 数据不足60条，跳过")
                continue

            indicators, close, high, low, volume = calculate_all_indicators(etf_hist_df)

            scores = calculate_score(n, indicators, close, volume)

            total_score = sum(scores.values())

            signal = get_signal(total_score)

            dailyData = {
                '代码': etf_code,
                '名称': etf_name,
                '综合评分': round(total_score, 2),
                '综合信号': signal
            }
            dfDailyScore.loc[row_index] = dailyData

            all_scores.append(total_score)
            signal_counts[signal] = signal_counts.get(signal, 0) + 1

            print(f"ETF: {etf_code} {etf_name} 综合评分: {round(total_score, 2)} 信号: {signal}")

        except Exception as e:
            print(f"处理 {etf_code} 时出错: {e}")
            import traceback
            traceback.print_exc()
            continue

    end_time = time.time()

    print("\n" + "=" * 70)
    print("ETF指标分析汇总")
    print("=" * 70)

    if len(all_scores) > 0:
        print(f"\n评分范围统计:")
        print(f"  最高分: {max(all_scores):.2f}")
        print(f"  最低分: {min(all_scores):.2f}")
        print(f"  平均分: {sum(all_scores)/len(all_scores):.2f}")
        print(f"  评分标准差: {np.std(all_scores):.2f}")

        print(f"\n信号分布统计:")
        for signal, count in sorted(signal_counts.items()):
            percentage = count / len(all_scores) * 100
            print(f"  {signal}: {count} 个 ({percentage:.1f}%)")

        df_summary = dfDailyScore.sort_values('综合评分', ascending=False)
        print(f"\n评分排名前10:")
        print(df_summary.head(10).to_string(index=False))

        print(f"\n评分排名后10:")
        print(df_summary.tail(10).to_string(index=False))

    print(f"\n运行时间：{end_time - start_time:.2f}秒")

    updateETFScoreFile(dfDailyScore, filename)


def updateETFScoreFile(dfDailyScore, etf_list_file):
    try:
        df_original = pd.read_csv(etf_list_file)

        score_dict = dfDailyScore.set_index('代码')['综合评分'].to_dict()
        signal_dict = dfDailyScore.set_index('代码')['综合信号'].to_dict()

        if END_DATE in df_original.columns:
            df_original[END_DATE] = df_original['代码'].map(score_dict)
            print(f"已更新 {etf_list_file} 中 {END_DATE} 列的数据")
        else:
            df_original[END_DATE] = df_original['代码'].map(score_dict)
            print(f"已将 {END_DATE} 列追加到 {etf_list_file}")

        signal_col_name = f"{END_DATE}_信号"
        df_original[signal_col_name] = df_original['代码'].map(signal_dict)

        df_original.to_csv(etf_list_file, encoding="utf-8-sig", index=False)

    except Exception as e:
        print(f"更新ETF评分文件时出错: {e}")


if __name__ == '__main__':
    findGoodTrend('etf_core_list.csv')