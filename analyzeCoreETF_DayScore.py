import pandas as pd
import numpy as np
import datetime
import warnings

import pymysql

try:
    from sqlalchemy import create_engine
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

from MyTT import MACD, KDJ, RSI, BOLL, BIAS, MA, CCI, WR, DMI, ATR, PSY, VR, TRIX, EMV, MFI, OBV, SAR, CR, WAD, TEMA, MIDPRICE, VWAP, CMF, VOLRATIO, PRICEVOLUME


ETF_MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'ZZQ1996zzq@',
    'database': 'etf_daily',
    'charset': 'utf8mb4'
}


INDICATOR_CONFIG = {
    'MACD': {
        'weight': 1.5,
        'category': 'medium',
        'max_score': 2.0,
        'min_score': -2.0,
        'trend_lookback': 3,
        'trend_bonus': 0.2
    },
    'KDJ': {
        'weight': 1.2,
        'category': 'fast',
        'max_score': 2.0,
        'min_score': -2.0,
        'trend_lookback': 2,
        'trend_bonus': 0.1
    },
    'RSI': {
        'weight': 1.0,
        'category': 'fast',
        'max_score': 2.0,
        'min_score': -2.0,
        'trend_lookback': 3,
        'trend_bonus': 0.12
    },
    '布林带': {
        'weight': 0.8,
        'category': 'medium',
        'max_score': 1.5,
        'min_score': -1.5,
        'trend_lookback': 2,
        'trend_bonus': 0.15
    },
    '均线': {
        'weight': 2.0,
        'category': 'slow',
        'max_score': 2.5,
        'min_score': -2.5,
        'trend_lookback': 5,
        'trend_bonus': 0.4
    },
    'CCI': {
        'weight': 0.9,
        'category': 'fast',
        'max_score': 1.5,
        'min_score': -1.5,
        'trend_lookback': 2,
        'trend_bonus': 0.1
    },
    'WR': {
        'weight': 0.8,
        'category': 'fast',
        'max_score': 1.5,
        'min_score': -1.5,
        'trend_lookback': 2,
        'trend_bonus': 0.1
    },
    'DMI': {
        'weight': 1.0,
        'category': 'slow',
        'max_score': 1.5,
        'min_score': -1.5,
        'trend_lookback': 3,
        'trend_bonus': 0.35
    },
    'ATR': {
        'weight': 0.3,
        'category': 'medium',
        'max_score': 0.5,
        'min_score': -0.5,
        'trend_lookback': 1,
        'trend_bonus': 0.05
    },
    'PSY': {
        'weight': 0.5,
        'category': 'fast',
        'max_score': 1.0,
        'min_score': -1.0,
        'trend_lookback': 2,
        'trend_bonus': 0.08
    },
    'VR': {
        'weight': 0.6,
        'category': 'slow',
        'max_score': 1.0,
        'min_score': -1.0,
        'trend_lookback': 3,
        'trend_bonus': 0.3
    },
    'BIAS': {
        'weight': 0.5,
        'category': 'fast',
        'max_score': 1.0,
        'min_score': -1.0,
        'trend_lookback': 2,
        'trend_bonus': 0.08
    },
    'MFI': {
        'weight': 0.9,
        'category': 'fast',
        'max_score': 1.5,
        'min_score': -1.5,
        'trend_lookback': 2,
        'trend_bonus': 0.12
    },
    'SAR': {
        'weight': 0.7,
        'category': 'medium',
        'max_score': 1.0,
        'min_score': -1.0,
        'trend_lookback': 2,
        'trend_bonus': 0.15
    },
    'CR': {
        'weight': 0.6,
        'category': 'slow',
        'max_score': 1.0,
        'min_score': -1.0,
        'trend_lookback': 3,
        'trend_bonus': 0.3
    },
    'TEMA': {
        'weight': 0.7,
        'category': 'medium',
        'max_score': 1.0,
        'min_score': -1.0,
        'trend_lookback': 2,
        'trend_bonus': 0.15
    },
    'VWAP': {
        'weight': 0.6,
        'category': 'medium',
        'max_score': 1.0,
        'min_score': -1.0,
        'trend_lookback': 2,
        'trend_bonus': 0.12
    },
    'CMF': {
        'weight': 0.7,
        'category': 'fast',
        'max_score': 1.0,
        'min_score': -1.0,
        'trend_lookback': 2,
        'trend_bonus': 0.1
    },
    'VOLRATIO': {
        'weight': 0.5,
        'category': 'fast',
        'max_score': 1.0,
        'min_score': -1.0,
        'trend_lookback': 1,
        'trend_bonus': 0.05
    },
    'PRICEVOLUME': {
        'weight': 0.5,
        'category': 'medium',
        'max_score': 1.0,
        'min_score': -1.0,
        'trend_lookback': 2,
        'trend_bonus': 0.12
    }
}


