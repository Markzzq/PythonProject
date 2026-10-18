# -*- coding: utf-8 -*-
"""
高阶指标对照分析
================
功能: 以交互式 HTML 图表展示 A股核心指数自 2010 年以来的走势对照
    - 横坐标: 时间(日线)
    - 左侧Y轴: 指数实际收盘点位 (基础指数)
    - 右侧Y轴: 派生比价指标数值 (如 创业板指/中证红利)
    - 页面顶部提供多选框, 可勾选/取消任意指数/比价指标进行组合对比,
      各指标以不同颜色区分

数据源: akshare stock_zh_index_daily (新浪指数日线, 全历史)
输出:   高阶指标对照分析.html (交互网页, 浏览器直接打开)
"""

import os
import datetime

import akshare as ak
import pandas as pd
import plotly.graph_objects as go

# ===================== 全局配置参数 (可按需调整) =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

START_DATE = '2010-01-01'                                   # 数据起始日期
END_DATE = datetime.date.today().strftime('%Y-%m-%d')       # 数据截止日期(默认今天)
OUTPUT_HTML = os.path.join(BASE_DIR, '高阶指标对照分析.html')  # 输出HTML文件路径
CHART_TITLE = 'A股核心指数走势对照'                          # 图表/网页标题

# 基础指数清单(显示在左侧Y轴): 代码(新浪格式) / 显示名称 / 线条颜色
BASE_INDEX_LIST = [
    {'code': 'sh000001', 'name': '上证指数',   'color': '#E53935'},   # 红
    {'code': 'sz399006', 'name': '创业板指',   'color': '#1E88E5'},   # 蓝
    {'code': 'sh000688', 'name': '科创50指数', 'color': '#43A047'},   # 绿
]

# 派生比价指标清单(显示在右侧Y轴): 名称 / 分子指数代码 / 分母指数代码 / 颜色
RATIO_INDEX_LIST = [
    {'name': '创业板指/中证红利', 'numerator': 'sz399006', 'denominator': 'sh000922', 'color': '#8E24AA'},   # 紫
]
# ====================================================================


def fetch_index_daily(code, start_date=START_DATE, end_date=END_DATE):
    """
    拉取单个指数的日线全历史, 截取 [start_date, end_date] 区间。
    多数据源回退: 新浪 -> 腾讯 -> 东财, 取数据最新的一份。
    返回 DataFrame(列: date/close), 按日期升序。
    """
    plain_code = code[2:] if code[:2].isalpha() else code

    def _norm_sina_tx(df):
        df = df.rename(columns={'date': 'date', 'close': 'close'})
        df['date'] = pd.to_datetime(df['date'])
        return df[['date', 'close']]

    def _norm_em(df):
        # 东财字段为中文
        col_map = {'日期': 'date', '收盘': 'close'}
        df = df.rename(columns=col_map)
        df['date'] = pd.to_datetime(df['date'])
        return df[['date', 'close']]

    sources = [
        ('新浪', lambda: _norm_sina_tx(ak.stock_zh_index_daily(symbol=code))),
        ('腾讯', lambda: _norm_sina_tx(ak.stock_zh_index_daily_tx(symbol=code))),
        ('东财', lambda: _norm_em(ak.index_zh_a_hist(
            symbol=plain_code, period='daily',
            start_date=start_date.replace('-', ''), end_date=end_date.replace('-', '')))),
    ]

    cutoff = pd.Timestamp(end_date) - pd.Timedelta(days=45)  # 数据尾部需在45天内, 否则换下一个源
    best = None
    for name, fn in sources:
        try:
            df = fn()
            if df is None or df.empty:
                continue
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            df = df.sort_values('date').reset_index(drop=True)
            if df.empty:
                continue
            if best is None or df['date'].iloc[-1] > best['date'].iloc[-1]:
                best = df
            if df['date'].iloc[-1] >= cutoff:
                print(f'  [源] {name} 提供 {code} 数据, 截止 {df["date"].iloc[-1]:%Y-%m-%d}')
                return df
        except Exception as e:
            print(f'  [源] {name} 拉取 {code} 失败: {type(e).__name__}')
    return best


def compute_ratio(df_num, df_den, name):
    """
    计算两个指数的比值序列: 分子 / 分母。
    按日期对齐(取交集), 返回 DataFrame(列: date/close), close 为比值。
    """
    merged = pd.merge(df_num, df_den, on='date', suffixes=('_num', '_den'))
    merged = merged[merged['close_den'] != 0].copy()
    merged['close'] = merged['close_num'] / merged['close_den']
    return merged[['date', 'close']].sort_values('date').reset_index(drop=True)


def build_figure(trace_specs):
    """
    trace_specs: [{'df': DataFrame, 'name': str, 'color': str, 'axis': 'y'|'y2', 'dash': str}, ...]
    按顺序添加折线, axis='y2' 的 trace 绑定到右侧Y轴。
    """
    fig = go.Figure()
    for spec in trace_specs:
        df = spec['df']
        if df is None or df.empty:
            continue
        axis = spec.get('axis', 'y')
        dash = spec.get('dash', 'solid')
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['close'],
            mode='lines', name=spec['name'],
            line=dict(color=spec['color'], width=1.5, dash=dash),
            yaxis=axis,
            hovertemplate='%{x|%Y-%m-%d}<br>数值: %{y:.4f}<extra>' + spec['name'] + '</extra>',
        ))

    fig.update_layout(
        title=CHART_TITLE + f' ({START_DATE} 至今)',
        xaxis_title='时间',
        yaxis=dict(title='指数点位', side='left'),
        yaxis2=dict(title='比价指标', overlaying='y', side='right'),
        hovermode='x unified',
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
        height=650,
    )
    return fig


