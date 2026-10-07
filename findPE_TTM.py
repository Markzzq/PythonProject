"""
动态市盈率 TTM 计算与绘图
======================
传入股票代码，按日计算从上市以来每一天的动态市盈率(TTM)，并用 plotly 画图。

用法示例:
    calc_and_plot_pe_ttm('600519')       # 贵州茅台
    calc_and_plot_pe_ttm('000001')       # 平安银行
    calc_and_plot_pe_ttm('300750')       # 宁德时代
"""

import numpy as np
import pandas as pd
import akshare as ak
import datetime
import time
import sys, os
from concurrent.futures import ThreadPoolExecutor, as_completed

# 引入本地 Ashare 库（与 utils.py 同目录）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from Ashare import get_price_sina
    _ASHARE_OK = True
except Exception:
    _ASHARE_OK = False

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio


# ============================================================
# 工具函数：补全股票代码前缀（SH/SZ）
# ============================================================
def _with_market(code):
    """
    补齐股票代码的市场前缀。
    规则: 43/83/87/88/92 开头 -> BJ(北交所)，6/9 开头 -> SH，其他 -> SZ
    如果已经带前缀则原样返回。
    """
    code = str(code).strip()
    if code[:2] in ('SH', 'SZ', 'BJ'):
        return code
    if code[:2] in ('43', '83', '87', '88', '92'):
        return f'BJ{code}'
    if code[0] in ('6', '9'):
        return f'SH{code}'
    return f'SZ{code}'


