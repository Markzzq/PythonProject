"""
ETF 每日评分分析工具 v2.0
=======================
升级内容：
- 使用声明式打分引擎 (scoring_engine.py)
- 市场状态自适应阈值 (market_regime.py)
- ETF特有指标加分（折溢价率、资金流向、份额变化）
- NaN柔性处理：单个指标缺失不压整只ETF
- 买卖方向分离的Trend Bonus
"""

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

from MyTT import MACD, KDJ, RSI, BOLL, BIAS, MA, CCI, WR, DMI, ATR, PSY, VR, MFI, OBV, SAR, CR, WAD, TEMA, MIDPRICE, VWAP, CMF, VOLRATIO, PRICEVOLUME, CROSS
from scoring_engine import calculate_total_score, calculate_trend_bonus
from market_regime import detect_market_regime


def try_import_akshare():
    """尝试导入 akshare，失败返回 None"""
    try:
        import akshare as ak
        return ak
    except ImportError:
        return None


def get_etf_premium_discount(etf_code, trade_date=None):
    """
    获取ETF折溢价率。
    折溢价率 = (市场价 - IOPV) / IOPV * 100
    > 0 → 溢价（市场价高于净值）, < 0 → 折价（市场价低于净值）
    获取失败返回 None
    """
    ak = try_import_akshare()
    if ak is None:
        return None
    try:
        df = ak.fund_etf_fund_info_em(
            fund=etf_code,
            start_date=trade_date or '20200101',
            end_date=trade_date or '20991231',
        )
        if df is not None and len(df) > 0:
            col_candidates = ['折溢价率', 'discount_rate', '折溢价']
            for col in col_candidates:
                if col in df.columns:
                    return round(float(df[col].iloc[-1]), 2)
        return None
    except Exception:
        return None


def get_etf_fund_flow(etf_code, trade_date=None):
    """
    获取ETF资金净流入/流出。
    返回: {'net_flow': 净流入(万元), 'turnover_rate': 换手率(%)}，失败返回 None
    """
    ak = try_import_akshare()
    if ak is None:
        return None
    try:
        df = ak.fund_etf_fund_info_em(
            fund=etf_code,
            start_date=trade_date or '20200101',
            end_date=trade_date or '20991231',
        )
        if df is not None and len(df) > 0:
            result = {}
            for col in ['资金净流入', 'net_inflow', '净流入']:
                if col in df.columns:
                    result['net_flow'] = round(float(df[col].iloc[-1]), 2)
                    break
            for col in ['换手率', 'turnover_rate']:
                if col in df.columns:
                    result['turnover_rate'] = round(float(df[col].iloc[-1]), 2)
                    break
            return result if result else None
        return None
    except Exception:
        return None


def get_etf_share_change(etf_code, days=5):
    """
    获取ETF份额变化率。
    返回: {'share_change_ratio': 份额变化率(%), 'current_shares': 当前份额(万份), 'days': 统计周期}，失败返回 None
    """
    ak = try_import_akshare()
    if ak is None:
        return None
    try:
        df = ak.fund_etf_share_em()
        if df is None or len(df) == 0:
            return None
        code_col = None
        for col in ['基金代码', 'code', '证券代码']:
            if col in df.columns:
                code_col = col
                break
        if code_col is None:
            return None
        etf_code_str = str(etf_code)
        mask = df[code_col].astype(str) == etf_code_str
        matched = df[mask].tail(days)
        if len(matched) < 2:
            return None
        share_col = None
        for col in ['基金份额', 'shares', '份额']:
            if col in df.columns:
                share_col = col
                break
        if share_col is None:
            return None
        shares = matched[share_col].astype(float).values
        change_ratio = (shares[-1] - shares[0]) / shares[0] * 100 if shares[0] != 0 else 0.0
        return {
            'share_change_ratio': round(float(change_ratio), 2),
            'current_shares': round(float(shares[-1]), 2),
            'days': days,
        }
    except Exception:
        return None


