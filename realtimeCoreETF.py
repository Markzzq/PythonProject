import sys
import os
os.environ['TQDM_DISABLE'] = '1'
import akshare as ak
import pandas as pd
import numpy as np
import time
import schedule
from datetime import datetime


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ============================================================
# 全局配置 —— 可自由调整的偏离阈值
# ============================================================
CONFIG_UPDATE_INTERVAL = 15          # 监控间隔(分钟)

# --- MA5 偏离阈值（价格偏离5日均线的百分比）---
CONFIG_MA5_UP_WARN = 0.05           # 向上偏离MA5 预警线（默认5%）
CONFIG_MA5_UP_ALERT = 0.08          # 向上偏离MA5 告警线（默认8%）
CONFIG_MA5_DOWN_WARN = 0.05         # 向下偏离MA5 预警线（默认5%）
CONFIG_MA5_DOWN_ALERT = 0.08        # 向下偏离MA5 告警线（默认8%）

# --- MA10 偏离阈值（价格偏离10日均线的百分比）---
CONFIG_MA10_UP_WARN = 0.05          # 向上偏离MA10 预警线（默认5%）
CONFIG_MA10_UP_ALERT = 0.08         # 向上偏离MA10 告警线（默认8%）
CONFIG_MA10_DOWN_WARN = 0.05        # 向下偏离MA10 预警线（默认5%）
CONFIG_MA10_DOWN_ALERT = 0.08       # 向下偏离MA10 告警线（默认8%）

# --- 告警冷却 ---
CONFIG_ALERT_COOLDOWN_MINUTES = 60   # 同ETF同方向同级别告警冷却时间(分钟)

running = True

# --- 内存缓存（性能优化）---
_ma_cache = {}          # {etf_code: {'ma5': float, 'ma10': float, 'ts': datetime}}
_alert_history = {}     # {alert_key: datetime}  用于冷却去重
_alert_stats = {}       # 当前轮次统计，每轮重置


def get_etf_ma_values(etf_code):
    """获取ETF的MA5/MA10（当天缓存复用，同一天只请求一次）"""
    cached = _ma_cache.get(etf_code)
    if cached is not None:
        if cached['ts'].date() == datetime.now().date():
            return cached['ma5'], cached['ma10']

    try:
        etf_hist_df = ak.fund_etf_hist_sina(symbol=etf_code)
        if etf_hist_df is None or etf_hist_df.empty:
            return None, None

        n = etf_hist_df.shape[0]
        if n < 10:
            return None, None

        CLOSE = etf_hist_df['close'].astype(float)
        ma5 = round(float(np.mean(CLOSE[-5:])), 4)
        ma10 = round(float(np.mean(CLOSE[-10:])), 4)

        _ma_cache[etf_code] = {'ma5': ma5, 'ma10': ma10, 'ts': datetime.now()}
        return ma5, ma10
    except Exception as e:
        print(f"获取 {etf_code} MA值失败: {e}")
        return None, None


def get_realtime_prices():
    """批量获取所有ETF实时价格"""
    try:
        df_spot = ak.fund_etf_spot_em()
        if df_spot is None or df_spot.empty:
            return None
        price_dict = {}
        for _, row in df_spot.iterrows():
            code = row['代码']
            price_dict[code] = float(row['最新价'])
        return price_dict
    except Exception as e:
        print(f"获取实时行情失败: {e}")
        return None


def _cooldown_ok(alert_key):
    """冷却检查：返回 True=可以触发，False=冷却中"""
    last = _alert_history.get(alert_key)
    if last is None:
        return True
    return (datetime.now() - last).total_seconds() / 60 >= CONFIG_ALERT_COOLDOWN_MINUTES


def _record(alert_key):
    """记录告警触发时间"""
    _alert_history[alert_key] = datetime.now()


def _check_deviation(realtime_price, ma_value, ma_label, etf_code, etf_name,
                     up_warn, up_alert, down_warn, down_alert, stat_prefix):
    """
    统一的偏离检查函数
    ma_label: 'MA5' / 'MA10'
    stat_prefix: 'ma5' / 'ma10'
    返回触发的告警数量
    """
    triggered = 0

    # --- 向上偏离 ---
    if realtime_price > ma_value:
        dev = (realtime_price - ma_value) / ma_value
        if dev >= up_alert:
            key = f"{etf_code}|{stat_prefix}_up_alert"
            if _cooldown_ok(key):
                _record(key)
                _alert_stats[f'{stat_prefix}_alert_up'] += 1
                print(f"🔴【{ma_label}告警】向上偏离过大 - {etf_code} {etf_name}")
                print(f"  实时净值: {realtime_price:.4f}  {ma_label}: {ma_value:.4f}  偏离度: {dev*100:+.2f}%  (> {up_alert*100:.1f}%)")
                print()
                triggered += 1
        elif dev >= up_warn:
            key = f"{etf_code}|{stat_prefix}_up_warn"
            if _cooldown_ok(key):
                _record(key)
                _alert_stats[f'{stat_prefix}_warn_up'] += 1
                print(f"🟡【{ma_label}预警】向上偏离偏大 - {etf_code} {etf_name}")
                print(f"  实时净值: {realtime_price:.4f}  {ma_label}: {ma_value:.4f}  偏离度: {dev*100:+.2f}%  (> {up_warn*100:.1f}%)")
                print()
                triggered += 1

    # --- 向下偏离 ---
    if realtime_price < ma_value:
        dev = (ma_value - realtime_price) / ma_value
        if dev >= down_alert:
            key = f"{etf_code}|{stat_prefix}_down_alert"
            if _cooldown_ok(key):
                _record(key)
                _alert_stats[f'{stat_prefix}_alert_down'] += 1
                print(f"🔴【{ma_label}告警】向下偏离过大 - {etf_code} {etf_name}")
                print(f"  实时净值: {realtime_price:.4f}  {ma_label}: {ma_value:.4f}  偏离度: -{dev*100:.2f}%  (< -{down_alert*100:.1f}%)")
                print()
                triggered += 1
        elif dev >= down_warn:
            key = f"{etf_code}|{stat_prefix}_down_warn"
            if _cooldown_ok(key):
                _record(key)
                _alert_stats[f'{stat_prefix}_warn_down'] += 1
                print(f"🟡【{ma_label}预警】向下偏离偏大 - {etf_code} {etf_name}")
                print(f"  实时净值: {realtime_price:.4f}  {ma_label}: {ma_value:.4f}  偏离度: -{dev*100:.2f}%  (< -{down_warn*100:.1f}%)")
                print()
                triggered += 1

    return triggered