# ============================================================
# 核心函数：按日计算 PE(TTM)
# ============================================================
def calc_pe_ttm(code):
    """
    按日计算一只股票的动态市盈率 TTM。

    思路:
      1. 优先用 ak.stock_value_em 直接拿东财提供的历史 PE(TTM)
         (东财从 2018-01-02 起有完整历史，新上市股票从上市日起)
      2. 对于东财数据起始日之前的时间段，用日线价格 + 季度归母净利润
         自己计算 TTM，再与东财数据拼接。

    参数:
        code: 股票代码，如 '600519'、'SH600519'、'sz000001'

    返回:
        DataFrame, 列: [日期, 收盘价, 总市值, PE_TTM, TTM净利润]
    """
    code_plain = str(code).strip().upper().replace('SH', '').replace('SZ', '')
    code_with_market = _with_market(code_plain)

    # ---------- 1. 东财 PE(TTM) 历史 ----------
    print(f'[1/3] 拉取 {code_plain} 的东财估值历史 (stock_value_em) ...')
    df_value = ak.stock_value_em(symbol=code_plain)
    df_value['日期'] = pd.to_datetime(df_value['数据日期'])
    df_value = df_value.rename(columns={
        '当日收盘价': '收盘价',
        '总市值': '总市值',
        'PE(TTM)': 'PE_TTM_EM',
        '总股本': '总股本'
    })
    df_em = df_value[['日期', '收盘价', '总市值', 'PE_TTM_EM', '总股本']].copy()
    df_em['TTM净利润_EM'] = df_em['总市值'] / df_em['PE_TTM_EM']
    print(f'    东财数据范围: {df_em["日期"].min().date()} ~ {df_em["日期"].max().date()}  共 {len(df_em)} 条')

    # ---------- 2. 利润表 ----------
    # 北交所等部分股票利润表接口可能失败，失败时降级为仅用东财 PE(TTM) 历史
    print(f'[2/3] 拉取 {code_plain} 的利润表 (stock_profit_sheet_by_report_em) ...')
    df_profit = None
    try:
        df_profit = ak.stock_profit_sheet_by_report_em(symbol=code_with_market)
        df_profit['REPORT_DATE'] = pd.to_datetime(df_profit['REPORT_DATE'])
        df_profit['NOTICE_DATE'] = pd.to_datetime(df_profit['NOTICE_DATE'])
        print(f'    已公告报告: {df_profit["NOTICE_DATE"].min().date()} ~ {df_profit["NOTICE_DATE"].max().date()}  共 {len(df_profit)} 条')
        # 累计利润 -> 单季度利润
        df_profit_q = _cumulative_to_quarter(df_profit)
    except Exception as e:
        print(f'    利润表获取失败({e})，降级为仅使用东财 PE(TTM) 历史')
        df_profit_q = pd.DataFrame(columns=['REPORT_DATE', 'NOTICE_DATE', 'quarter_profit'])

    # ---------- 3. 日线 ----------
    # 优先用本地 Ashare 库（新浪接口，稳定），fallback 到 akshare 东财接口
    code_sina = _with_market(code_plain).lower()  # ashare 用 sh600519 / sz000001
    print(f'[3/3] 拉取 {code_plain} 的日线 ...')

    df_daily = None
    # 3a. Ashare 新浪接口（分两次拉，覆盖完整历史）
    if _ASHARE_OK:
        try:
            print(f'    Ashare 新浪接口 (双次拉取) ...', end=' ', flush=True)
            df1 = get_price_sina(code=code_sina, count=5000, frequency='1d')
            if len(df1) == 0:
                raise ValueError('新浪接口无数据(北交所等不支持)')
            earliest = df1.index.min()
            earlier = earliest - pd.Timedelta(days=365)
            df2 = get_price_sina(code=code_sina, end_date=earlier.strftime('%Y-%m-%d'),
                                 count=5000, frequency='1d')
            df_all = pd.concat([df1, df2])
            df_all = df_all[~df_all.index.duplicated(keep='first')].sort_index()
            df_all = df_all.reset_index()
            df_all.columns = [c if c not in ('', 'index') else '日期' for c in df_all.columns]
            df_all['日期'] = pd.to_datetime(df_all['日期'])
            df_daily = df_all[['日期', 'close']].rename(columns={'close': '收盘价'}).copy()
            print(f'{len(df_daily)} 条  [{df_daily["日期"].min().date()} ~ {df_daily["日期"].max().date()}]')
        except Exception as e:
            print(f'失败 ({e})，尝试东财接口 ...')

    # 3b. fallback: akshare 东财接口
    if df_daily is None:
        try:
            start_str = df_profit['NOTICE_DATE'].min().strftime('%Y%m%d')
        except Exception:
            start_str = '20180101'  # 无利润表时从东财估值数据起点开始
        end_str = datetime.datetime.now().strftime('%Y%m%d')
        try:
            print(f'    akshare stock_zh_a_hist ({start_str} ~ {end_str}) ...', end=' ', flush=True)
            df_daily = _fetch_daily_in_batches(code_plain, start_str, end_str)
            df_daily['日期'] = pd.to_datetime(df_daily['日期'])
            df_daily = df_daily.rename(columns={'收盘': '收盘价'})
            df_daily = df_daily[['日期', '收盘价']].copy()
            print(f'{len(df_daily)} 条')
        except Exception as e:
            print(f'失败 ({e})')

    # 3c. 最终兜底: 直接用东财估值表自带的收盘价（如北交所股票）
    if df_daily is None:
        print('    使用东财估值表自带收盘价作为日线')
        df_daily = df_em[['日期', '收盘价']].copy()

    df_daily = df_daily.sort_values('日期').reset_index(drop=True)
    print(f'    日线范围: {df_daily["日期"].min().date()} ~ {df_daily["日期"].max().date()}  共 {len(df_daily)} 条')

    # ---------- 4. 逐天计算 TTM ----------
    print('正在按日计算 TTM ...')
    df_daily = df_daily.sort_values('日期').reset_index(drop=True)
    ttm_list = _calc_daily_ttm(df_daily['日期'], df_profit_q)
    df_daily['TTM净利润'] = ttm_list

    # ---------- 5. 拼接 & 汇总 ----------
    # 用东财数据的总股本（最精确），缺失时用最早可用的值
    df_em_sorted = df_em.sort_values('日期')
    # 向前填充总股本
    df_em_sorted['总股本_ff'] = df_em_sorted['总股本'].ffill()
    earliest_equity = df_em_sorted['总股本_ff'].iloc[0] if pd.notna(df_em_sorted['总股本_ff'].iloc[0]) else None

    # 合并: 以日线为基准，左连接东财估值
    df = df_daily.merge(df_em_sorted[['日期', 'PE_TTM_EM', '总市值', '总股本_ff']], on='日期', how='left')
    df = df.rename(columns={'总股本_ff': '总股本'})

    # 填充总股本（用东财有值的最早一个）
    if earliest_equity is not None:
        df['总股本'] = df['总股本'].fillna(earliest_equity)

    # 计算自己的 PE(TTM)
    df['总市值_自算'] = df['收盘价'] * df['总股本']
    df['PE_TTM_自算'] = df['总市值_自算'] / df['TTM净利润']

    # 最终 PE_TTM: 优先东财，没有则用自算
    df['PE_TTM'] = df['PE_TTM_EM'].combine_first(df['PE_TTM_自算'])
    df['总市值'] = df['总市值'].combine_first(df['总市值_自算'])

    # 只保留需要的列
    df = df[['日期', '收盘价', '总市值', 'PE_TTM', 'TTM净利润', 'PE_TTM_EM', 'PE_TTM_自算']].copy()
    df = df.sort_values('日期').reset_index(drop=True)

    # 去除最前面还没有完整 4 个季度的天（TTM 还没意义）
    # 保留 TTM净利润 > 0 的记录（亏损股也可留，PE 为负）
    # 这里只去除 NaN
    df = df.dropna(subset=['PE_TTM'])

    print(f'    最终结果: {df["日期"].min().date()} ~ {df["日期"].max().date()}  共 {len(df)} 条')
    return df