def get_etf_specific_indicators(etf_code, trade_date=None):
    """
    聚合获取ETF特有指标。
    返回: {premium_discount_rate, net_fund_flow, turnover_rate, share_change_ratio, current_shares}
    各项在取数失败时为 None
    """
    result = {
        'premium_discount_rate': None,
        'net_fund_flow': None,
        'turnover_rate': None,
        'share_change_ratio': None,
        'current_shares': None,
    }
    pd_rate = get_etf_premium_discount(etf_code, trade_date)
    if pd_rate is not None:
        result['premium_discount_rate'] = pd_rate
    flow = get_etf_fund_flow(etf_code, trade_date)
    if flow:
        result['net_fund_flow'] = flow.get('net_flow')
        result['turnover_rate'] = flow.get('turnover_rate')
    shares = get_etf_share_change(etf_code, days=5)
    if shares:
        result['share_change_ratio'] = shares.get('share_change_ratio')
        result['current_shares'] = shares.get('current_shares')
    return result


def score_etf_specific(indicators):
    """
    对ETF特有指标打分。
    折溢价率: 折价(-)加分, 溢价(+)减分
    资金流向: 正流入加分, 负流入减分
    份额变化: 份额增加加分, 份额减少减分
    """
    score = 0.0
    details = {}

    # 折溢价率打分
    pd_rate = indicators.get('premium_discount_rate')
    if pd_rate is not None and not np.isnan(pd_rate):
        if pd_rate < -1.0:        sub = 2.0
        elif pd_rate < -0.5:      sub = 1.0
        elif pd_rate > 1.0:       sub = -2.0
        elif pd_rate > 0.5:       sub = -1.0
        else:                       sub = 0.0
        details['premium_discount'] = {'value': pd_rate, 'score': sub}
        score += sub

    # 资金流向打分
    net_flow = indicators.get('net_fund_flow')
    if net_flow is not None and not np.isnan(net_flow):
        if net_flow > 10000:        sub = 3.0
        elif net_flow > 1000:       sub = 1.5
        elif net_flow < -10000:     sub = -3.0
        elif net_flow < -1000:      sub = -1.5
        else:                         sub = 0.0
        details['net_fund_flow'] = {'value': net_flow, 'score': sub}
        score += sub

    # 份额变化打分
    sc_ratio = indicators.get('share_change_ratio')
    if sc_ratio is not None and not np.isnan(sc_ratio):
        if sc_ratio > 5:            sub = 3.0
        elif sc_ratio > 2:          sub = 1.5
        elif sc_ratio < -5:         sub = -3.0
        elif sc_ratio < -2:         sub = -1.5
        else:                         sub = 0.0
        details['share_change'] = {'value': sc_ratio, 'score': sub}
        score += sub

    return {'score': round(score, 2), 'details': details}


ETF_MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'ZZQ1996zzq@',
    'database': 'etf_daily',
    'charset': 'utf8mb4'
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
    
    # 统一列名为小写，兼容大小写差异
    rename_map = {}
    for col in df.columns:
        if col.lower() != col:
            rename_map[col] = col.lower()
    if rename_map:
        df = df.rename(columns=rename_map)
    
    return df


def calculate_indicators(df):
    """计算全部技术指标，写入DataFrame"""
    if len(df) < 120:
        return None
    
    # 兼容列名大小写
    col_map = {}
    for col in df.columns:
        col_map[col.lower()] = col
    
    close = df[col_map.get('close', 'close')].values
    high = df[col_map.get('high', 'high')].values
    low = df[col_map.get('low', 'low')].values
    volume = df[col_map.get('volume', 'volume')].values
    open_price = df[col_map.get('open', 'open')].values if 'open' in col_map else close
    
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
    
    df['dif'] = dif; df['dea'] = dea; df['macd'] = macd
    df['k'] = k; df['d'] = d; df['j'] = j
    df['rsi_6'] = rsi_6; df['rsi_12'] = rsi_12; df['rsi_24'] = rsi_24
    df['boll_upper'] = upper; df['boll_mid'] = mid; df['boll_lower'] = lower
    df['bias_6'] = bias_6; df['bias_12'] = bias_12; df['bias_24'] = bias_24
    df['ma5'] = ma5; df['ma10'] = ma10; df['ma20'] = ma20; df['ma60'] = ma60
    df['cci'] = cci; df['wr'] = wr; df['wr1'] = wr1
    df['pdi'] = pdi; df['mdi'] = mdi; df['adx'] = adx; df['adxr'] = adxr
    df['atr'] = atr; df['psy'] = psy; df['psyma'] = psyma; df['vr'] = vr
    df['mfi'] = mfi; df['obv'] = obv; df['sar'] = sar; df['cr'] = cr
    df['wad'] = wad; df['tema'] = tema; df['midprice'] = midprice
    df['vwap'] = vwap; df['cmf'] = cmf; df['volratio'] = volratio
    df['pricevolume'] = pricevolume
    
    return df


