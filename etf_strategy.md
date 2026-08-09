# ETF 日频打分策略文档

> 最后更新：2026-08-02  
> 源文件：`analyzeCoreETF_DayScore.py`、`scoring_engine.py`、`market_regime.py`、`MyTT.py`

---

## 一、整体流程

```
数据库读取K线
  → calculate_indicators(df)        # 用 MyTT 计算底层指标 → 写入 DataFrame 列
  → extract_indicator_values(df)    # 从 DataFrame 提取 19 个可打分指标值（含金叉死叉判断）
  → detect_market_regime(df)        # 检测当前市场状态 → regime
  → calculate_total_score(...)      # 根据 regime 自适应阈值，对 19 个指标逐一打分
  → 趋势加成/惩罚                  # 顺势信号加分，逆势信号扣分
  → ETF特有指标加分                 # 折溢价率、资金流向、份额变化
  → 最终信号判定                   # 总得分 vs 买入/卖出阈值 → 建议
```

---

## 二、MyTT 底层指标计算

**`calculate_indicators(df)` 共调用 23 个 MyTT 函数，产出 41 个 DataFrame 列：**

| 指标 | MyTT 函数 | 参数 | 产出列 |
|------|-----------|------|--------|
| MACD | `MACD(close, 12, 26, 9)` | — | `dif` `dea` `macd` |
| KDJ | `KDJ(close, high, low, 9, 3, 3)` | — | `k` `d` `j` |
| RSI(6) | `RSI(close, 6)` | — | `rsi_6` |
| RSI(12) | `RSI(close, 12)` | — | `rsi_12` |
| RSI(24) | `RSI(close, 24)` | — | `rsi_24` |
| BOLL | `BOLL(close, 20, 2)` | — | `boll_upper` `boll_mid` `boll_lower` |
| BIAS(6) | `BIAS(close, 6)` | — | `bias_6` |
| BIAS(12) | `BIAS(close, 12)` | — | `bias_12` |
| BIAS(24) | `BIAS(close, 24)` | — | `bias_24` |
| MA(5/10/20/60) | `MA(close, N)` | ×4 | `ma5` `ma10` `ma20` `ma60` |
| CCI | `CCI(close, high, low, 14)` | — | `cci` |
| WR(10/6) | `WR(close, high, low, 10, 6)` | — | `wr` `wr1` |
| DMI | `DMI(close, high, low, 14, 6)` | — | `pdi` `mdi` `adx` `adxr` |
| ATR | `ATR(close, high, low, 14)` | — | `atr` |
| PSY | `PSY(close, 12, 6)` | — | `psy` `psyma` |
| VR | `VR(close, volume, 26)` | — | `vr` |
| MFI | `MFI(close, high, low, volume, 14)` | — | `mfi` |
| OBV | `OBV(close, volume)` | — | `obv` |
| SAR | `SAR(high, low, 0.02, 0.2)` | — | `sar` |
| CR | `CR(high, low, open, 26)` | — | `cr` `ma1` `ma2` `ma3` `ma4` |
| WAD | `WAD(high, low, close, open)` | — | `wad` |
| TEMA | `TEMA(close, 20)` | — | `tema` |
| MIDPRICE | `MIDPRICE(high, low, 14)` | — | `midprice` |
| VWAP | `VWAP(close, volume, 14)` | — | `vwap` |
| CMF | `CMF(high, low, close, volume, 14)` | — | `cmf` |
| VOLRATIO | `VOLRATIO(volume, 5)` | — | `volratio` |
| PRICEVOLUME | `PRICEVOLUME(close, volume, 14)` | — | `pricevolume` |

---

## 三、提取为可打分指标（19 个）

**`extract_indicator_values(df)` → 19 个指标值，传给评分引擎：**

| # | 指标名 | 来源 | 提取方式 | 取值含义 |
|---|--------|------|----------|----------|
| 1 | `MACD_DIF位置` | `dif` 末值 | 直接取 | DIF 数值 |
| 2 | `MACD金叉死叉` | `dif` vs `dea` | `CROSS(dif, dea)` | 1=金叉, -1=死叉, 0=无 |
| 3 | `MA5_MA10金叉死叉` | `ma5` vs `ma10` | `CROSS(ma5, ma10)` | 1=金叉, -1=死叉, 0=无 |
| 4 | `MA多头排列` | `ma5/ma10/ma20/ma60` | 链式比较 | 1=多头, 0.5=短多, -0.5=短空, -1=空头, 0=交织 |
| 5 | `价格vs MA20` | `close` vs `ma20` | `(c-ma20)/ma20*100` | 偏离百分比 |
| 6 | `价格vs MA60` | `close` vs `ma60` | `(c-ma60)/ma60*100` | 偏离百分比 |
| 7 | `RSI(14)` | `rsi_12` 末值 | 直接取 | RSI 数值（注意：实际用 RSI(12)） |
| 8 | `KDJ_K位置` | `k` 末值 | 直接取 | K 值 |
| 9 | `KDJ金叉死叉` | `k` vs `d` | `CROSS(k, d)` | 1=金叉, -1=死叉, 0=无 |
| 10 | `WR(10)` | `wr` 末值 | 取反 `-wr` | 负值，越大（越接近 0）→ 越超卖 |
| 11 | `BIAS(6)` | `bias_6` 末值 | 直接取 | 乖离率 |
| 12 | `量比` | `volratio` 末值 | 直接取 | 5 日均量比 |
| 13 | `CCI(14)` | `cci` 末值 | 直接取 | CCI 数值 |
| 14 | `ADX趋势强度` | `adx` 末值 | 直接取 | ADX 数值 |
| 15 | `DMI方向` | `pdi` - `mdi` | 手算 `pdi-mdi` | + 为多头方向, - 为空头方向 |
| 16 | `ATR波动率` | `high` `low` `atr` | `(high-low)/atr` | 当日波幅 vs ATR |
| 17 | `OBV趋势` | `obv` 近 5 日 | `obv[-1] > obv[-2]` | 1=上涨, -1=下跌, 0=无 |
| 18 | `MFI资金流量` | `mfi` 末值 | 直接取 | MFI 数值 |
| 19 | `price_trend_score` | `close` vs `ma20/ma60` | `(价vsMA20*0.6 + 价vsMA60*0.4)` 加权综合 | 趋势综合偏离度 |

