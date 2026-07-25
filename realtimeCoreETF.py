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


CONFIG_UPDATE_INTERVAL = 15
CONFIG_HISTORY_DAYS = 15
CONFIG_UP_DEVIATION_THRESHOLD = 0.08
CONFIG_DOWN_DEVIATION_THRESHOLD = 0.08

running = True


def get_etf_ma_values(etf_code):
    try:
        etf_hist_df = ak.fund_etf_hist_sina(symbol=etf_code)
        if etf_hist_df is None or etf_hist_df.empty:
            return None, None
        
        n = etf_hist_df.shape[0]
        if n < 10:
            return None, None
        
        CLOSE = etf_hist_df['close'].astype(float)
        ma5 = np.mean(CLOSE[-5:])
        ma10 = np.mean(CLOSE[-10:])
        
        return ma5, ma10
    except Exception as e:
        print(f"获取 {etf_code} MA值失败: {e}")
        return None, None


def get_realtime_prices():
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


def monitor_etf_deviation():
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

    price_dict = get_realtime_prices()
    if price_dict is None:
        print("无法获取实时行情，本次监控跳过")
        return

    up_alert_count = 0
    down_alert_count = 0

    for _, row in df_etf.iterrows():
        etf_code_with_prefix = row['代码']
        etf_name = row['名称']
        
        etf_code = etf_code_with_prefix[2:] if len(etf_code_with_prefix) > 2 else etf_code_with_prefix

        ma5, ma10 = get_etf_ma_values(etf_code_with_prefix)
        if ma5 is None or ma10 is None:
            continue

        realtime_price = price_dict.get(etf_code)
        if realtime_price is None:
            continue

        up_threshold = ma5 * (1 + CONFIG_UP_DEVIATION_THRESHOLD)
        down_threshold = ma5 * (1 - CONFIG_DOWN_DEVIATION_THRESHOLD)

        if realtime_price > up_threshold and ma5 > ma10:
            up_alert_count += 1
            deviation = (realtime_price - ma5) / ma5 * 100
            print(f"【多头告警】上升偏离过高 - {etf_code_with_prefix} {etf_name}")
            print(f"  实时净值: {realtime_price:.4f}")
            print(f"  MA5: {ma5:.4f}, MA10: {ma10:.4f}")
            print(f"  偏离度: {deviation:+.2f}% (> {CONFIG_UP_DEVIATION_THRESHOLD*100:.1f}%)")
            print(f"  均线状态: MA5 > MA10 (多头排列)")
            print()

        elif realtime_price < down_threshold and ma5 < ma10:
            down_alert_count += 1
            deviation = (realtime_price - ma5) / ma5 * 100
            print(f"【空头告警】下跌偏离过大 - {etf_code_with_prefix} {etf_name}")
            print(f"  实时净值: {realtime_price:.4f}")
            print(f"  MA5: {ma5:.4f}, MA10: {ma10:.4f}")
            print(f"  偏离度: {deviation:+.2f}% (< -{CONFIG_DOWN_DEVIATION_THRESHOLD*100:.1f}%)")
            print(f"  均线状态: MA5 < MA10 (空头排列)")
            print()

        if not running:
            break
        for _ in range(3):
            if not running:
                break
            time.sleep(0.1)

    end_time = time.time()
    print(f"\n监控完成")
    print(f"上升偏离过高: {up_alert_count} 个")
    print(f"下跌偏离过大: {down_alert_count} 个")
    print(f"运行时间: {end_time - start_time:.2f} 秒")


if __name__ == '__main__':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')
    print("ETF MA5/MA10 偏离监控程序启动")
    print(f"监控规则:")
    print(f"  上涨偏离: 实时净值 > MA5 × {1 + CONFIG_UP_DEVIATION_THRESHOLD:.0%} 且 MA5 > MA10")
    print(f"  下跌偏离: 实时净值 < MA5 × {1 - CONFIG_DOWN_DEVIATION_THRESHOLD:.0%} 且 MA5 < MA10")
    print(f"执行间隔: {CONFIG_UPDATE_INTERVAL} 分钟")
    print("按 Ctrl+C 退出")
    print()

    monitor_etf_deviation()

    schedule.every(CONFIG_UPDATE_INTERVAL).minutes.do(monitor_etf_deviation)

    try:
        while running:
            schedule.run_pending()
            for _ in range(10):
                if not running:
                    break
                time.sleep(0.1)
    except KeyboardInterrupt:
        running = False
        print("\n正在退出监控程序...")
        print("监控程序已退出")