def extract_indicator_values(df):
    """
    从计算结果DataFrame中提取指标最新值，转换为打分引擎需要的格式。
    
    返回: {指标名: 值} 字典
    """
    if df is None or len(df) < 120:
        return {}

    latest = df.iloc[-1]

    values = {}

    # --- 趋势类 ---
    # MACD DIF 位置
    if pd.notna(latest.get('dif')) and not np.isnan(latest['dif']):
        values['MACD_DIF位置'] = float(latest['dif'])

    # MACD 金叉死叉: 1=金叉, -1=死叉, 0=无（使用 MyTT CROSS）
    if len(df) >= 2:
        dif_vals = df['dif'].values
        dea_vals = df['dea'].values
        if pd.notna(dif_vals[-1]) and pd.notna(dea_vals[-1]):
            cross_macd = CROSS(dif_vals, dea_vals)[-1]
            if cross_macd:
                values['MACD金叉死叉'] = 1 if dif_vals[-1] > dea_vals[-1] else -1
            else:
                values['MACD金叉死叉'] = 0

    # MA5_MA10 金叉死叉（使用 MyTT CROSS）
    if len(df) >= 2:
        ma5_vals = df['ma5'].values
        ma10_vals = df['ma10'].values
        if all(pd.notna(x) and not np.isnan(x) for x in [ma5_vals[-1], ma10_vals[-1]]):
            cross_ma = CROSS(ma5_vals, ma10_vals)[-1]
            if cross_ma:
                values['MA5_MA10金叉死叉'] = 1 if ma5_vals[-1] > ma10_vals[-1] else -1
            else:
                values['MA5_MA10金叉死叉'] = 0

    # MA 多头排列: 1=多头, -1=空头, 0=交织
    if all(k in df.columns and pd.notna(latest[k]) and not np.isnan(latest[k])
           for k in ['ma5', 'ma10', 'ma20', 'ma60']):
        ma5, ma10, ma20, ma60 = latest['ma5'], latest['ma10'], latest['ma20'], latest['ma60']
        if ma5 > ma10 > ma20 > ma60:
            values['MA多头排列'] = 1
        elif ma5 < ma10 < ma20 < ma60:
            values['MA多头排列'] = -1
        elif ma5 > ma10 > ma20:
            values['MA多头排列'] = 0.5
        elif ma5 < ma10 < ma20:
            values['MA多头排列'] = -0.5
        else:
            values['MA多头排列'] = 0

    # 价格 vs MA20
    if pd.notna(latest.get('ma20')) and not np.isnan(latest['ma20']):
        values['价格vs MA20'] = round(
            (latest['close'] - latest['ma20']) / latest['ma20'] * 100, 2
        )

    # 价格 vs MA60
    if pd.notna(latest.get('ma60')) and not np.isnan(latest['ma60']):
        values['价格vs MA60'] = round(
            (latest['close'] - latest['ma60']) / latest['ma60'] * 100, 2
        )

    # --- 动量类 ---
    if pd.notna(latest.get('rsi_12')) and not np.isnan(latest['rsi_12']):
        values['RSI(14)'] = float(latest['rsi_12'])

    if pd.notna(latest.get('k')) and not np.isnan(latest['k']):
        values['KDJ_K位置'] = float(latest['k'])

    # KDJ 金叉死叉（使用 MyTT CROSS）
    if len(df) >= 2:
        k_vals = df['k'].values
        d_vals = df['d'].values
        if pd.notna(k_vals[-1]) and pd.notna(d_vals[-1]):
            cross_kdj = CROSS(k_vals, d_vals)[-1]
            if cross_kdj:
                values['KDJ金叉死叉'] = 1 if k_vals[-1] > d_vals[-1] else -1
            else:
                values['KDJ金叉死叉'] = 0

    if pd.notna(latest.get('wr')) and not np.isnan(latest['wr']):
        # WR: 越高越超卖 → 取反
        values['WR(10)'] = -float(latest['wr'])

    # --- 成交量类 ---
    if pd.notna(latest.get('volratio')) and not np.isnan(latest['volratio']):
        values['量比'] = float(latest['volratio'])

    if pd.notna(latest.get('mfi')) and not np.isnan(latest['mfi']):
        values['MFI资金流量'] = float(latest['mfi'])

    # OBV趋势
    if len(df) >= 5 and 'obv' in df.columns:
        obv_recent = df['obv'].tail(5).values
        if not np.any(np.isnan(obv_recent)) and len(obv_recent) >= 2:
            values['OBV趋势'] = 1 if obv_recent[-1] > obv_recent[-2] else -1

    # --- 波动类 ---
    if all(pd.notna(latest.get(k)) and not np.isnan(latest[k]) for k in ['boll_upper', 'boll_lower']):
        denom = latest['boll_upper'] - latest['boll_lower']
        if denom != 0:
            values['布林带位置'] = round(
                (latest['close'] - latest['boll_lower']) / denom, 4
            )

    # ATR 波动率（当日振幅 / 20日均ATR）
    if pd.notna(latest.get('atr')) and not np.isnan(latest['atr']) and latest['atr'] > 0:
        price_range = latest['high'] - latest['low']
        values['ATR波动率'] = round(price_range / latest['atr'], 2)

    if pd.notna(latest.get('cci')) and not np.isnan(latest['cci']):
        values['CCI(14)'] = float(latest['cci'])

    # --- 趋势强度 ---
    if pd.notna(latest.get('adx')) and not np.isnan(latest['adx']):
        values['ADX趋势强度'] = float(latest['adx'])

    if all(pd.notna(latest.get(k)) and not np.isnan(latest[k]) for k in ['pdi', 'mdi']):
        values['DMI方向'] = float(latest['pdi'] - latest['mdi'])

    # --- 乖离类 ---
    if pd.notna(latest.get('bias_6')) and not np.isnan(latest['bias_6']):
        values['BIAS(6)'] = float(latest['bias_6'])

    return values


