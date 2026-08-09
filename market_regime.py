# -*- coding: utf-8 -*-
"""
市场状态检测
============
- ADX趋势强度判定
- 价格vs MA60偏离度
- MA60斜率 = 趋势方向
- 波动率 = 市场情绪
  
返回市场状态: strong_bull / bull / range / bear / strong_bear
"""

import numpy as np
import pandas as pd
from MyTT import MA, STD, ROLLING_SLOPE, DMI


def detect_market_regime(df, ma_period=60, adx_period=14, vol_period=20):
    """
    检测当前市场状态。
    
    Args:
        df: DataFrame，必须包含 Close, High, Low 列
        ma_period: 长期均线周期（默认60）
        adx_period: ADX计算周期（默认14）
        vol_period: 波动率计算周期（默认20）
    
    Returns:
        {
            'regime': 'strong_bull'/'bull'/'range'/'bear'/'strong_bear',
            'adx': ADX值,
            'pdi': PDI值,
            'mdi': MDI值,
            'ma_slope': MA60斜率（每周期变化率）,
            'price_vs_ma60': 价格vs MA60偏离百分比,
            'volatility': 波动率(标准差/均值),
            'trend_direction': 'up'/'down'/'neutral',
            'trend_strength': 趋势强度 0~2,
            'details': 详细数据字典,
        }
    """
    # 兼容大小写列名
    col_map = {col.lower(): col for col in df.columns}
    close = df[col_map.get('close', 'close')].values
    high = df[col_map.get('high', 'high')].values
    low = df[col_map.get('low', 'low')].values

    result = {
        'adx': np.nan,
        'pdi': np.nan,
        'mdi': np.nan,
        'ma_slope': np.nan,
        'price_vs_ma60': np.nan,
        'volatility': np.nan,
        'trend_direction': 'neutral',
        'trend_strength': 0.0,
        'details': {},
    }

    if len(close) < max(ma_period, adx_period, vol_period):
        result['regime'] = 'range'
        return result

    # --- ADX 趋势强度 ---
    try:
        pdi, mdi, adx, adxr = DMI(close, high, low, M1=adx_period, M2=6)
        result['adx'] = float(adx[-1]) if len(adx) > 0 else np.nan
        result['pdi'] = float(pdi[-1]) if len(pdi) > 0 else np.nan
        result['mdi'] = float(mdi[-1]) if len(mdi) > 0 else np.nan
        result['details']['adx'] = result['adx']
        result['details']['pdi'] = result['pdi']
        result['details']['mdi'] = result['mdi']
    except Exception:
        pass

    # --- MA60 偏离度 ---
    ma60 = MA(close, ma_period)
    if len(ma60) > 0 and ma60[-1] > 0 and not np.isnan(ma60[-1]):
        price_vs_ma = (close[-1] - ma60[-1]) / ma60[-1] * 100
        result['price_vs_ma60'] = round(float(price_vs_ma), 2)
        result['details']['price_vs_ma60'] = result['price_vs_ma60']

    # --- MA60 斜率（趋势方向） ---
    if len(close) >= ma_period * 2:
        ma60_slope = ROLLING_SLOPE(ma60, ma_period)
        if len(ma60_slope) > 0 and not np.isnan(ma60_slope[-1]):
            result['ma_slope'] = round(float(ma60_slope[-1]), 6)
            result['details']['ma_slope'] = result['ma_slope']

    # --- 波动率 ---
    if len(close) >= vol_period:
        vol_arr = STD(close, vol_period) / MA(close, vol_period)
        if len(vol_arr) > 0:
            result['volatility'] = round(float(vol_arr[-1]) * 100, 2)
            result['details']['volatility'] = result['volatility']

    # === 判定市场状态 ===
    adx_val = result['adx']
    pdi_val = result['pdi']
    mdi_val = result['mdi']
    slope = result['ma_slope']
    price_vs_ma = result['price_vs_ma60']
    vol = result['volatility']

    is_trending = (not np.isnan(adx_val)) and adx_val > 25

    if not is_trending or np.isnan(adx_val):
        result['regime'] = 'range'
        result['trend_direction'] = 'neutral'
        result['trend_strength'] = 0.0
        return result

    # 趋势方向
    if not np.isnan(pdi_val) and not np.isnan(mdi_val):
        if pdi_val > mdi_val:
            result['trend_direction'] = 'up'
        else:
            result['trend_direction'] = 'down'
    elif not np.isnan(slope):
        result['trend_direction'] = 'up' if slope > 0 else 'down'

    # 趋势强度 (0~2)
    strength = min(2.0, max(0.0, adx_val / 50.0))
    result['trend_strength'] = round(strength, 2)

    # 强弱判定
    if result['trend_direction'] == 'up':
        if strength >= 1.2 and not np.isnan(price_vs_ma) and price_vs_ma > 0:
            result['regime'] = 'strong_bull'
        else:
            result['regime'] = 'bull'
    elif result['trend_direction'] == 'down':
        if strength >= 1.2 and not np.isnan(price_vs_ma) and price_vs_ma < 0:
            result['regime'] = 'strong_bear'
        else:
            result['regime'] = 'bear'
    else:
        result['regime'] = 'range'

    # 高波动叠加
    if not np.isnan(vol) and vol > 3.0:
        if result['regime'] == 'bull':
            result['regime'] = 'strong_bull'
        elif result['regime'] == 'bear':
            result['regime'] = 'strong_bear'

    return result