# ============================================================
# 辅助：分批拉日线（东财 stock_zh_a_hist 单次请求太长可能被拒）
# ============================================================
def _fetch_daily_in_batches(code_plain, start_date, end_date, batch_years=4):
    """
    按 batch_years 年一段拆分请求，循环拉取日线后拼接去重。
    每段之间加 1 秒延迟，避免触发风控。
    """
    start_dt = pd.Timestamp(start_date)
    end_dt = pd.Timestamp(end_date)
    all_frames = []

    cur = start_dt
    while cur <= end_dt:
        seg_end = min(cur + pd.DateOffset(years=batch_years) - pd.Timedelta(days=1), end_dt)
        seg_start_str = cur.strftime('%Y%m%d')
        seg_end_str = seg_end.strftime('%Y%m%d')
        print(f'      {seg_start_str} ~ {seg_end_str}', end=' ... ')

        df_seg = ak.stock_zh_a_hist(
            symbol=code_plain, period='daily',
            start_date=seg_start_str, end_date=seg_end_str, adjust=''
        )
        print(f'{len(df_seg)} 条')
        all_frames.append(df_seg)
        cur = seg_end + pd.Timedelta(days=1)
        time.sleep(1)

    df_all = pd.concat(all_frames, ignore_index=True)
    # 去重（边界日期可能重复）
    df_all = df_all.drop_duplicates(subset=['日期'], keep='first').sort_values('日期').reset_index(drop=True)
    return df_all