def analyze_etf(df, etf_code=''):
    """
    新版ETF分析：使用声明式打分引擎 + 市场状态 + ETF特有指标。
    
    Args:
        df: 技术指标DataFrame (需先经calculate_indicators处理)
        etf_code: ETF代码（用于获取ETF特有指标数据）
    
    Returns:
        分析结果字典，或None（数据不足时）
    """
    if df is None or len(df) < 120:
        return None

    latest = df.iloc[-1]

    # 1. 提取指标值
    indicator_values = extract_indicator_values(df)

    # 2. 检测市场状态
    regime_info = detect_market_regime(df)
    regime = regime_info.get('regime', 'range')

    # 3. 计算技术指标总分（自适应阈值 + NaN柔性处理）
    scoring_result = calculate_total_score(
        indicator_values,
        market_regime=regime,
    )

    # 诊断：当总分为0时，输出提取到的指标值和打分明细
    if scoring_result['total_score'] == 0.0:
        print(f"  [诊断] 提取到 {len(indicator_values)} 个指标: {list(indicator_values.keys())}")
        valid_details = [d for d in scoring_result['details'] if d['matched']]
        unmatched = [d for d in scoring_result['details'] if not d['matched']]
        truly_missing = [d for d in unmatched if d.get('raw_value') is None]
        neutral = [d for d in unmatched if d.get('raw_value') is not None]
        print(f"  [诊断] 命中规则: {len(valid_details)} 个, 中性区间: {len(neutral)} 个, 真正缺失: {len(truly_missing)} 个")
        if truly_missing:
            print(f"  [诊断] 缺失(值为None): {[d['name'] for d in truly_missing]}")
        if neutral:
            for d in neutral:
                print(f"  [诊断] 中性: {d['name']}={d.get('raw_value','?')} (未触发任何规则)")
        if valid_details:
            for d in valid_details:
                print(f"  [诊断] 命中: {d['name']}={d.get('raw_value','?')} → 得分={d['score']}")

    # 4. 趋势加成（买卖方向分离，消除循环依赖）
    trend_direction = regime_info.get('trend_direction', 'neutral')
    trend_strength = regime_info.get('trend_strength', 1.0)
    trend_bonus_result = calculate_trend_bonus(
        scoring_result['indicator_scores'],
        trend_direction,
        trend_strength,
    )

    # 5. ETF特有指标打分
    etf_specific_indicators = get_etf_specific_indicators(etf_code)
    etf_specific_score = score_etf_specific(etf_specific_indicators)

    # 6. 合成总分
    final_score = (
        scoring_result['total_score']
        + trend_bonus_result['bonus_score']
        + etf_specific_score['score']
    )

    # 7. 信号判定（自适应阈值）
    thresholds = scoring_result['adaptive_thresholds']
    if final_score >= thresholds['strong_buy']:
        final_signal = '加仓'
    elif final_score >= thresholds['buy']:
        final_signal = '逐步建仓'
    elif final_score <= thresholds['strong_sell']:
        final_signal = '减仓'
    elif final_score <= thresholds['sell']:
        final_signal = '逐步减仓'
    else:
        final_signal = '持有不动'

    # 8. 构建输出结果（保持向后兼容）
    weighted_scores = {}
    for detail in scoring_result['details']:
        name = detail['name']
        weighted_scores[name] = {
            '原始得分': 0.0 if not detail['matched'] else round(detail['score'], 2),
            '权重': 1.0,
            '加权得分': round(detail['score'], 2),
            '信号': detail['signal'] or '持仓',
            '状态': detail['status'],
        }

    # 补充趋势加成信息
    weighted_scores['_趋势加成'] = {
        '原始得分': trend_bonus_result['bonus_score'],
        '权重': 1.0,
        '加权得分': trend_bonus_result['bonus_score'],
        '方向': trend_bonus_result['direction'],
        '买入信号数': trend_bonus_result['signal_count']['buy'],
        '卖出信号数': trend_bonus_result['signal_count']['sell'],
    }

    # 补充ETF特有指标信息
    if any(v is not None for v in etf_specific_indicators.values()):
        weighted_scores['_ETF特有指标'] = {
            '折溢价率': etf_specific_indicators.get('premium_discount_rate'),
            '资金净流入': etf_specific_indicators.get('net_fund_flow'),
            '份额变化率': etf_specific_indicators.get('share_change_ratio'),
            '特异得分': etf_specific_score['score'],
        }
        if etf_specific_score['details']:
            weighted_scores['_ETF特有指标']['详情'] = etf_specific_score['details']

    result = {
        '日期': latest['date'].strftime('%Y-%m-%d') if hasattr(latest['date'], 'strftime') else str(latest['date'])[:10],
        'ETF代码': latest.get('etf_code', ''),
        'ETF名称': latest.get('etf_name', ''),
        '收盘价': round(float(latest['close']), 3),
        '成交量': int(latest['volume']),
        '综合评分': round(final_score, 2),
        '技术评分': scoring_result['total_score'],
        '趋势加成': trend_bonus_result['bonus_score'],
        'ETF特异得分': etf_specific_score['score'],
        '综合信号': final_signal,
        '市场状态': regime,
        '信心度': scoring_result['confidence'],
        '有效指标数': f"{scoring_result['valid_count']}/{scoring_result['total_count']}",
        '缺失指标': scoring_result['missing_indicators'],
        '指标得分': weighted_scores,
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
                
                analysis_result = analyze_etf(df_with_indicators, code)
                if analysis_result:
                    results.append(analysis_result)
                    print(f"  分析完成: {analysis_result['ETF名称']} - 信号: {analysis_result['综合信号']} - 评分: {analysis_result['综合评分']} - 市场: {analysis_result['市场状态']}")
                else:
                    print(f"  数据不足，跳过")
            
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
                '技术评分': result.get('技术评分', 0),
                '趋势加成': result.get('趋势加成', 0),
                'ETF特异得分': result.get('ETF特异得分', 0),
                '综合信号': result['综合信号'],
                '市场状态': result.get('市场状态', 'unknown'),
                '信心度': result.get('信心度', 0),
                '有效指标数': result.get('有效指标数', '0/0'),
            }
            
            for indicator_name, indicator_data in result.get('指标得分', {}).items():
                if indicator_name.startswith('_'):
                    continue
                row[f'{indicator_name}加权得分'] = indicator_data.get('加权得分', '')
                row[f'{indicator_name}信号'] = indicator_data.get('信号', '')
            
            csv_rows.append(row)
        
        df_csv = pd.DataFrame(csv_rows)
        
        df_summary = df_csv[['ETF名称', 'ETF代码', '收盘价', '综合评分', '技术评分', '趋势加成', 'ETF特异得分', '综合信号', '市场状态']].copy()
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
        print(f"\n评分范围统计:")
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
