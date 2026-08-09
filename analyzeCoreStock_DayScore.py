"""
股票每日评分分析工具 v2.0
=======================
升级内容：
- 使用声明式打分引擎 (scoring_engine.py)
- 市场状态自适应阈值 (market_regime.py)
- NaN柔性处理：单个指标缺失不压整只股票
- 买卖方向分离的Trend Bonus
"""

import pandas as pd
import numpy as np
import datetime
import warnings
import os

import pymysql

try:
    from sqlalchemy import create_engine
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

from MyTT import MACD, KDJ, RSI, BOLL, BIAS, MA, CCI, WR, DMI, ATR, PSY, VR, TRIX, EMV, MFI, OBV, SAR, CR, WAD, TEMA, MIDPRICE, VWAP, CMF, VOLRATIO, PRICEVOLUME
from scoring_engine import calculate_total_score, calculate_trend_bonus
from market_regime import detect_market_regime


STOCK_MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'ZZQ1996zzq@',
    'database': 'stock_daily',
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


def get_all_stock_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES LIKE 'stock_%'")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables


def get_stock_data(conn, table_name):
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


def extract_indicator_values(df):
    """
    从计算结果DataFrame中提取指标最新值，转换为打分引擎需要的格式。
    """
    if df is None or len(df) < 120:
        return {}

    latest = df.iloc[-1]
    values = {}

    # --- 趋势类 ---
    if pd.notna(latest.get('dif')) and not np.isnan(latest['dif']):
        values['MACD_DIF位置'] = float(latest['dif'])

    if len(df) >= 2:
        prev_dif = df['dif'].iloc[-2]; prev_dea = df['dea'].iloc[-2]
        curr_dif = latest['dif']; curr_dea = latest['dea']
        if all(pd.notna(x) and not np.isnan(x) for x in [prev_dif, prev_dea, curr_dif, curr_dea]):
            if prev_dif <= prev_dea and curr_dif > curr_dea:
                values['MACD金叉死叉'] = 1
            elif prev_dif >= prev_dea and curr_dif < curr_dea:
                values['MACD金叉死叉'] = -1
            else:
                values['MACD金叉死叉'] = 0

    if len(df) >= 2:
        prev_ma5 = df['ma5'].iloc[-2]; prev_ma10 = df['ma10'].iloc[-2]
        curr_ma5 = latest['ma5']; curr_ma10 = latest['ma10']
        if all(pd.notna(x) and not np.isnan(x) for x in [prev_ma5, prev_ma10, curr_ma5, curr_ma10]):
            if prev_ma5 <= prev_ma10 and curr_ma5 > curr_ma10:
                values['MA5_MA10金叉死叉'] = 1
            elif prev_ma5 >= prev_ma10 and curr_ma5 < curr_ma10:
                values['MA5_MA10金叉死叉'] = -1
            else:
                values['MA5_MA10金叉死叉'] = 0

    if all(k in df.columns and pd.notna(latest[k]) and not np.isnan(latest[k]) for k in ['ma5', 'ma10', 'ma20', 'ma60']):
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

    if pd.notna(latest.get('ma20')) and not np.isnan(latest['ma20']):
        values['价格vs MA20'] = round((latest['close'] - latest['ma20']) / latest['ma20'] * 100, 2)

    if pd.notna(latest.get('ma60')) and not np.isnan(latest['ma60']):
        values['价格vs MA60'] = round((latest['close'] - latest['ma60']) / latest['ma60'] * 100, 2)

    # --- 动量类 ---
    if pd.notna(latest.get('rsi_12')) and not np.isnan(latest['rsi_12']):
        values['RSI(14)'] = float(latest['rsi_12'])

    if pd.notna(latest.get('k')) and not np.isnan(latest['k']):
        values['KDJ_K位置'] = float(latest['k'])

    if len(df) >= 2:
        prev_k = df['k'].iloc[-2]; prev_d = df['d'].iloc[-2]
        curr_k = latest['k']; curr_d = latest['d']
        if all(pd.notna(x) and not np.isnan(x) for x in [prev_k, prev_d, curr_k, curr_d]):
            if prev_k <= prev_d and curr_k > curr_d:
                values['KDJ金叉死叉'] = 1
            elif prev_k >= prev_d and curr_k < curr_d:
                values['KDJ金叉死叉'] = -1
            else:
                values['KDJ金叉死叉'] = 0

    if pd.notna(latest.get('wr')) and not np.isnan(latest['wr']):
        values['WR(10)'] = -float(latest['wr'])

    # --- 成交量类 ---
    if pd.notna(latest.get('volratio')) and not np.isnan(latest['volratio']):
        values['量比'] = float(latest['volratio'])

    if pd.notna(latest.get('mfi')) and not np.isnan(latest['mfi']):
        values['MFI资金流量'] = float(latest['mfi'])

    if len(df) >= 5 and 'obv' in df.columns:
        obv_recent = df['obv'].tail(5).values
        if not np.any(np.isnan(obv_recent)) and len(obv_recent) >= 2:
            values['OBV趋势'] = 1 if obv_recent[-1] > obv_recent[-2] else -1

    # --- 波动类 ---
    if all(pd.notna(latest.get(k)) and not np.isnan(latest[k]) for k in ['boll_upper', 'boll_lower']):
        denom = latest['boll_upper'] - latest['boll_lower']
        if denom != 0:
            values['布林带位置'] = round((latest['close'] - latest['boll_lower']) / denom, 4)

    if pd.notna(latest.get('atr')) and not np.isnan(latest['atr']) and latest['atr'] > 0:
        values['ATR波动率'] = round((latest['high'] - latest['low']) / latest['atr'], 2)

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


