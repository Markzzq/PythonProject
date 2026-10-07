# -*- coding: utf-8 -*-
"""
巴菲特 DCF 现金流折现模型 —— 自由现金流(FCF)连续三年为正筛选
==============================================================

理论背景:
    巴菲特 DCF 的折现对象不是会计净利润, 而是"所有者盈余"(Owner Earnings,
    1986年致股东信): 报告利润 + 折旧摊销等非现金支出 - 维持竞争地位所需的资本支出。
    内在价值 V = Σ FCF_t/(1+r)^t + 终值, 但 DCF 估值的前提是企业能持续产生正 FCF。

自由现金流计算口径 (尽可能详细全面, 全部取自现金流量表标准科目):
    FCF = 经营活动产生的现金流量净额                        (NETCASH_OPERATE)
        - 购建固定资产、无形资产和其他长期资产支付的现金      (CONSTRUCT_LONG_ASSET, 资本支出 CapEx)
        + 处置固定资产、无形资产和其他长期资产收回的现金净额    (DISPOSAL_LONG_ASSET, 长期资产变现回收)
        - 取得子公司及其他营业单位支付的现金净额              (OBTAIN_SUBSIDIARY_OTHER, 并购扩张支出)
        + 处置子公司及其他营业单位收到的现金净额              (DISPOSAL_SUBSIDIARY_OTHER, 出售子公司回收)

    与简易版 "经营现金流净额 - 资本支出" 相比, 增加了 3 项投资活动明细调整:
      1. 处置长期资产收回的现金: 出售设备/房产等属于资本开支的回收, 应加回
      2. 取得子公司支付的现金净额: 收购兼并是真实的扩张性资本投入, 应扣除
      3. 处置子公司收到的现金净额: 出售子公司是投资收回, 应加回

    不纳入口径的科目及理由:
      - 分配股利、利润或偿付利息支付的现金(ASSIGN_DIVIDEND_PORFIT):
        股利是对股东的回报, 不应从 FCF 扣除; 利息虽是融资成本, 但该科目无法与股利拆分,
        且财务费用已在经营现金流中体现, 故不调整
      - 投资支付的现金(INVEST_PAY_CASH): 多为购买理财/金融资产等资金配置行为,
        不属于维持经营的资本开支, 扣除会扭曲主业造血能力 -> 不调整

本脚本功能:
    读取股票列表 csv (默认 stock_A_list.csv) -> 逐个公司拉取现金流量表(东财) ->
    计算最近 n_years 个完整会计年度(从2026年往前: 2025/2024/2023/2022/2021)的年度 FCF ->
    连续 n_years 年 FCF 均为正值的公司写入输出 csv (默认 stock_FCF_list.csv)。

    输出csv除各年FCF外, 还包含"平均增长率(%)": 近5个年度FCF的复合增长率(CAGR),
    即 (FCF末年/FCF首年)^(1/(年数-1)) - 1, 比同比增速的算术平均更稳健(不受中间年份波动和低基数影响)。

数据来源: akshare stock_cash_flow_sheet_by_report_em (现金流量表按报告期, 元 -> 统一换算为万元)
输出说明: 股票代码补齐前导零保证6位数字; 全部FCF及构成科目均以万元为统计单位。

用法:
    python findFCF.py
"""

