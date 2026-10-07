# -*- coding: utf-8 -*-
"""
DCF（未来现金流折现）估值模型
================================
原理：公司内在价值 = 未来每年自由现金流折现到今天的总和

    PV = Σ CF_t / (1 + r)^t          （前 N 年，按分段增长率逐年推算）
    终值 TV = CF_{N+1} / (r - g_term)（第 N 年后按永续增速 g_term 永远增长）
    内在价值 = 前 N 年现值合计 + 终值现值

运行：python dcf_估值模型.py
依赖：仅 Python 标准库，无第三方包。
所有可调数字都在下方「参数区」，改完直接运行即可。
"""

# ============================================================
# 参数区（所有可调数字都在这里，按需修改）
# ============================================================

# --- 现金流基础 ---
FCF0 = 100.0          # 当期自由现金流（亿元）：= 净利润 + 折旧摊销 − 维持性资本开支

# --- 增长率（可分段，示例 = 前 3 年 8%、接着 4 年 6%、再 3 年 4%，共 10 年）
# 默认与正文讲解一致："前 10 年统一 8%" = STAGES = [(10, 0.08)]
# 想用分段模型改成：STAGES = [(3, 0.08), (4, 0.06), (3, 0.04)]
STAGES = [
    (10, 0.08),       # (年限, 年增长率) 第一段：高增长期
]
G_TERMINAL = 0.03     # 永续增速（第 10 年以后，永远按此增长；建议 2%–3% 封顶，≈GDP/通胀）

# --- 贴现率（折现率）---
R_DISCOUNT = 0.05     # 贴现率：无风险利率（如长期国债）+ 风险溢价；巴菲特做法≈长期无风险利率

# --- 市场对比（用于判断低估/高估）---
MARKET_CAP = 6000.0   # 当前总市值（亿元）
SHARES = None         # 总股本（亿股）。填了才输出"每股价值 vs 当前股价"；不填填 None
PRICE = None          # 当前股价（元/股）。与 SHARES 一起填，输出每股口径；不填填 None

# --- 安全边际（只买打折的锚）---
SAFETY_MARGIN = 0.70  # 买入阈值：市值 ≤ 内在价值 × 该系数 才算"有安全边际"

# --- 增长率自洽检查（可选，用于验证 g 是否合理）---
ROIC = 0.15           # 增量资本回报率：每投入 1 元新资本能赚回多少
REINVEST_RATE = 0.53  # 再投资率：赚到的钱里有多大比例再投回生意（可持续 g ≈ ROIC×再投资率）

# --- 敏感性分析范围 ---
SENS_R_MIN = 0.040    # 贴现率敏感性下限
SENS_R_MAX = 0.060    # 贴现率敏感性上限
SENS_R_STEP = 0.005   # 贴现率敏感性步长
SENS_G_MIN = 0.020    # 永续增速敏感性下限
SENS_G_MAX = 0.040    # 永续增速敏感性上限
SENS_G_STEP = 0.005   # 永续增速敏感性步长

# ============================================================
# 以下为模型实现，一般无需修改
# ============================================================

def build_cashflows(fcf0, stages, g_terminal):
    """按分段增长率生成未来各年现金流及终值。
    返回: (years, 逐年现金流列表, 终值)
    """
    cf_list = []
    cf = fcf0
    for years, growth in stages:
        for _ in range(years):
            cf = cf * (1 + growth)
            cf_list.append(cf)
    # 终值 = 第 N+1 年现金流 / (r - g_terminal)
    terminal_cf = cf * (1 + g_terminal)
    return cf_list, terminal_cf


def dcf_value(fcf0, stages, g_terminal, r):
    """两阶段/多阶段 DCF：返回 (内在价值, 前N年现值, 终值现值, 终值占比, 逐年明细)"""
    cf_list, terminal_cf = build_cashflows(fcf0, stages, g_terminal)
    n = len(cf_list)
    if r <= g_terminal:
        raise ValueError(f"贴现率 r({r:.2%}) 必须大于永续增速 g_terminal({g_terminal:.2%})，否则模型发散")
    pv_list = []
    for t, cf in enumerate(cf_list, start=1):
        pv = cf / (1 + r) ** t
        pv_list.append(pv)
    pv_phase1 = sum(pv_list)                          # 前 N 年现值合计
    terminal_value = terminal_cf / (r - g_terminal)   # 终值（第 N 年末）
    pv_terminal = terminal_value / (1 + r) ** n       # 终值折回今天
    total = pv_phase1 + pv_terminal
    share_terminal = pv_terminal / total if total else 0
    detail = list(zip(range(1, n + 1), cf_list, pv_list))
    return total, pv_phase1, pv_terminal, share_terminal, detail


def format_ratio(x):
    return f"{x*100:.1f}%"