# ============================================================
# 辅助：累计利润表 -> 单季度利润
# ============================================================
def _cumulative_to_quarter(df):
    """
    ak.stock_profit_sheet_by_report_em 返回的 PARENT_NETPROFIT 是【累计值】:
      一季报 = Q1
      中报   = Q1 + Q2
      三季报 = Q1 + Q2 + Q3
      年报   = Q1 + Q2 + Q3 + Q4

    此函数将其转成单季度归母净利润, REPORT_DATE 不变，新增 quarter_profit 列。
    """
    df = df.sort_values('REPORT_DATE').reset_index(drop=True).copy()
    # 先一次性添加空列，避免连续 insert 的 PerformanceWarning
    quarter_profit_col = np.full(len(df), np.nan)

    for year, year_df in df.groupby(df['REPORT_DATE'].dt.year):
        q1 = year_df[year_df['REPORT_TYPE'] == '一季报']
        h1 = year_df[year_df['REPORT_TYPE'] == '中报']
        q3 = year_df[year_df['REPORT_TYPE'] == '三季报']
        annual = year_df[year_df['REPORT_TYPE'] == '年报']

        if len(q1):
            quarter_profit_col[q1.index] = q1['PARENT_NETPROFIT'].values
        if len(h1) and len(q1):
            quarter_profit_col[h1.index] = h1['PARENT_NETPROFIT'].values - q1['PARENT_NETPROFIT'].values
        if len(q3) and len(h1):
            quarter_profit_col[q3.index] = q3['PARENT_NETPROFIT'].values - h1['PARENT_NETPROFIT'].values
        if len(annual):
            if len(q3):
                val = annual['PARENT_NETPROFIT'].values - q3['PARENT_NETPROFIT'].values
            elif len(h1):
                val = annual['PARENT_NETPROFIT'].values - h1['PARENT_NETPROFIT'].values
            elif len(q1):
                val = annual['PARENT_NETPROFIT'].values - q1['PARENT_NETPROFIT'].values
            else:
                continue  # 只有年报的情况跳过（如早年可能只披露年报）
            quarter_profit_col[annual.index] = val

    df['quarter_profit'] = quarter_profit_col
    # 丢掉没有算出单季度的记录
    return df.dropna(subset=['quarter_profit']).copy()


# ============================================================
# 辅助：按日计算 TTM（滚动4个已公告的单季度归母净利润）
# ============================================================
def _calc_daily_ttm(dates: pd.Series, df_profit_q: pd.DataFrame) -> list:
    """
    对每一个日期，取 NOTIICE_DATE <= 该日期 的所有单季度利润，
    按 REPORT_DATE 取最近 4 个，求和即为 TTM。
    """
    result = []
    # 按公告日排序利润表
    profit_sorted = df_profit_q.sort_values('NOTICE_DATE').reset_index(drop=True)
    notice_dates = profit_sorted['NOTICE_DATE'].values.astype('datetime64[ns]')
    quarter_profits = profit_sorted['quarter_profit'].values
    report_dates = profit_sorted['REPORT_DATE'].values.astype('datetime64[ns]')

    for day in dates:
        day_ts = np.datetime64(pd.Timestamp(day))
        # 找到所有公告日 <= day 的利润记录
        mask = notice_dates <= day_ts
        if not mask.any():
            result.append(np.nan)
            continue

        available_profits = quarter_profits[mask]
        available_report_dates = report_dates[mask]

        # 按报告期末日期倒序，取最近 4 个季度
        order = np.argsort(available_report_dates)[::-1]
        top4 = available_profits[order][:4]
        if len(top4) < 4:
            result.append(np.nan)
        else:
            result.append(float(top4.sum()))

    return result


# ============================================================
# 绘图
# ============================================================
def plot_pe_ttm(df_pe, code, name=None, show=False, save_path=None):
    """
    参考 utils.py 的 plotly.express 风格，画 PE(TTM) 折线图。

    样式要点 (与 utils.py showAllStock / showOneETF 保持一致):
      - px.line 主曲线
      - 最新数据点加红色 marker + 绿色文字标注
      - 标题 = 股票名 + 股票代码

    参数:
        show: 是否弹窗显示（暂时注释掉不弹窗）
        save_path: 保存路径，不为空则保存交互式 HTML（无需 kaleido，比存图更稳定）
    """
    if name is None:
        name = code

    fig = px.line(
        df_pe, x='日期', y='PE_TTM',
        title=f'{name}  动态市盈率(TTM)  ——  {code}',
        labels={'PE_TTM': 'PE(TTM)'}
    )

    # 最新点高亮（与 utils.py showAllStock 保持一致）
    last = df_pe.iloc[-1]
    fig.add_trace(go.Scatter(
        x=[last['日期']],
        y=[last['PE_TTM']],
        text=[f"{last['PE_TTM']:.2f}"],
        mode='markers+text',
        marker=dict(color='red', size=10),
        textfont=dict(color='green', size=10),
        textposition='top left',
        showlegend=False,
    ))

    fig.update_layout(
        xaxis_title='日期',
        yaxis_title='PE(TTM)',
        hovermode='x unified',
    )

    # 画图弹窗暂时注释掉，按要求不执行
    # if show:
    #     fig.show()

    if save_path:
        # 保存为交互式 HTML（用浏览器打开可缩放、悬停查看数值）
        fig.write_html(save_path, include_plotlyjs='cdn')
    return fig