import pandas as pd
import akshare as ak
import sys, os
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # 脚本所在目录（工程当前目录）
MAX_WORKERS = 8      # 并行线程数（网络IO密集型，可按需调整）
N_YEARS = 5          # 检查的年报年数


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
# 单只股票: 计算最近 n_years 个完整会计年度的年度自由现金流
# ============================================================
def calc_fcf_annual(code, n_years=N_YEARS):
    """
    拉取该公司现金流量表(按报告期), 取最近 n_years 份年报, 计算各年度自由现金流。

    详细口径:
        FCF = 经营活动现金流净额
            - 购建固定资产、无形资产和其他长期资产支付的现金 (资本支出)
            + 处置固定资产、无形资产和其他长期资产收回的现金净额
            - 取得子公司及其他营业单位支付的现金净额 (并购支出)
            + 处置子公司及其他营业单位收到的现金净额 (出售子公司回收)
        (老报表若缺某明细科目, 按该科目为 0 处理)

    返回 DataFrame(列: 年份/经营现金流净额/资本支出/处置长期资产回收/并购净支出/FCF,
    统计单位万元, 按年份升序); 已公告年报不足 n_years 份(次新股)时返回 None。
    """
    code_with_market = _with_market(code)
    df = ak.stock_cash_flow_sheet_by_report_em(symbol=code_with_market)

    df['REPORT_DATE'] = pd.to_datetime(df['REPORT_DATE'])
    df['NOTICE_DATE'] = pd.to_datetime(df['NOTICE_DATE'])

    # 只保留年报(报告期末为12-31)且已公告的
    df = df[df['REPORT_DATE'].dt.month == 12].copy()
    df = df.dropna(subset=['NOTICE_DATE'])
    df = df[df['NOTICE_DATE'] <= pd.Timestamp.now()]

    # 取最近 n_years 份年报
    df = df.sort_values('REPORT_DATE', ascending=False).head(n_years)
    if len(df) < n_years:
        return None

    # 明细科目缺失(老报表/行业差异)按 0 处理
    for c in ['DISPOSAL_LONG_ASSET', 'OBTAIN_SUBSIDIARY_OTHER', 'DISPOSAL_SUBSIDIARY_OTHER']:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = df[c].fillna(0.0)

    # 统一换算为万元 (元 -> 万元)
    df['并购净支出'] = (df['OBTAIN_SUBSIDIARY_OTHER'] - df['DISPOSAL_SUBSIDIARY_OTHER']) / 1e4
    df['经营现金流净额'] = df['NETCASH_OPERATE'] / 1e4
    df['资本支出'] = df['CONSTRUCT_LONG_ASSET'] / 1e4
    df['处置长期资产回收'] = df['DISPOSAL_LONG_ASSET'] / 1e4

    # FCF = 经营现金流净额 - 资本支出 + 处置长期资产回收 - 并购净支出
    df['FCF'] = df['经营现金流净额'] - df['资本支出'] + df['处置长期资产回收'] - df['并购净支出']
    df['年份'] = df['REPORT_DATE'].dt.year

    out = df[['年份', '经营现金流净额', '资本支出', '处置长期资产回收', '并购净支出', 'FCF']].copy()
    return out.sort_values('年份').reset_index(drop=True)


# ============================================================
# 线程池 worker: 判断是否连续 n_years 年 FCF 为正
# ============================================================
def check_fcf_positive(code_plain, name, n_years=N_YEARS):
    """
    满足"最近 n_years 年年报 FCF 全部为正"返回一行结果 dict, 否则返回 None。
    (现金流数据缺失/拉取失败/年报不足/存在负值或零值 均不入选)
    统计单位: 万元; 股票代码补齐前导零保证 6 位。
    """
    code_plain = str(code_plain).strip().zfill(6)   # 补齐前导零, 保证 6 位数字
    rec = {'股票代码': code_plain, '股票名称': name}
    try:
        df_fcf = calc_fcf_annual(code_plain, n_years)
        if df_fcf is None:
            print(f'[跳过] {code_plain} {name} 已公告年报不足 {n_years} 份(次新股)')
            return None

        # 必须无缺失且全部为正
        if df_fcf['FCF'].isna().any() or not (df_fcf['FCF'] > 0).all():
            neg_years = df_fcf[df_fcf['FCF'] <= 0]['年份'].tolist()
            print(f'[排除] {code_plain} {name} 非连续{n_years}年FCF为正, 不达标年份: {neg_years}')
            return None

        # 满足条件 -> 组装输出行 (各年FCF + 合计 + 年均 + 平均增长率 + 主要驱动科目均值)
        for _, r in df_fcf.iterrows():
            rec[f'{int(r["年份"])}年FCF'] = round(r['FCF'], 2)
        rec[f'{n_years}年FCF合计'] = round(df_fcf['FCF'].sum(), 2)
        rec[f'{n_years}年FCF年均'] = round(df_fcf['FCF'].mean(), 2)

        # 平均增长率(%): 近4个年度FCF的复合增长率 CAGR
        # CAGR = (FCF末年/FCF首年)^(1/(年数-1)) - 1
        # (入选公司各年FCF均>0, CAGR必然有定义; df_fcf 已按年份升序)
        fcf_vals = df_fcf['FCF'].values
        cagr = ((fcf_vals[-1] / fcf_vals[0]) ** (1.0 / (len(fcf_vals) - 1)) - 1) * 100
        rec['平均增长率(%)'] = round(float(cagr), 2)

        # 透明化: 输出主要构成项的年均值, 便于核查公司靠什么产生FCF
        rec['年均经营现金流净额'] = round(df_fcf['经营现金流净额'].mean(), 2)
        rec['年均资本支出'] = round(df_fcf['资本支出'].mean(), 2)
        rec['年均并购净支出'] = round(df_fcf['并购净支出'].mean(), 2)
        return rec

    except Exception as e:
        print(f'[失败] {code_plain} {name}: {e}')
        return None