def export_html(fig, all_items, output_path=OUTPUT_HTML):
    """
    all_items: [{'name': str, 'color': str}, ...]  按 trace 顺序, 用于生成多选框。
    顶部多选框颜色与对应折线一致, 勾选状态通过 Plotly.restyle 联动折线显隐。
    """
    chart_div = fig.to_html(full_html=False, include_plotlyjs='cdn', div_id='indexChart')

    boxes = []
    for i, item in enumerate(all_items):
        boxes.append(
            f'<label style="color:{item["color"]};font-weight:bold;margin-right:18px;cursor:pointer;">'
            f'<input type="checkbox" class="idx-cb" data-i="{i}" checked '
            f'style="accent-color:{item["color"]};"> {item["name"]}</label>'
        )
    panel_html = '\n        '.join(boxes)

    js = """
const gd = document.getElementById('indexChart');
document.querySelectorAll('.idx-cb').forEach(function (cb) {
    cb.addEventListener('change', function () {
        const vis = [];
        document.querySelectorAll('.idx-cb').forEach(function (c) {
            vis.push(c.checked ? true : 'legendonly');
        });
        Plotly.restyle(gd, 'visible', vis);
    });
});
"""
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{CHART_TITLE}</title>
<style>
  body {{ font-family: "Microsoft YaHei", sans-serif; margin: 20px; }}
  #panel {{ padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px;
           display: inline-block; background: #fafafa; margin-bottom: 8px; }}
  .hint {{ color:#888; font-size:12px; margin-top:6px; }}
</style>
</head>
<body>
<h3>{CHART_TITLE}</h3>
<div id="panel">
    <span style="margin-right:14px;color:#666;">勾选需要对比的指标:</span>
        {panel_html}
</div>
<div class="hint">左侧Y轴: 指数点位 &nbsp;|&nbsp; 右侧Y轴: 比价指标(虚线)</div>
{chart_div}
<script>{js}</script>
</body>
</html>"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[完成] 交互图表已保存: {output_path}')


def main():
    """
    主流程:
    1. 收集所有需要的基础指数代码(基础指数 + 比价指标的分子/分母)
    2. 逐个拉取日线
    3. 组装 trace 列表: 基础指数 -> 左轴实线, 比价指标 -> 右轴虚线
    4. 构建图表并导出带多选框的交互HTML
    """
    # 收集所有需拉取的基础指数代码(去重)
    needed_codes = set(item['code'] for item in BASE_INDEX_LIST)
    for r in RATIO_INDEX_LIST:
        needed_codes.add(r['numerator'])
        needed_codes.add(r['denominator'])

    # 逐个拉取
    code_to_df = {}
    for code in sorted(needed_codes):
        try:
            df = fetch_index_daily(code)
            if df.empty:
                print(f'[跳过] {code}: 区间内无数据')
                continue
            code_to_df[code] = df
            print(f'[数据] {code}: {df["date"].iloc[0]:%Y-%m-%d} ~ {df["date"].iloc[-1]:%Y-%m-%d}, '
                  f'共 {len(df)} 个交易日')
        except Exception as e:
            print(f'[失败] {code}: {e}')

    if not code_to_df:
        print('无有效指数数据, 终止')
        return

    # 组装 trace 规格列表 (顺序决定图例与多选框顺序)
    trace_specs = []
    all_items = []  # 用于生成多选框

    # 基础指数(左轴)
    for cfg in BASE_INDEX_LIST:
        df = code_to_df.get(cfg['code'])
        if df is None:
            continue
        trace_specs.append({'df': df, 'name': cfg['name'], 'color': cfg['color'],
                            'axis': 'y', 'dash': 'solid'})
        all_items.append({'name': cfg['name'], 'color': cfg['color']})

    # 比价指标(右轴)
    for r in RATIO_INDEX_LIST:
        df_num = code_to_df.get(r['numerator'])
        df_den = code_to_df.get(r['denominator'])
        if df_num is None or df_den is None:
            print(f'[跳过] {r["name"]}: 分子或分母数据缺失')
            continue
        df_ratio = compute_ratio(df_num, df_den, r['name'])
        if df_ratio.empty:
            print(f'[跳过] {r["name"]}: 无可对齐日期')
            continue
        trace_specs.append({'df': df_ratio, 'name': r['name'], 'color': r['color'],
                            'axis': 'y2', 'dash': 'dot'})
        all_items.append({'name': r['name'], 'color': r['color']})
        print(f'[比价] {r["name"]}: 对齐后 {len(df_ratio)} 个交易日, '
              f'当前值 {df_ratio["close"].iloc[-1]:.4f}')

    if not trace_specs:
        print('无有效指标可绘制, 终止')
        return

    fig = build_figure(trace_specs)
    export_html(fig, all_items)


if __name__ == '__main__':
    main()