def monitor_etf_deviation():
    global _alert_stats
    _alert_stats = {
        'ma5_warn_up': 0, 'ma5_warn_down': 0,
        'ma5_alert_up': 0, 'ma5_alert_down': 0,
        'ma10_warn_up': 0, 'ma10_warn_down': 0,
        'ma10_alert_up': 0, 'ma10_alert_down': 0,
    }

    start_time = time.time()
    print(f"\n{'='*60}")
    print(f"监控执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    try:
        csv_path = get_resource_path('etf_core_list.csv')
        df_etf_list = pd.read_csv(csv_path, encoding='utf-8-sig')
        df_etf = df_etf_list[['代码', '名称']]
    except Exception as e:
        print(f"读取 ETF 列表失败: {e}")
        return

    # 批量获取实时行情（一次API调用覆盖所有ETF）
    price_dict = get_realtime_prices()
    if price_dict is None:
        print("无法获取实时行情，本次监控跳过")
        return

    for _, row in df_etf.iterrows():
        etf_code_with_prefix = row['代码']
        etf_name = row['名称']
        etf_code = etf_code_with_prefix[2:] if len(etf_code_with_prefix) > 2 else etf_code_with_prefix

        # MA值带缓存，当天只请求一次历史数据
        ma5, ma10 = get_etf_ma_values(etf_code_with_prefix)
        if ma5 is None or ma10 is None:
            continue

        realtime_price = price_dict.get(etf_code)
        if realtime_price is None:
            continue

        # 偏离 MA5 检查
        _check_deviation(realtime_price, ma5, 'MA5', etf_code, etf_name,
                         CONFIG_MA5_UP_WARN, CONFIG_MA5_UP_ALERT,
                         CONFIG_MA5_DOWN_WARN, CONFIG_MA5_DOWN_ALERT, 'ma5')

        # 偏离 MA10 检查
        _check_deviation(realtime_price, ma10, 'MA10', etf_code, etf_name,
                         CONFIG_MA10_UP_WARN, CONFIG_MA10_UP_ALERT,
                         CONFIG_MA10_DOWN_WARN, CONFIG_MA10_DOWN_ALERT, 'ma10')

        if not running:
            break

    end_time = time.time()
    s = _alert_stats
    print(f"\n{'─'*60}")
    print(f"监控汇总")
    print(f"  MA5  向上预警: {s['ma5_warn_up']}  向上告警: {s['ma5_alert_up']}  |  向下预警: {s['ma5_warn_down']}  向下告警: {s['ma5_alert_down']}")
    print(f"  MA10 向上预警: {s['ma10_warn_up']} 向上告警: {s['ma10_alert_up']}  |  向下预警: {s['ma10_warn_down']} 向下告警: {s['ma10_alert_down']}")
    print(f"  运行时间: {end_time - start_time:.2f} 秒")


if __name__ == '__main__':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')
    print("ETF MA5/MA10 偏离分级监控程序启动")
    print(f"监控规则:")
    print(f"  MA5  向上: 预警>{CONFIG_MA5_UP_WARN*100:.0f}%  告警>{CONFIG_MA5_UP_ALERT*100:.0f}%")
    print(f"  MA5  向下: 预警>{CONFIG_MA5_DOWN_WARN*100:.0f}%  告警>{CONFIG_MA5_DOWN_ALERT*100:.0f}%")
    print(f"  MA10 向上: 预警>{CONFIG_MA10_UP_WARN*100:.0f}%  告警>{CONFIG_MA10_UP_ALERT*100:.0f}%")
    print(f"  MA10 向下: 预警>{CONFIG_MA10_DOWN_WARN*100:.0f}%  告警>{CONFIG_MA10_DOWN_ALERT*100:.0f}%")
    print(f"  告警冷却: {CONFIG_ALERT_COOLDOWN_MINUTES} 分钟")
    print(f"执行间隔: {CONFIG_UPDATE_INTERVAL} 分钟")
    print("按 Ctrl+C 退出")
    print()

    monitor_etf_deviation()

    schedule.every(CONFIG_UPDATE_INTERVAL).minutes.do(monitor_etf_deviation)

    try:
        while running:
            schedule.run_pending()
            time.sleep(0.5)
    except KeyboardInterrupt:
        running = False
        print("\n正在退出监控程序...")
        print("监控程序已退出")