# ============================================================
# 主流程: 读取csv -> 多线程逐个计算 -> 输出csv
# ============================================================
def run_fcf_screen(csv_path=os.path.join(BASE_DIR, 'stock_A_list.csv'),
                   output_csv=os.path.join(BASE_DIR, 'stock_FCF_list.csv'),
                   n_years=N_YEARS, max_workers=MAX_WORKERS):
    """
    从 csv_path 读取股票列表（列: 代码/名称，代码带 sh/sz/bj 前缀），
    多线程并行检查每只股票最近 n_years 年年报 FCF 是否连续为正，
    满足条件的公司写入 output_csv（按 n_years 年FCF合计降序）。

    - bj 开头的北交所股票直接跳过不处理
    - 每 100 只落盘一次，防止长时间运行中断丢数据
    """
    df_list = pd.read_csv(csv_path, encoding='utf-8-sig', dtype={'代码': str})

    # 组装任务列表（bj 开头的北交所股票直接跳过不处理）
    tasks = []
    skipped = 0
    for _, row in df_list.iterrows():
        raw_code = str(row['代码']).strip()
        name = str(row['名称']).strip()
        if raw_code.lower().startswith('bj'):
            skipped += 1
            continue
        # 去掉 sh/sz/bj 前缀，补齐前导零保证6位数字
        code_plain = raw_code[2:] if raw_code[:2].isalpha() else raw_code
        code_plain = code_plain.zfill(6)
        tasks.append((code_plain, name))

    total = len(tasks)
    results = []
    done = 0
    print(f'===== 共 {total} 只股票（已跳过 {skipped} 只 bj 北交所股票），'
          f'{max_workers} 线程并行检查最近 {n_years} 年 FCF =====')

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(check_fcf_positive, c, n, n_years) for c, n in tasks]
        for fut in as_completed(futures):
            rec = fut.result()
            done += 1

            if rec is not None:
                results.append(rec)
                print(f'[{done}/{total}] {rec["股票代码"]} {rec["股票名称"]} '
                      f'入选: {n_years}年FCF合计 {rec[f"{n_years}年FCF合计"]} 万元')

            # 每 100 只落盘一次（先写临时文件再替换，避免中断产生损坏文件）
            if done % 100 == 0:
                tmp = output_csv + '.tmp'
                pd.DataFrame(results).to_csv(tmp, index=False, encoding='utf-8-sig')
                os.replace(tmp, output_csv)
                print(f'[checkpoint] 已完成 {done}/{total}，当前入选 {len(results)} 只，'
                      f'中间结果已写入 {output_csv}')

    # 最后统一输出（按 n_years 年FCF合计降序）
    df_out = pd.DataFrame(results)
    if len(df_out) > 0:
        df_out = df_out.sort_values(f'{n_years}年FCF合计', ascending=False)
    tmp = output_csv + '.tmp'
    df_out.to_csv(tmp, index=False, encoding='utf-8-sig')
    os.replace(tmp, output_csv)

    print(f'\n===== 全部完成，连续 {n_years} 年 FCF 为正的公司共 {len(df_out)} 家，'
          f'已保存: {output_csv} =====')
    return df_out


# ============================================================
# 测试入口
# ============================================================
if __name__ == '__main__':
    df_out = run_fcf_screen()

    print()
    print(f'=== 连续{N_YEARS}年FCF为正的公司(按{N_YEARS}年FCF合计降序) ===')
    print(df_out.to_string(index=False))