def analyze_stock(df):
    """
    新版股票分析：使用声明式打分引擎 + 市场状态。
    
    Args:
        df: 技术指标DataFrame (需先经calculate_indicators处理)
    
    Returns:
        分析结果字典，或None（数据不足时）
    """
    if df is None or len(df) < 120:
        return None

    latest = df.iloc[-1]

    # 1. 提取指标值（复用 extract_indicator_values 逻辑）
    indicator_values = extract_indicator_values(df)

    # 2. 检测市场状态
    regime_info = detect_market_regime(df)
    regime = regime_info.get('regime', 'range')

    # 3. 计算技术指标总分（自适应阈值 + NaN柔性处理）
    scoring_result = calculate_total_score(
        indicator_values,
        market_regime=regime,
    )

    # 4. 趋势加成（买卖方向分离，消除循环依赖）
    trend_direction = regime_info.get('trend_direction', 'neutral')
    trend_strength = regime_info.get('trend_strength', 1.0)
    trend_bonus_result = calculate_trend_bonus(
        scoring_result['indicator_scores'],
        trend_direction,
        trend_strength,
    )

    # 5. 合成总分（股票无ETF特有指标）
    final_score = scoring_result['total_score'] + trend_bonus_result['bonus_score']

    # 6. 信号判定（自适应阈值）
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

    # 7. 构建输出结果（保持向后兼容）
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

    result = {
        '日期': latest['date'].strftime('%Y-%m-%d') if hasattr(latest['date'], 'strftime') else str(latest['date'])[:10],
        '股票代码': latest.get('stock_code', ''),
        '股票名称': latest.get('stock_name', ''),
        '收盘价': round(float(latest['close']), 3),
        '成交量': int(latest['volume']),
        '综合评分': round(final_score, 2),
        '技术评分': scoring_result['total_score'],
        '趋势加成': trend_bonus_result['bonus_score'],
        '综合信号': final_signal,
        '市场状态': regime,
        '信心度': scoring_result['confidence'],
        '有效指标数': f"{scoring_result['valid_count']}/{scoring_result['total_count']}",
        '缺失指标': scoring_result['missing_indicators'],
        '指标得分': weighted_scores
    }

    return result


def load_core_stock_list():
    csv_path = 'stock_core_list.csv'
    if not os.path.exists(csv_path):
        print(f"错误: 未找到股票列表文件 {csv_path}")
        return []
    
    df = pd.read_csv(csv_path)
    if '代码' not in df.columns:
        print("错误: CSV文件缺少'代码'列")
        return []
    
    stock_codes = df['代码'].tolist()
    return stock_codes


def analyze_all_stocks():
    print("=" * 70)
    print("股票指标分析工具")
    print("=" * 70)
    print(f"数据库: {STOCK_MYSQL_CONFIG['host']}:{STOCK_MYSQL_CONFIG['port']}/{STOCK_MYSQL_CONFIG['database']}")
    print(f"分析时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    conn = None
    
    try:
        conn = get_mysql_connection(STOCK_MYSQL_CONFIG)
        print("数据库连接成功\n")
        
        core_stock_codes = load_core_stock_list()
        if not core_stock_codes:
            print("未加载到有效股票列表，程序退出")
            conn.close()
            return
        
        print(f"从 stock_core_list.csv 加载了 {len(core_stock_codes)} 个股票")
        
        tables = get_all_stock_tables(conn)
        print(f"数据库中共有 {len(tables)} 个股票数据表")
        
        results = []
        for code in core_stock_codes:
            table_name = f'stock_{code}'
            print(f"\n处理: {code}")
            
            try:
                df = get_stock_data(conn, table_name)
                if len(df) < 120:
                    print(f"  数据不足120条，跳过")
                    continue
                
                df_with_indicators = calculate_indicators(df)
                if df_with_indicators is None:
                    print(f"  指标计算失败，跳过")
                    continue
                
                analysis_result = analyze_stock(df_with_indicators)
                if analysis_result:
                    results.append(analysis_result)
                    print(f"  分析完成: {analysis_result['股票名称']} - 信号: {analysis_result['综合信号']} - 评分: {analysis_result['综合评分']} - 市场: {analysis_result['市场状态']}")
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
                '股票名称': result['股票名称'],
                '股票代码': result['股票代码'],
                '收盘价': result['收盘价'],
                '成交量': result['成交量'],
                '综合评分': result['综合评分'],
                '技术评分': result.get('技术评分', 0),
                '趋势加成': result.get('趋势加成', 0),
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
        
        df_summary = df_csv[['股票名称', '股票代码', '收盘价', '综合评分', '技术评分', '趋势加成', '综合信号', '市场状态']].copy()
        df_summary = df_summary.sort_values('综合评分', ascending=False)
        
        print("\n" + "=" * 70)
        print("股票指标分析汇总")
        print("=" * 70)
        print(df_summary.to_string(index=False))
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"stock_analysis_{timestamp}.csv"
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
    analyze_all_stocks()