# ============================================================
# 一键入口
# ============================================================
def calc_and_plot_pe_ttm(code, name=None):
    """计算 + 绘图，一步到位。"""
    df = calc_pe_ttm(code)
    plot_pe_ttm(df, code, name=name)
    return df


# ============================================================
# 统计：当前PE_TTM / 历史最高 / 历史最低 / 历史百分位
# ============================================================
def calc_pe_stats(df_pe):
    """
    计算当前PE_TTM及历史分位。

    百分位定义: 历史上所有 PE_TTM <= 当前值 的天数占比
              = count(PE <= 当前) / 总天数 * 100
    """
    pe = df_pe['PE_TTM'].dropna()
    cur = float(pe.iloc[-1])
    hist_max = float(pe.max())
    hist_min = float(pe.min())
    percentile = float((pe <= cur).sum()) / len(pe) * 100
    return cur, hist_max, hist_min, percentile


# ============================================================
# 批量执行：读取 stock_A_list.csv，逐只计算并汇总到 Excel
# ============================================================
LOW_PERCENTILE = 15   # 低于该百分位则保存图片
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # 脚本所在目录（工程当前目录）
IMG_DIR = os.path.join(BASE_DIR, 'pe_ttm_low_percentile')   # 低百分位图片统一保存文件夹
OUTPUT_EXCEL = os.path.join(BASE_DIR, 'pe_ttm_summary.xlsx')  # 汇总Excel
MAX_WORKERS = 8      # 并行线程数（网络IO密集型，可按需调整）


def _process_one_stock(code_plain, name, img_dir, low_pct):
    """
    单只股票处理（线程池 worker），返回一行结果 dict。
    当前 PE_TTM 为负（TTM净利润为负）时直接跳过，返回 None。
    """
    rec = {'股票代码': code_plain, '股票名称': name}
    try:
        df_pe = calc_pe_ttm(code_plain)
        cur, mx, mn, pct = calc_pe_stats(df_pe)

        # 当前PE为负 => 公司TTM净利润为负，按要求直接跳过该股票
        if cur < 0:
            print(f'[跳过] {code_plain} {name} 当前PE_TTM={cur:.2f}（TTM净利润为负）')
            return None

        rec.update({
            '当前PE_TTM': round(cur, 2),
            '历史最高PE_TTM': round(mx, 2),
            '历史最低PE_TTM': round(mn, 2),
            '当前百分位(%)': round(pct, 2),
            '是否低于15%分位': '是' if pct < low_pct else '否',
            '数据起始日': str(df_pe['日期'].min().date()),
            '数据结束日': str(df_pe['日期'].max().date()),
            '数据天数': len(df_pe),
        })

        # 低于15%分位 -> 保存 PE(TTM) 日线交互式HTML到统一文件夹
        if pct < low_pct:
            save_path = os.path.join(img_dir, f'{code_plain}_{name}.html')
            try:
                plot_pe_ttm(df_pe, code_plain, name=name, save_path=save_path)
                rec['已保存图片'] = '是'
            except Exception as e:
                rec['已保存图片'] = '否'
                rec['备注'] = f'存图失败: {e}'
        else:
            rec['已保存图片'] = '否'

    except Exception as e:
        rec['备注'] = f'计算失败: {e}'

    return rec