def main():
    print("=" * 68)
    print("DCF 估值模型（未来现金流折现）")
    print("=" * 68)

    # ---------- 1. 输入回显 ----------
    print("\n【输入参数】")
    print(f"  当期自由现金流 FCF₀        : {FCF0:>10.1f} 亿元")
    stage_desc = " → ".join(f"{y}年×{format_ratio(g)}" for y, g in STAGES)
    print(f"  前 {sum(y for y, _ in STAGES)} 年增长率（分段） : {stage_desc}")
    print(f"  永续增速 g_terminal        : {G_TERMINAL:>10.2%}")
    print(f"  贴现率 r                   : {R_DISCOUNT:>10.2%}")
    print(f"  当前总市值                 : {MARKET_CAP:>10.1f} 亿元")

    # ---------- 2. 主体计算 ----------
    total, pv1, pvt, share_t, detail = dcf_value(FCF0, STAGES, G_TERMINAL, R_DISCOUNT)
    n = len(detail)

    print("\n【逐年现金流折现明细】")
    print(f"  {'年份':>4} {'现金流(亿)':>12} {'折现因子':>10} {'现值(亿)':>12}")
    for year, cf, pv in detail:
        factor = 1 / (1 + R_DISCOUNT) ** year
        print(f"  {year:>4} {cf:>12.1f} {factor:>10.4f} {pv:>12.1f}")

    print("\n【估值结果】")
    print(f"  前 {n} 年现金流现值合计      : {pv1:>12.1f} 亿元")
    print(f"  终值（永续）现值            : {pvt:>12.1f} 亿元")
    print(f"  → 内在价值（股权价值）     : {total:>12.1f} 亿元")
    print(f"  终值占比                   : {share_t:>12.1%} （越大说明远期假设越关键）")

    # ---------- 3. 每股口径 ----------
    if SHARES is not None and SHARES > 0:
        per_share = total / SHARES
        print(f"\n【每股口径】总股本 {SHARES:.2f} 亿股")
        print(f"  每股内在价值               : {per_share:>10.2f} 元/股")
        if PRICE is not None and PRICE > 0:
            upside = (per_share / PRICE - 1) * 100
            print(f"  当前股价 {PRICE} 元 → 隐含空间 {upside:+.1f}%")

    # ---------- 4. 低估 / 高估判断 ----------
    ratio = MARKET_CAP / total
    margin_implied = 1 - ratio
    print("\n【当前市值 vs 内在价值】")
    print(f"  市值 / 内在价值             : {ratio:>10.2%}")
    if ratio < SAFETY_MARGIN:
        verdict = "低估（已进入安全边际区）"
    elif ratio < 1.0:
        verdict = "偏低估（低于内在价值，但安全边际不足）"
    elif ratio < 1.2:
        verdict = "合理（价格与价值基本相当）"
    else:
        verdict = "高估（价格明显高于内在价值）"
    print(f"  结论                       : {verdict}")
    print(f"  安全边际买入线（{format_ratio(SAFETY_MARGIN)}×价值）: {total*SAFETY_MARGIN:.1f} 亿"
          f"（当前市值需 ≤ 该值才符合巴菲特式买入）")
    print(f"  当前相对内在价值的隐含折扣  : {margin_implied:>10.1%}")

    # ---------- 5. 增长率自洽检查 ----------
    g_sustainable = ROIC * REINVEST_RATE
    max_g = max((g for _, g in STAGES), default=0)
    print("\n【增长率自洽检查】")
    print(f"  可持续增长率 g≈ROIC×再投资率: {g_sustainable:>10.2%}  (ROIC={ROIC:.0%} × {REINVEST_RATE:.0%})")
    print(f"  模型用的最高增长率          : {max_g:>10.2%}")
    if max_g > g_sustainable * 1.5:
        print("  ⚠ 高增长阶段远超 ROIC 支撑上限（>1.5 倍），增长假设可能过于乐观")
    else:
        print("  高增长假设在 ROIC 支撑范围内，基本自洽")

    # ---------- 6. 敏感性分析 ----------
    print("\n【敏感性分析：贴现率 r 变化 → 内在价值（亿元）】")
    print(f"  {'r':>8} {'内在价值':>12} {'较基准':>10}")
    for r in _frange(SENS_R_MIN, SENS_R_MAX, SENS_R_STEP):
        v, *_ = dcf_value(FCF0, STAGES, G_TERMINAL, r)
        chg = (v / total - 1) * 100
        print(f"  {r:>7.1%} {v:>12.1f} {chg:>+9.1f}%")

    print("\n【敏感性分析：永续增速 g 变化 → 内在价值（亿元）】")
    print(f"  {'g':>8} {'内在价值':>12} {'较基准':>10}")
    for g in _frange(SENS_G_MIN, SENS_G_MAX, SENS_G_STEP):
        v, *_ = dcf_value(FCF0, STAGES, g, R_DISCOUNT)
        chg = (v / total - 1) * 100
        print(f"  {g:>7.1%} {v:>12.1f} {chg:>+9.1f}%")

    # ---------- 7. 结论 ----------
    print("\n【结论】")
    print(f"  在 r={R_DISCOUNT:.1%}、前{n}年分段增长、永续{G_TERMINAL:.1%} 的假设下，")
    print(f"  该标的的内在价值约为 {total:,.0f} 亿元；当前市值 {MARKET_CAP:,.0f} 亿元 → {verdict}。")
    print("  提醒：DCF 是估值框架不是精确预测，请结合情景法（悲观/中性/乐观）使用区间判断。")
    print("=" * 68)


def _frange(start, stop, step):
    """浮点等差数列（避免浮点误差丢末尾点）"""
    n = int(round((stop - start) / step)) + 1
    for i in range(n):
        yield start + i * step


if __name__ == "__main__":
    main()