**注意：以下 MyTT 计算产出列未参与打分（仅在 DataFrame 中存在）：**  
`psy` `psyma` `vr` `sar` `cr` `wad` `tema` `midprice` `vwap` `cmf` `pricevolume`（11 列）

---

## 四、打分规则（`INDICATOR_CONFIG`，共 19 条）

每条规则格式：`{name, weight, rules: [{condition, score}], adaptive_weight}`

### 趋势类（权重高）

| 指标 | 权重 | 规则 | 信号 |
|------|------|------|------|
| **MACD金叉死叉** | 3.0 | `==1` → `max*1.0` | 买入 |
| | | `==-1` → `min*0.8` | 卖出 |
| **MA多头排列** | 2.0 | `>=1` → `max*0.8` | 买入 |
| | | `>=0.5` → `max*0.4` | 买入 |
| | | `<=-1` → `min*0.6` | 卖出 |
| | | `<=-0.5` → `min*0.3` | 卖出 |
| **MA5_MA10金叉死叉** | 2.0 | `==1` → `max*0.7` | 买入 |
| | | `==-1` → `min*0.6` | 卖出 |
| **价格vs MA20** | 2.0 | `>1` → `max*0.6` | 买入 |
| | | `>0` → `max*0.3` | 买入 |
| | | `<-1` → `min*0.5` | 卖出 |
| | | `<0` → `min*0.2` | 卖出 |
| **价格vs MA60** | 1.5 | `>1` → `max*0.4` | 买入 |
| | | `>0` → `max*0.2` | 买入 |
| | | `<-1` → `min*0.4` | 卖出 |
| | | `<0` → `min*0.2` | 卖出 |

### 动量类

| 指标 | 权重 | 规则 | 信号 |
|------|------|------|------|
| **MACD_DIF位置** | 3.0 | `>0` → `max*0.6` | 买入 |
| | | `>0.05` → `max*0.8` | 买入 |
| | | `<0` → `min*0.5` | 卖出 |
| | | `<-0.05` → `min*0.8` | 卖出 |
| **RSI(14)** | 2.0 | `<30` → `max*0.8` | 买入(超卖) |
| | | `<40` → `max*0.4` | 买入 |
| | | `30~70` → `max*0.4` | 持有(中性) |
| | | `>70` → `min*0.8` | 卖出(超买) |
| | | `>60` → `min*0.4` | 卖出 |
| **KDJ_K位置** | 2.0 | `<20` → `max*0.8` | 买入 |
| | | `<40` → `max*0.3` | 买入 |
| | | `>80` → `min*0.8` | 卖出 |
| | | `>60` → `min*0.3` | 卖出 |
| **KDJ金叉死叉** | 2.0 | `==1` → `max*0.6` | 买入 |
| | | `==-1` → `min*0.5` | 卖出 |
| **WR(10)** | 1.5 | `<-80` → `max*0.7` | 买入(超卖) |
| | | `<-40` → `max*0.3` | 买入 |
| | | `>-20` → `min*0.6` | 卖出(超买) |
| **BIAS(6)** | 1.5 | `<-3` → `max*0.6` | 买入 |
| | | `<-1` → `max*0.3` | 买入 |
| | | `>3` → `min*0.6` | 卖出 |
| | | `>1` → `min*0.3` | 卖出 |
| **CCI(14)** | 1.5 | `<-100` → `max*0.7` | 买入 |
| | | `<-40` → `max*0.3` | 买入 |
| | | `>100` → `min*0.7` | 卖出 |
| | | `>40` → `min*0.3` | 卖出 |

### 成交量类