def run_all_stocks(csv_path='stock_A_list.csv', output_excel=OUTPUT_EXCEL,
                   img_dir=IMG_DIR, low_pct=LOW_PERCENTILE, max_workers=MAX_WORKERS):
    """
    从 csv_path 读取股票列表（列: 代码/名称，代码带 sh/sz/bj 前缀），
    多线程并行计算每只股票的 PE(TTM) 及历史分位，汇总后统一输出 Excel。

    - 当前百分位 < low_pct 的股票: PE(TTM) 日线图保存到 img_dir 文件夹
    - 当前 PE_TTM 为负（TTM净利润为负）的股票: 直接跳过，不计入汇总
    - 每只股票一行数据，每完成50只落盘一次防中断丢失
    """
    df_list = pd.read_csv(csv_path, encoding='utf-8-sig')
    os.makedirs(img_dir, exist_ok=True)

    # 组装任务列表（bj 开头的北交所股票直接跳过不处理）
    tasks = []
    skipped = 0
    for _, row in df_list.iterrows():
        raw_code = str(row['代码']).strip()
        name = str(row['名称']).strip()
        if raw_code.lower().startswith('bj'):
            skipped += 1
            continue
        # 去掉 sh/sz/bj 前缀，只留6位数字（与 utils.py showAllStock 同样处理）
        code_plain = raw_code[2:] if raw_code[:2].isalpha() else raw_code
        tasks.append((code_plain, name))

    total = len(tasks)
    results = []
    done = 0
    skipped_pe = 0
    print(f'===== 共 {total} 只股票（已跳过 {skipped} 只 bj 北交所股票），{max_workers} 线程并行执行 =====')

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_process_one_stock, c, n, img_dir, low_pct) for c, n in tasks]
        for fut in as_completed(futures):
            rec = fut.result()
            done += 1

            # 当前PE为负的股票：不计入汇总
            if rec is None:
                skipped_pe += 1
                continue

            results.append(rec)

            # 单行进度摘要
            if '备注' in rec:
                print(f'[{done}/{total}] {rec["股票代码"]} {rec["股票名称"]} {rec["备注"]}')
            else:
                extra = '，图片已保存' if rec.get('已保存图片') == '是' else ''
                print(f'[{done}/{total}] {rec["股票代码"]} {rec["股票名称"]} '
                      f'当前PE={rec["当前PE_TTM"]} 百分位={rec["当前百分位(%)"]}%{extra}')

            # 每50只股票落盘一次，防止长时间运行中断丢数据
            # （先写临时文件再替换，避免中途被打断产生损坏的 xlsx）
            if done % 50 == 0:
                tmp = output_excel + '.tmp.xlsx'
                pd.DataFrame(results).to_excel(tmp, index=False)
                os.replace(tmp, output_excel)
                print(f'[checkpoint] 已完成 {done}/{total}，中间结果已写入 {output_excel}')

    # 最后统一输出
    df_out = pd.DataFrame(results)
    tmp = output_excel + '.tmp.xlsx'
    df_out.to_excel(tmp, index=False)
    os.replace(tmp, output_excel)
    print(f'\n===== 全部完成，汇总已保存: {output_excel}  共 {len(df_out)} 行 =====')
    print(f'===== 跳过统计: {skipped} 只 bj 北交所股票，{skipped_pe} 只当前PE为负（净利润为负） =====')
    return df_out


# ============================================================
# 测试入口
# ============================================================
if __name__ == '__main__':
    # 批量: 从 stock_A_list.csv 读取股票列表依次执行
    # 画图弹窗已注释掉，仅对百分位<15%的股票保存图片到 pe_ttm_low_percentile 文件夹
    df_out = run_all_stocks()

    print()
    print('=== 汇总预览(前20行) ===')
    print(df_out.head(20).to_string(index=False))