def get_mysql_connection(config):
    return pymysql.connect(
        host=config['host'],
        port=config['port'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset=config['charset']
    )


def get_sqlalchemy_engine(config):
    if not HAS_SQLALCHEMY:
        return None
    return create_engine(
        f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?charset={config['charset']}"
    )


def get_all_etf_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES LIKE 'etf_%'")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables


def get_etf_data(conn, table_name):
    sql = f"SELECT * FROM `{table_name}` ORDER BY date ASC"
    cursor = conn.cursor()
    cursor.execute(sql)
    columns = [desc[0] for desc in cursor.description]
    data = cursor.fetchall()
    cursor.close()
    
    df = pd.DataFrame(data, columns=columns)
    
    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def calculate_indicators(df):
    if len(df) < 120:
        return None
    
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    volume = df['volume'].values
    open_price = df['open'].values if 'open' in df.columns else close
    
    dif, dea, macd = MACD(close, SHORT=12, LONG=26, M=9)
    k, d, j = KDJ(close, high, low, N=9, M1=3, M2=3)
    rsi_6 = RSI(close, N=6)
    rsi_12 = RSI(close, N=12)
    rsi_24 = RSI(close, N=24)
    upper, mid, lower = BOLL(close, N=20, P=2)
    bias_6, bias_12, bias_24 = BIAS(close, L1=6, L2=12, L3=24)
    ma5 = MA(close, 5)
    ma10 = MA(close, 10)
    ma20 = MA(close, 20)
    ma60 = MA(close, 60)
    cci = CCI(close, high, low, N=14)
    wr, wr1 = WR(close, high, low, N=10, N1=6)
    pdi, mdi, adx, adxr = DMI(close, high, low, M1=14, M2=6)
    atr = ATR(close, high, low, N=20)
    psy, psyma = PSY(close, N=12, M=6)
    vr = VR(close, volume, M1=26)
    
    mfi = MFI(close, high, low, volume, N=14)
    obv = OBV(close, volume)
    sar = SAR(high, low, N=4, M=0.02, MMAX=0.2)
    cr, cr_ma1, cr_ma2, cr_ma3, cr_ma4 = CR(high, low, open_price, N=26)
    wad = WAD(high, low, close, open_price)
    tema = TEMA(close, N=12)
    midprice = MIDPRICE(high, low, N=14)
    vwap = VWAP(close, volume, N=20)
    cmf = CMF(high, low, close, volume, N=20)
    volratio = VOLRATIO(volume, N=5)
    pricevolume = PRICEVOLUME(close, volume, N=14)
    
    df['dif'] = dif
    df['dea'] = dea
    df['macd'] = macd
    df['k'] = k
    df['d'] = d
    df['j'] = j
    df['rsi_6'] = rsi_6
    df['rsi_12'] = rsi_12
    df['rsi_24'] = rsi_24
    df['boll_upper'] = upper
    df['boll_mid'] = mid
    df['boll_lower'] = lower
    df['bias_6'] = bias_6
    df['bias_12'] = bias_12
    df['bias_24'] = bias_24
    df['ma5'] = ma5
    df['ma10'] = ma10
    df['ma20'] = ma20
    df['ma60'] = ma60
    df['cci'] = cci
    df['wr'] = wr
    df['wr1'] = wr1
    df['pdi'] = pdi
    df['mdi'] = mdi
    df['adx'] = adx
    df['adxr'] = adxr
    df['atr'] = atr
    df['psy'] = psy
    df['psyma'] = psyma
    df['vr'] = vr
    
    df['mfi'] = mfi
    df['obv'] = obv
    df['sar'] = sar
    df['cr'] = cr
    df['wad'] = wad
    df['tema'] = tema
    df['midprice'] = midprice
    df['vwap'] = vwap
    df['cmf'] = cmf
    df['volratio'] = volratio
    df['pricevolume'] = pricevolume
    
    return df


def analyze_etf(df):
    if df is None or len(df) < 120:
        return None
    
    latest = df.iloc[-1]
    
    key_indicators = [
        'dif', 'dea', 'macd', 'k', 'd', 'j', 'rsi_12',
        'boll_upper', 'boll_mid', 'boll_lower', 'ma5', 'ma10', 'ma20', 'ma60',
        'cci', 'wr', 'pdi', 'mdi', 'adx', 'atr', 'psy', 'vr',
        'mfi', 'sar', 'cr', 'tema', 'vwap', 'cmf', 'volratio', 'pricevolume'
    ]
    for indicator in key_indicators:
        if pd.isna(latest[indicator]) or np.isnan(latest[indicator]):
            return None
    
    scores = {}
    
    def get_trend_bonus(df, col_name, lookback, bonus=0.3, is_positive_trend=True):
        if len(df) < lookback + 1:
            return 0
        recent = df[col_name].iloc[-lookback:]
        prev = df[col_name].iloc[-(lookback + 1):-1]
        if all(pd.notna(recent)) and all(pd.notna(prev)):
            recent_mean = recent.mean()
            prev_mean = prev.mean()
            if is_positive_trend:
                return bonus if recent_mean > prev_mean else 0
            else:
                return bonus if recent_mean < prev_mean else 0
        return 0
    
    def get_cross_bonus(df, fast_col, slow_col, lookback):
        if len(df) < lookback + 1:
            return 0
        recent = df.iloc[-lookback:]
        for i in range(1, len(recent)):
            prev_fast = recent.iloc[i-1][fast_col]
            prev_slow = recent.iloc[i-1][slow_col]
            curr_fast = recent.iloc[i][fast_col]
            curr_slow = recent.iloc[i][slow_col]
            if pd.notna(prev_fast) and pd.notna(prev_slow) and pd.notna(curr_fast) and pd.notna(curr_slow):
                if prev_fast <= prev_slow and curr_fast > curr_slow:
                    return -0.5
                elif prev_fast >= prev_slow and curr_fast < curr_slow:
                    return 0.5
        return 0
    
    macd_signal = '持仓'
    macd_score = 0
    config = INDICATOR_CONFIG['MACD']
    if latest['dif'] > latest['dea'] and latest['dif'] > 0 and latest['dea'] > 0:
        macd_signal = '卖出'
        macd_score = config['max_score']
    elif latest['dif'] > latest['dea'] and latest['dif'] < 0 and latest['dea'] < 0:
        macd_signal = '买入'
        macd_score = config['min_score'] * 0.5
    elif latest['dif'] < latest['dea'] and latest['dif'] > 0 and latest['dea'] > 0:
        macd_signal = '买入'
        macd_score = config['min_score']
    elif latest['dif'] < latest['dea'] and latest['dif'] < 0 and latest['dea'] < 0:
        macd_signal = '卖出'
        macd_score = config['max_score'] * 0.5
    elif latest['macd'] > 0:
        macd_signal = '持仓'
        macd_score = 0.3
    else:
        macd_signal = '持仓'
        macd_score = -0.3
    macd_trend_bonus = get_trend_bonus(df, 'macd', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(macd_score > 0))
    scores['MACD'] = {'得分': round(macd_score + macd_trend_bonus, 2), '信号': macd_signal}
    
    kdj_signal = '持仓'
    kdj_score = 0
    config = INDICATOR_CONFIG['KDJ']
    if latest['j'] < 20 and latest['k'] < 20:
        kdj_signal = '买入'
        kdj_score = config['min_score']
    elif latest['j'] > 80 and latest['k'] > 80:
        kdj_signal = '卖出'
        kdj_score = config['max_score']
    elif 20 <= latest['j'] <= 80:
        kdj_signal = '持仓'
        kdj_score = 0
    kdj_trend_bonus = get_trend_bonus(df, 'j', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(kdj_score > 0))
    scores['KDJ'] = {'得分': round(kdj_score + kdj_trend_bonus, 2), '信号': kdj_signal}
    
    rsi_signal = '持仓'
    rsi_score = 0
    config = INDICATOR_CONFIG['RSI']
    if latest['rsi_12'] < 30:
        rsi_signal = '买入'
        rsi_score = config['min_score']
    elif latest['rsi_12'] > 70:
        rsi_signal = '卖出'
        rsi_score = config['max_score']
    elif 30 <= latest['rsi_12'] <= 70:
        rsi_signal = '持仓'
        rsi_score = 0
    rsi_trend_bonus = get_trend_bonus(df, 'rsi_12', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(rsi_score > 0))
    scores['RSI'] = {'得分': round(rsi_score + rsi_trend_bonus, 2), '信号': rsi_signal}
    
    boll_signal = '持仓'
    boll_score = 0
    config = INDICATOR_CONFIG['布林带']
    price_position = (latest['close'] - latest['boll_lower']) / (latest['boll_upper'] - latest['boll_lower'])
    if price_position < 0.2:
        boll_signal = '买入'
        boll_score = config['min_score']
    elif price_position > 0.8:
        boll_signal = '卖出'
        boll_score = config['max_score']
    elif price_position < 0.3:
        boll_signal = '偏买入'
        boll_score = config['min_score'] * 0.5
    elif price_position > 0.7:
        boll_signal = '偏卖出'
        boll_score = config['max_score'] * 0.5
    else:
        boll_signal = '持仓'
        boll_score = 0
    scores['布林带'] = {'得分': round(boll_score, 2), '信号': boll_signal}
    
    ma_signal = '持仓'
    ma_score = 0
    config = INDICATOR_CONFIG['均线']
    if latest['ma5'] > latest['ma10'] and latest['ma10'] > latest['ma20'] and latest['ma20'] > latest['ma60']:
        ma_signal = '卖出'
        ma_score = config['max_score']
    elif latest['ma5'] < latest['ma10'] and latest['ma10'] < latest['ma20'] and latest['ma20'] < latest['ma60']:
        ma_signal = '买入'
        ma_score = config['min_score']
    elif latest['ma5'] > latest['ma10'] and latest['ma10'] > latest['ma20']:
        ma_signal = '卖出'
        ma_score = config['max_score'] * 0.6
    elif latest['ma5'] < latest['ma10'] and latest['ma10'] < latest['ma20']:
        ma_signal = '买入'
        ma_score = config['min_score'] * 0.6
    elif latest['ma5'] > latest['ma10']:
        ma_signal = '偏卖出'
        ma_score = config['max_score'] * 0.3
    elif latest['ma5'] < latest['ma10']:
        ma_signal = '偏买入'
        ma_score = config['min_score'] * 0.3
    ma_cross_bonus = get_cross_bonus(df, 'ma5', 'ma10', config['trend_lookback'])
    scores['均线'] = {'得分': round(ma_score + ma_cross_bonus, 2), '信号': ma_signal}
    
    cci_signal = '持仓'
    cci_score = 0
    config = INDICATOR_CONFIG['CCI']
    if latest['cci'] < -100:
        cci_signal = '买入'
        cci_score = config['min_score']
    elif latest['cci'] > 100:
        cci_signal = '卖出'
        cci_score = config['max_score']
    elif latest['cci'] < -50:
        cci_signal = '偏买入'
        cci_score = config['min_score'] * 0.5
    elif latest['cci'] > 50:
        cci_signal = '偏卖出'
        cci_score = config['max_score'] * 0.5
    else:
        cci_signal = '持仓'
        cci_score = 0
    cci_trend_bonus = get_trend_bonus(df, 'cci', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(cci_score > 0))
    scores['CCI'] = {'得分': round(cci_score + cci_trend_bonus, 2), '信号': cci_signal}
    
    wr_signal = '持仓'
    wr_score = 0
    config = INDICATOR_CONFIG['WR']
    if latest['wr'] > 80:
        wr_signal = '买入'
        wr_score = config['min_score']
    elif latest['wr'] < 20:
        wr_signal = '卖出'
        wr_score = config['max_score']
    elif latest['wr'] > 60:
        wr_signal = '偏买入'
        wr_score = config['min_score'] * 0.5
    elif latest['wr'] < 40:
        wr_signal = '偏卖出'
        wr_score = config['max_score'] * 0.5
    else:
        wr_signal = '持仓'
        wr_score = 0
    wr_trend_bonus = get_trend_bonus(df, 'wr', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(wr_score > 0))
    scores['WR'] = {'得分': round(wr_score + wr_trend_bonus, 2), '信号': wr_signal}
    
    dmi_signal = '持仓'
    dmi_score = 0
    config = INDICATOR_CONFIG['DMI']
    if latest['pdi'] > latest['mdi'] and latest['adx'] > 20:
        dmi_signal = '卖出'
        dmi_score = config['max_score']
    elif latest['pdi'] < latest['mdi'] and latest['adx'] > 20:
        dmi_signal = '买入'
        dmi_score = config['min_score']
    elif latest['pdi'] > latest['mdi'] and latest['adx'] <= 20:
        dmi_signal = '偏卖出'
        dmi_score = config['max_score'] * 0.5
    elif latest['pdi'] < latest['mdi'] and latest['adx'] <= 20:
        dmi_signal = '偏买入'
        dmi_score = config['min_score'] * 0.5
    else:
        dmi_signal = '持仓'
        dmi_score = 0
    dmi_trend_bonus = get_trend_bonus(df, 'adx', config['trend_lookback'], config['trend_bonus'], is_positive_trend=True)
    scores['DMI'] = {'得分': round(dmi_score + dmi_trend_bonus, 2), '信号': dmi_signal}
    
    atr_signal = '持仓'
    atr_score = 0
    config = INDICATOR_CONFIG['ATR']
    recent_atr = df['atr'].tail(20).mean()
    price_range = latest['high'] - latest['low']
    if price_range > recent_atr * 1.5:
        atr_signal = '波动大'
        atr_score = config['max_score']
    elif price_range < recent_atr * 0.5:
        atr_signal = '波动小'
        atr_score = config['min_score']
    else:
        atr_signal = '正常'
        atr_score = 0
    scores['ATR'] = {'得分': round(atr_score, 2), '信号': atr_signal}
    
    psy_signal = '持仓'
    psy_score = 0
    config = INDICATOR_CONFIG['PSY']
    if latest['psy'] < 25:
        psy_signal = '买入'
        psy_score = config['min_score']
    elif latest['psy'] > 75:
        psy_signal = '卖出'
        psy_score = config['max_score']
    elif latest['psy'] < 40:
        psy_signal = '偏买入'
        psy_score = config['min_score'] * 0.5
    elif latest['psy'] > 60:
        psy_signal = '偏卖出'
        psy_score = config['max_score'] * 0.5
    else:
        psy_signal = '持仓'
        psy_score = 0
    psy_trend_bonus = get_trend_bonus(df, 'psy', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(psy_score > 0))
    scores['PSY'] = {'得分': round(psy_score + psy_trend_bonus, 2), '信号': psy_signal}
    
    vr_signal = '持仓'
    vr_score = 0
    config = INDICATOR_CONFIG['VR']
    if latest['vr'] < 70:
        vr_signal = '买入'
        vr_score = config['min_score']
    elif latest['vr'] > 150:
        vr_signal = '卖出'
        vr_score = config['max_score']
    elif latest['vr'] < 100:
        vr_signal = '偏买入'
        vr_score = config['min_score'] * 0.5
    elif latest['vr'] > 120:
        vr_signal = '偏卖出'
        vr_score = config['max_score'] * 0.5
    else:
        vr_signal = '持仓'
        vr_score = 0
    vr_trend_bonus = get_trend_bonus(df, 'vr', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(vr_score > 0))
    scores['VR'] = {'得分': round(vr_score + vr_trend_bonus, 2), '信号': vr_signal}
    
    bias_signal = '持仓'
    bias_score = 0
    config = INDICATOR_CONFIG['BIAS']
    if latest['bias_6'] < -5:
        bias_signal = '买入'
        bias_score = config['min_score']
    elif latest['bias_6'] > 5:
        bias_signal = '卖出'
        bias_score = config['max_score']
    elif latest['bias_6'] < -2:
        bias_signal = '偏买入'
        bias_score = config['min_score'] * 0.5
    elif latest['bias_6'] > 2:
        bias_signal = '偏卖出'
        bias_score = config['max_score'] * 0.5
    else:
        bias_signal = '持仓'
        bias_score = 0
    bias_trend_bonus = get_trend_bonus(df, 'bias_6', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(bias_score > 0))
    scores['BIAS'] = {'得分': round(bias_score + bias_trend_bonus, 2), '信号': bias_signal}
    
    mfi_signal = '持仓'
    mfi_score = 0
    config = INDICATOR_CONFIG['MFI']
    if latest['mfi'] < 20:
        mfi_signal = '买入'
        mfi_score = config['min_score']
    elif latest['mfi'] > 80:
        mfi_signal = '卖出'
        mfi_score = config['max_score']
    elif latest['mfi'] < 35:
        mfi_signal = '偏买入'
        mfi_score = config['min_score'] * 0.5
    elif latest['mfi'] > 65:
        mfi_signal = '偏卖出'
        mfi_score = config['max_score'] * 0.5
    else:
        mfi_signal = '持仓'
        mfi_score = 0
    mfi_trend_bonus = get_trend_bonus(df, 'mfi', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(mfi_score > 0))
    scores['MFI'] = {'得分': round(mfi_score + mfi_trend_bonus, 2), '信号': mfi_signal}
    
    sar_signal = '持仓'
    sar_score = 0
    config = INDICATOR_CONFIG['SAR']
    if latest['close'] > latest['sar']:
        sar_signal = '卖出'
        sar_score = config['max_score']
    else:
        sar_signal = '买入'
        sar_score = config['min_score']
    sar_trend_bonus = get_trend_bonus(df, 'sar', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(sar_score > 0))
    scores['SAR'] = {'得分': round(sar_score + sar_trend_bonus, 2), '信号': sar_signal}
    
    cr_signal = '持仓'
    cr_score = 0
    config = INDICATOR_CONFIG['CR']
    if latest['cr'] < 100:
        cr_signal = '买入'
        cr_score = config['min_score']
    elif latest['cr'] > 300:
        cr_signal = '卖出'
        cr_score = config['max_score']
    elif latest['cr'] < 150:
        cr_signal = '偏买入'
        cr_score = config['min_score'] * 0.5
    elif latest['cr'] > 200:
        cr_signal = '偏卖出'
        cr_score = config['max_score'] * 0.5
    else:
        cr_signal = '持仓'
        cr_score = 0
    cr_trend_bonus = get_trend_bonus(df, 'cr', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(cr_score > 0))
    scores['CR'] = {'得分': round(cr_score + cr_trend_bonus, 2), '信号': cr_signal}
    
    tema_signal = '持仓'
    tema_score = 0
    config = INDICATOR_CONFIG['TEMA']
    tema_diff = latest['tema'] - latest['close']
    if tema_diff > 0:
        tema_signal = '卖出'
        tema_score = config['max_score']
    else:
        tema_signal = '买入'
        tema_score = config['min_score']
    tema_trend_bonus = get_trend_bonus(df, 'tema', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(tema_score > 0))
    scores['TEMA'] = {'得分': round(tema_score + tema_trend_bonus, 2), '信号': tema_signal}
    
    vwap_signal = '持仓'
    vwap_score = 0
    config = INDICATOR_CONFIG['VWAP']
    if latest['close'] > latest['vwap']:
        vwap_signal = '卖出'
        vwap_score = config['max_score']
    else:
        vwap_signal = '买入'
        vwap_score = config['min_score']
    scores['VWAP'] = {'得分': round(vwap_score, 2), '信号': vwap_signal}
    
    cmf_signal = '持仓'
    cmf_score = 0
    config = INDICATOR_CONFIG['CMF']
    if latest['cmf'] > 0.1:
        cmf_signal = '卖出'
        cmf_score = config['max_score']
    elif latest['cmf'] < -0.1:
        cmf_signal = '买入'
        cmf_score = config['min_score']
    elif latest['cmf'] > 0.05:
        cmf_signal = '偏卖出'
        cmf_score = config['max_score'] * 0.5
    elif latest['cmf'] < -0.05:
        cmf_signal = '偏买入'
        cmf_score = config['min_score'] * 0.5
    else:
        cmf_signal = '持仓'
        cmf_score = 0
    cmf_trend_bonus = get_trend_bonus(df, 'cmf', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(cmf_score > 0))
    scores['CMF'] = {'得分': round(cmf_score + cmf_trend_bonus, 2), '信号': cmf_signal}
    
    volratio_signal = '持仓'
    volratio_score = 0
    config = INDICATOR_CONFIG['VOLRATIO']
    if latest['volratio'] > 2:
        volratio_signal = '卖出'
        volratio_score = config['max_score']
    elif latest['volratio'] < 0.5:
        volratio_signal = '买入'
        volratio_score = config['min_score']
    elif latest['volratio'] > 1.5:
        volratio_signal = '偏卖出'
        volratio_score = config['max_score'] * 0.5
    elif latest['volratio'] < 0.7:
        volratio_signal = '偏买入'
        volratio_score = config['min_score'] * 0.5
    else:
        volratio_signal = '持仓'
        volratio_score = 0
    scores['VOLRATIO'] = {'得分': round(volratio_score, 2), '信号': volratio_signal}
    
    pv_signal = '持仓'
    pv_score = 0
    config = INDICATOR_CONFIG['PRICEVOLUME']
    if latest['pricevolume'] > 70:
        pv_signal = '卖出'
        pv_score = config['max_score']
    elif latest['pricevolume'] < 30:
        pv_signal = '买入'
        pv_score = config['min_score']
    elif latest['pricevolume'] > 60:
        pv_signal = '偏卖出'
        pv_score = config['max_score'] * 0.5
    elif latest['pricevolume'] < 40:
        pv_signal = '偏买入'
        pv_score = config['min_score'] * 0.5
    else:
        pv_signal = '持仓'
        pv_score = 0
    pv_trend_bonus = get_trend_bonus(df, 'pricevolume', config['trend_lookback'], config['trend_bonus'], is_positive_trend=(pv_score > 0))
    scores['PRICEVOLUME'] = {'得分': round(pv_score + pv_trend_bonus, 2), '信号': pv_signal}
    
    total_score = 0
    total_weight = 0
    weighted_scores = {}
    for indicator_name, score_info in scores.items():
        if indicator_name in INDICATOR_CONFIG:
            weight = INDICATOR_CONFIG[indicator_name]['weight']
            total_score += score_info['得分'] * weight
            total_weight += weight
            weighted_scores[indicator_name] = {
                '原始得分': score_info['得分'],
                '权重': weight,
                '加权得分': round(score_info['得分'] * weight, 2),
                '信号': score_info['信号']
            }
        else:
            total_score += score_info['得分']
            total_weight += 1
            weighted_scores[indicator_name] = {
                '原始得分': score_info['得分'],
                '权重': 1.0,
                '加权得分': round(score_info['得分'], 2),
                '信号': score_info['信号']
            }
    
    if total_score >= 18:
        final_signal = '强烈卖出'
    elif total_score >= 8:
        final_signal = '卖出'
    elif total_score >= -8:
        final_signal = '持仓'
    elif total_score >= -18:
        final_signal = '买入'
    else:
        final_signal = '强烈买入'
    
    result = {
        '日期': latest['date'].strftime('%Y-%m-%d') if hasattr(latest['date'], 'strftime') else str(latest['date'])[:10],
        'ETF代码': latest.get('etf_code', ''),
        'ETF名称': latest.get('etf_name', ''),
        '收盘价': round(float(latest['close']), 3),
        '成交量': int(latest['volume']),
        '综合评分': round(total_score, 2),
        '综合信号': final_signal,
        '指标得分': weighted_scores
    }
    
    return result


def analyze_all_etfs():
    print("=" * 70)
    print("ETF指标分析工具")
    print("=" * 70)
    print(f"数据库: {ETF_MYSQL_CONFIG['host']}:{ETF_MYSQL_CONFIG['port']}/{ETF_MYSQL_CONFIG['database']}")
    print(f"分析时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    conn = None
    
    try:
        conn = get_mysql_connection(ETF_MYSQL_CONFIG)
        print("数据库连接成功\n")
        
        tables = get_all_etf_tables(conn)
        print(f"共发现 {len(tables)} 个ETF数据表")
        
        results = []
        for table in tables:
            code = table[4:]
            print(f"\n处理: {code}")
            
            try:
                df = get_etf_data(conn, table)
                if len(df) < 120:
                    print(f"  数据不足120条，跳过")
                    continue
                
                df_with_indicators = calculate_indicators(df)
                if df_with_indicators is None:
                    print(f"  指标计算失败，跳过")
                    continue
                
                analysis_result = analyze_etf(df_with_indicators)
                if analysis_result:
                    results.append(analysis_result)
                    print(f"  分析完成: {analysis_result['ETF名称']} - 信号: {analysis_result['综合信号']} - 评分: {analysis_result['综合评分']}")
                else:
                    print(f"  指标值包含NaN，跳过")
            
            except Exception as e:
                print(f"  处理异常: {e}")
                continue
        
        conn.close()
        
        if not results:
            print("\n没有有效的分析结果")
            return
        
        csv_rows = []
        for result in results:
            row = {
                'ETF名称': result['ETF名称'],
                'ETF代码': result['ETF代码'],
                '收盘价': result['收盘价'],
                '成交量': result['成交量'],
                '综合评分': result['综合评分'],
                '综合信号': result['综合信号']
            }
            
            for indicator_name, indicator_data in result['指标得分'].items():
                row[f'{indicator_name}加权得分'] = indicator_data['加权得分']
                row[f'{indicator_name}信号'] = indicator_data['信号']
            
            csv_rows.append(row)
        
        df_csv = pd.DataFrame(csv_rows)
        
        df_summary = df_csv[['ETF名称', 'ETF代码', '收盘价', '综合评分', '综合信号']].copy()
        df_summary = df_summary.sort_values('综合评分', ascending=False)
        
        print("\n" + "=" * 70)
        print("ETF指标分析汇总")
        print("=" * 70)
        print(df_summary.to_string(index=False))
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"etf_analysis_{timestamp}.csv"
        df_csv.to_csv(filename, encoding='utf-8-sig', index=False)
        print(f"\n分析结果已保存至: {filename}")
        
        print("\n" + "=" * 70)
        signal_counts = df_summary['综合信号'].value_counts()
        print("信号分布统计:")
        for signal, count in signal_counts.items():
            print(f"  {signal}: {count} 个")
        print("=" * 70)
        
        all_scores = [r['综合评分'] for r in results]
        max_theoretical = sum(c['max_score'] * c['weight'] for c in INDICATOR_CONFIG.values())
        min_theoretical = sum(c['min_score'] * c['weight'] for c in INDICATOR_CONFIG.values())
        print(f"\n评分范围统计:")
        print(f"  理论最高分: {max_theoretical:.2f}")
        print(f"  理论最低分: {min_theoretical:.2f}")
        print(f"  实际最高分: {max(all_scores):.2f}")
        print(f"  实际最低分: {min(all_scores):.2f}")
        print(f"  平均分: {sum(all_scores)/len(all_scores):.2f}")
        
        return df_summary
        
    except Exception as e:
        if conn:
            try:
                conn.close()
            except:
                pass
        print(f"\n执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    warnings.filterwarnings('ignore', category=UserWarning)
    analyze_all_etfs()