| 指标 | 权重 | 规则 | 信号 |
|------|------|------|------|
| **量比** | 2.0 | `>1.5` → `max*0.5` | 买入(放量) |
| | | `>1.0` → `max*0.2` | 买入 |
| | | `<0.5` → `min*0.3` | 卖出(缩量) |
| **OBV趋势** | 1.5 | `==1` → `max*0.4` | 买入(量增价升) |
| | | `==-1` → `min*0.3` | 卖出(量增价跌) |
| **MFI资金流量** | 1.5 | `<20` → `max*0.6` | 买入(超卖) |
| | | `<40` → `max*0.3` | 买入 |
| | | `>80` → `min*0.6` | 卖出(超买) |
| | | `>60` → `min*0.3` | 卖出 |

### 趋势/波动/综合类

| 指标 | 权重 | 规则 | 信号 |
|------|------|------|------|
| **ADX趋势强度** | 1.5 | `>25` → `max*0.5` | 买入(趋势明确) |
| | | `<20` → `min*0.3` | 卖出(无趋势) |
| **DMI方向** | 1.5 | `>0` → `max*0.5` | 买入(多头方向) |
| | | `<-10` → `min*0.4` | 卖出(空头) |
| | | `<0` → `min*0.2` | 卖出 |
| **ATR波动率** | 1.0 | `<1.0` → `max*0.3` | 买入(低波可能突破) |
| | | `>2.0` → `min*0.4` | 卖出(高波风险) |
| **price_trend_score** | 2.5 | `>1` → `max*0.5` | 买入 |
| | | `>0` → `max*0.2` | 买入 |
| | | `<-1` → `min*0.5` | 卖出 |
| | | `<0` → `min*0.2` | 卖出 |

---

## 五、市场状态检测（`market_regime.py` → 5 种状态）

| 状态 | ADX 条件 | PDI vs MDI | MA60 斜率 | 波动率 | 说明 |
|------|----------|------------|-----------|--------|------|
| `strong_bull` | ≥ 30 | PDI > MDI | 上升(>0.5%) | — | 强牛 |
| `bull` | ≥ 25 | PDI > MDI | 上升 | — | 弱牛 |
| `range` | ≤ 20 | — | — | — | 震荡 |
| `bear` | ≥ 25 | MDI > PDI | 下降 | — | 弱熊 |
| `strong_bear` | ≥ 30 | MDI > PDI | 下降(<-0.5%) | 高 | 强熊 |

---

## 六、自适应阈值（`get_adaptive_thresholds`）

基础阈值：`buy_threshold = 5.0`, `sell_threshold = -5.0`

| 市场状态 | buy 系数 | sell 系数 | 实际 buy | 实际 sell |
|----------|----------|-----------|----------|-----------|
| `strong_bull` | ×0.7 | ×1.3 | 3.5 | -6.5 |
| `bull` | ×0.85 | ×1.15 | 4.25 | -5.75 |
| `range` | ×1.0 | ×1.0 | 5.0 | -5.0 |
| `bear` | ×1.15 | ×0.85 | 5.75 | -4.25 |
| `strong_bear` | ×1.3 | ×0.7 | 6.5 | -3.5 |

牛市降低买入门槛、收紧卖出条件；熊市收紧买入条件、降低卖出门槛。

---

## 七、趋势加成/惩罚

```
price_trend_score > 0（趋势向上）:
  - 买入信号 → 加分：score × 0.2 × price_trend_score
  - 卖出信号 → 扣分：score × 0.15 × price_trend_score

price_trend_score < 0（趋势向下）:
  - 卖出信号 → 加分（顺势）：score × 0.2 × |price_trend_score|
  - 买入信号 → 扣分（逆势）：score × 0.3 × |price_trend_score|
```

---

## 八、ETF 特有指标加分（`get_etf_specific_indicators`）

| 指标 | 来源 | 加分条件 | 加分值 |
|------|------|----------|--------|
| 折溢价率 | `akshare fund_etf_fund_info_em` | < -0.5%（折价） | +1.0 |
| | | > 1.0%（溢价） | -0.5 |
| 资金净流入 | 同上 | > 0（净流入） | +1.0 |
| | | < -5000 万 | -1.0 |
| 份额变化率(5日) | `akshare fund_etf_share_em` | > 1% | +0.5 |
| | | < -1% | -0.5 |

各项获取失败时不影响总分（None 跳过）。

---

## 九、最终信号判定

```
total_score >= buy_threshold  → 买入信号
total_score <= sell_threshold → 卖出信号
否则                          → 持有不动
```

`buy_threshold` / `sell_threshold` 来源于第六节自适应阈值。

---

## 十、关键参数速查

| 参数 | 值 | 位置 |
|------|----|------|
| MACD | 12/26/9 | `MyTT.MACD` |
| KDJ | 9/3/3 | `MyTT.KDJ` |
| RSI | 6/12/24 | `MyTT.RSI` |
| BOLL | 20/2 | `MyTT.BOLL` |
| MA | 5/10/20/60 | `MyTT.MA` |
| DMI | 14/6 | `MyTT.DMI` |
| ATR | 14 | `MyTT.ATR` |
| 买入阈值(基础) | 5.0 | `scoring_engine` |
| 卖出阈值(基础) | -5.0 | `scoring_engine` |
| 最大分(max) | 1.0 | `scoring_engine` |
| 最小分(min) | -1.0 | `scoring_engine` |
