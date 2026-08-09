# -*- coding: utf-8 -*-
"""
声明式打分引擎
================
- 支持声明式指标配置 + 规则化打分
- NaN柔性处理：单个指标NaN只跳过该指标，不打压整只ETF
- Trend Bonus修复：买卖方向分离，避免循环依赖
- 分数表达式白名单安全求值（不使用eval）
"""

import operator as op
import numpy as np


# ===================== 安全表达式求值器 =====================
_SAFE_OPS = {
    'abs': op.abs,
    'max': max,
    'min': min,
    'round': round,
    '+': op.add,
    '-': op.sub,
    '*': op.mul,
    '/': op.truediv,
}

def _eval_score_expr(expr, value_dict):
    """安全求值分数表达式，仅支持白名单运算符"""
    expr = str(expr).strip()

    # 特殊表达式：'max', 'min', 'max*0.5', 'min*0.5' 等
    if expr in ('max', 'min'):
        return None  # 需要特殊处理

    if expr.startswith('max*'):
        factor = float(expr.replace('max*', '').strip())
        return None  # 需要特殊处理

    if expr.startswith('min*'):
        factor = float(expr.replace('min*', '').strip())
        return None  # 需要特殊处理

    # 字符串数字 → 直接返回
    try:
        return float(expr)
    except (ValueError, TypeError):
        pass

    # 安全的变量替换求值
    for var_name, var_value in value_dict.items():
        if var_name in expr:
            # 只替换完整的变量名
            import re
            expr = re.sub(r'\b' + re.escape(var_name) + r'\b', str(var_value), expr)

    try:
        result = float(eval(expr, {"__builtins__": {}}, {"abs": abs, "max": max, "min": min}))
        return result
    except Exception:
        return None


def _resolve_score(value, score_config, theoretical_max, theoretical_min):
    """
    根据配置解析得分：
    - 如果是固定数值，直接返回
    - 如果是 'max'/'min' 表达式，返回理论极值的对应分数
    """
    if isinstance(score_config, (int, float)):
        return float(score_config)

    s = str(score_config).strip()

    if s == 'max':
        return float(theoretical_max)
    if s == 'min':
        return float(theoretical_min)

    if s.startswith('max*'):
        factor = float(s.replace('max*', '').strip())
        return theoretical_max * factor

    if s.startswith('min*'):
        factor = float(s.replace('min*', '').strip())
        return theoretical_min * factor

    # 自定义表达式求值
    result = _eval_score_expr(s, {
        'theoretical_max': theoretical_max,
        'theoretical_min': theoretical_min,
    })
    if result is not None:
        return result

    return 0.0


# ===================== 信号阈值配置（支持自适应调整） =====================
SIGNAL_THRESHOLD_CONFIG = {
    'default': {
        'strong_buy': 18,
        'buy': 8,
        'sell': -8,
        'strong_sell': -18,
    },
    'regime_adjustments': {
        'strong_bull':   1.30,   # 强势牛市中阈值放宽
        'bull':          1.15,
        'range':         1.00,   # 震荡市不变
        'bear':          0.85,
        'strong_bear':   0.70,   # 弱势熊市中阈值收紧
    },
    'min_valid_indicators': 12,   # 最少有效指标数
}


def get_adaptive_thresholds(market_regime='range'):
    """
    根据市场状态返回自适应信号阈值
    regime: 'strong_bull', 'bull', 'range', 'bear', 'strong_bear'
    """
    base = SIGNAL_THRESHOLD_CONFIG['default'].copy()
    multiplier = SIGNAL_THRESHOLD_CONFIG['regime_adjustments'].get(
        market_regime, 1.0
    )
    return {
        key: value * multiplier
        for key, value in base.items()
    }


# ===================== 指标配置格式说明 =====================
# 每个指标的配置项：
#   name:       指标名称
#   weight:     权重（正数=同向，负数=反向）
#   value:      指标计算值（在外部预先计算好传入）
#   base_score: 基准分（默认0）
#   rules: 打分规则列表，每条规则：
#     - condition: 条件表达式，支持 {value} 占位符，如 "{value} > 0"
#     - score:  分数表达式，支持数字、'max'、'min'、'max*0.5' 等
#     - signal: 信号方向 'buy'/'sell'/'none' (选填)
#     - bonus:  趋势加成条件 'confirm'/'divergence'/'none' (选填)
#               'confirm': 同向确认（买入信号+上涨趋势→加分）
#               'divergence': 背离信号（买入信号+下跌趋势→加分）

# ===================== 声明式指标配置 =====================
INDICATOR_CONFIG = [
    # === 趋势类 ===
    {
        'name': 'MACD_DIF位置',
        'weight': 3,
        'rules': [
            {'condition': '{value} > 0', 'score': 'max*0.8', 'signal': 'buy', 'bonus': 'confirm'},
            {'condition': '{value} < 0', 'score': 'min*0.8', 'signal': 'sell', 'bonus': 'confirm'},
        ],
    },
    {
        'name': 'MACD金叉死叉',
        'weight': 3,
        'rules': [
            {'condition': '{value} == 1', 'score': 'max', 'signal': 'buy'},
            {'condition': '{value} == -1', 'score': 'min', 'signal': 'sell'},
        ],
    },
    {
        'name': 'MA5_MA10金叉死叉',
        'weight': 2.5,
        'rules': [
            {'condition': '{value} == 1', 'score': 'max*0.7', 'signal': 'buy'},
            {'condition': '{value} == -1', 'score': 'min*0.7', 'signal': 'sell'},
        ],
    },
    {
        'name': 'MA多头排列',
        'weight': 2,
        'rules': [
            {'condition': '{value} >= 1', 'score': 'max*0.6', 'signal': 'buy'},
            {'condition': '{value} <= -1', 'score': 'min*0.6', 'signal': 'sell'},
        ],
    },
    {
        'name': '价格vs MA20',
        'weight': 2,
        'rules': [
            {'condition': '{value} > 1.0', 'score': 'max*0.5', 'signal': 'buy'},
            {'condition': '{value} < -1.0', 'score': 'min*0.5', 'signal': 'sell'},
        ],
    },
    {
        'name': '价格vs MA60',
        'weight': 1.5,
        'rules': [
            {'condition': '{value} > 1.0', 'score': 'max*0.4', 'signal': 'buy'},
            {'condition': '{value} < -1.0', 'score': 'min*0.4', 'signal': 'sell'},
        ],
    },

    # === 动量类 ===
    {
        'name': 'RSI(14)',
        'weight': 2,
        'rules': [
            {'condition': '{value} > 70', 'score': 'max*0.2', 'signal': 'sell'},
            {'condition': '{value} < 30', 'score': 'max*0.8', 'signal': 'buy'},
            {'condition': '30 <= {value} <= 70', 'score': 'max*0.4'},
        ],
    },
    {
        'name': 'KDJ_K位置',
        'weight': 2,
        'rules': [
            {'condition': '{value} > 80', 'score': 'max*0.2', 'signal': 'sell'},
            {'condition': '{value} < 20', 'score': 'max*0.8', 'signal': 'buy'},
        ],
    },
    {
        'name': 'KDJ金叉死叉',
        'weight': 2,
        'rules': [
            {'condition': '{value} == 1', 'score': 'max*0.6', 'signal': 'buy'},
            {'condition': '{value} == -1', 'score': 'min*0.6', 'signal': 'sell'},
        ],
    },
    {
        'name': 'WR(10)',
        'weight': 1.5,
        'rules': [
            {'condition': '{value} < -80', 'score': 'max*0.7', 'signal': 'buy'},
            {'condition': '{value} > -20', 'score': 'min*0.7', 'signal': 'sell'},
        ],
    },

    # === 成交量类 ===
    {
        'name': '量比',
        'weight': 2,
        'rules': [
            {'condition': '{value} > 1.5', 'score': 'max*0.5', 'signal': 'buy'},
            {'condition': '{value} < 0.5', 'score': 'min*0.5', 'signal': 'sell'},
        ],
    },
    {
        'name': 'MFI资金流量',
        'weight': 1.5,
        'rules': [
            {'condition': '{value} > 80', 'score': 'min*0.5', 'signal': 'sell'},
            {'condition': '{value} < 20', 'score': 'max*0.6', 'signal': 'buy'},
        ],
    },
    {
        'name': 'OBV趋势',
        'weight': 1.5,
        'rules': [
            {'condition': '{value} > 0', 'score': 'max*0.4', 'signal': 'buy'},
            {'condition': '{value} < 0', 'score': 'min*0.4', 'signal': 'sell'},
        ],
    },

    # === 波动类 ===
    {
        'name': '布林带位置',
        'weight': 2,
        'rules': [
            {'condition': '{value} <= 0.1', 'score': 'max*0.6', 'signal': 'buy'},
            {'condition': '{value} >= 0.9', 'score': 'min*0.6', 'signal': 'sell'},
        ],
    },
    {
        'name': 'ATR波动率',
        'weight': 1,
        'rules': [
            {'condition': '{value} > 1.5', 'score': 'max*0.3', 'signal': 'buy'},
        ],
    },
    {
        'name': 'CCI(14)',
        'weight': 2,
        'rules': [
            {'condition': '{value} > 100', 'score': 'max*0.3', 'signal': 'buy'},
            {'condition': '{value} < -100', 'score': 'max*0.7', 'signal': 'buy'},
        ],
    },

    # === 趋势强度 ===
    {
        'name': 'ADX趋势强度',
        'weight': 1.5,
        'rules': [
            {'condition': '{value} > 25', 'score': 'max*0.5', 'signal': 'buy'},
            {'condition': '{value} < 20', 'score': 'min*0.5', 'signal': 'sell'},
        ],
    },
    {
        'name': 'DMI方向',
        'weight': 1.5,
        'rules': [
            {'condition': '{value} > 0', 'score': 'max*0.5', 'signal': 'buy'},
            {'condition': '{value} < 0', 'score': 'min*0.5', 'signal': 'sell'},
        ],
    },

    # === 乖离类 ===
    {
        'name': 'BIAS(6)',
        'weight': 1.5,
        'rules': [
            {'condition': '{value} > 5', 'score': 'min*0.5', 'signal': 'sell'},
            {'condition': '{value} < -5', 'score': 'max*0.6', 'signal': 'buy'},
        ],
    },
]


# ===================== 打分函数 =====================
def score_indicator(indicator_value, indicator_config):
    """
    对单个指标值按rules规则打分。
    
    Args:
        indicator_value: 指标当前值（标量）
        indicator_config: 配置字典，包含 name, weight, rules
    
    Returns:
        {
            'score': 分数（已乘权重后）,
            'signal': 'buy'/'sell'/None,
            'bonus': 'confirm'/'divergence'/None,
            'matched': 是否匹配到规则,
            'raw_score': 原始分数（未乘权重）
        }
    """
    if indicator_value is None or not np.isfinite(indicator_value):
        return {
            'score': 0.0, 'signal': None, 'bonus': None,
            'matched': False, 'raw_score': 0.0
        }

    weight = abs(indicator_config['weight'])
    raw_max = 10.0  # 单指标最大原始分
    raw_min = -10.0

    for rule in indicator_config.get('rules', []):
        condition = rule['condition'].replace('{value}', str(indicator_value))
        try:
            # 安全求值条件表达式
            local_ns = {'abs': abs, 'max': max, 'min': min, 'inf': float('inf')}
            cond_result = eval(condition, {"__builtins__": {}}, local_ns)
        except Exception:
            continue

        if cond_result:
            score_config = rule.get('score', 0)
            raw_score = _resolve_score(None, score_config, raw_max, raw_min)
            signal = rule.get('signal', None)
            bonus = rule.get('bonus', None)
            final_score = raw_score * weight / raw_max if raw_max != 0 else 0.0

            return {
                'score': final_score * np.sign(indicator_config['weight']),
                'signal': signal,
                'bonus': bonus,
                'matched': True,
                'raw_score': raw_score,
            }

    # 没有匹配到规则 → 默认中性
    return {
        'score': 0.0, 'signal': None, 'bonus': None,
        'matched': False, 'raw_score': 0.0,
    }


def calculate_total_score(indicator_values, indicator_config=None, market_regime='range'):
    """
    计算总分，支持NaN柔性处理。
    
    Args:
        indicator_values: {指标名: 指标值} 字典
        indicator_config: 指标配置列表，默认使用内置INDICATOR_CONFIG
        market_regime: 市场状态 'strong_bull'/'bull'/'range'/'bear'/'strong_bear'
    
    Returns:
        {
            'total_score': 总分,
            'signal': 'strong_buy'/'buy'/'hold'/'sell'/'strong_sell',
            'details': [{指标名, 得分, 信号, 匹配}],
            'valid_count': 有效指标数,
            'total_count': 总指标数,
            'indicator_scores': {指标名: 得分},
            'adaptive_thresholds': 自适应阈值,
        }
    """
    if indicator_config is None:
        indicator_config = INDICATOR_CONFIG

    thresholds = get_adaptive_thresholds(market_regime)
    min_valid = SIGNAL_THRESHOLD_CONFIG['min_valid_indicators']

    details = []
    total_score = 0.0
    total_weight = 0.0
    valid_count = 0
    total_count = len(indicator_config)
    missing_indicators = []
    indicator_scores = {}

    for cfg in indicator_config:
        name = cfg['name']
        raw_val = indicator_values.get(name, None)

        if raw_val is None or (isinstance(raw_val, float) and not np.isfinite(raw_val)):
            missing_indicators.append(name)
            indicator_scores[name] = np.nan
            details.append({
                'name': name, 'score': 0.0, 'signal': None,
                'matched': False, 'raw_value': None, 'status': 'missing',
            })
            continue

        result = score_indicator(raw_val, cfg)
        abs_weight = abs(cfg['weight'])
        total_score += result['score']
        total_weight += abs_weight
        valid_count += 1
        indicator_scores[name] = result['score']

        details.append({
            'name': name,
            'score': result['score'],
            'signal': result['signal'],
            'matched': result['matched'],
            'raw_value': raw_val,
            'status': 'ok',
        })

    # 有效指标不足 → 降低置信度
    if valid_count < min_valid:
        if valid_count == 0:
            return {
                'total_score': 0.0,
                'signal': 'hold',
                'details': details,
                'valid_count': valid_count,
                'total_count': total_count,
                'indicator_scores': indicator_scores,
                'adaptive_thresholds': thresholds,
                'missing_indicators': missing_indicators,
                'confidence': 0.0,
            }
        # 按有效权重重新归一化
        if total_weight > 0:
            total_score = total_score / total_weight * sum(abs(cfg['weight']) for cfg in indicator_config)

    # 判定信号
    if total_score >= thresholds['strong_buy']:
        signal = 'strong_buy'
    elif total_score >= thresholds['buy']:
        signal = 'buy'
    elif total_score <= thresholds['strong_sell']:
        signal = 'strong_sell'
    elif total_score <= thresholds['sell']:
        signal = 'sell'
    else:
        signal = 'hold'

    confidence = min(1.0, valid_count / total_count)

    return {
        'total_score': round(total_score, 2),
        'signal': signal,
        'details': details,
        'valid_count': valid_count,
        'total_count': total_count,
        'indicator_scores': indicator_scores,
        'adaptive_thresholds': thresholds,
        'missing_indicators': missing_indicators,
        'confidence': round(confidence, 2),
    }


# ===================== Trend Bonus 修复版 =====================
def calculate_trend_bonus(indicator_scores, trend_direction, trend_strength=1.0):
    """
    趋势加成：买卖方向分离，消除循环依赖。
    
    Args:
        indicator_scores: {指标名: 得分} 字典
        trend_direction: 趋势方向 'up'/'down'/'neutral'
        trend_strength: 趋势强度 0.0~2.0（默认1.0）
    
    Returns:
        {
            'bonus_score': 趋势加成分数,
            'direction': 'bullish'/'bearish'/'neutral',
            'signal_count': {'buy': n, 'sell': m},
        }
    
    逻辑：
    - 上涨趋势 + 买入信号 → 加分（顺势）
    - 下跌趋势 + 卖出信号 → 加分（顺势）
    - 上涨趋势 + 卖出信号 → 减分（逆势）
    - 下跌趋势 + 买入信号 → 减分（逆势）
    """
    buy_count = sum(
        1 for v in indicator_scores.values()
        if isinstance(v, (int, float)) and not np.isnan(v) and v > 0
    )
    sell_count = sum(
        1 for v in indicator_scores.values()
        if isinstance(v, (int, float)) and not np.isnan(v) and v < 0
    )

    bonus = 0.0

    if trend_direction == 'up':
        direction = 'bullish'
        confirm = buy_count
        diverge = sell_count
        bonus = trend_strength * (confirm * 0.5 - diverge * 0.3)
    elif trend_direction == 'down':
        direction = 'bearish'
        confirm = sell_count
        diverge = buy_count
        bonus = trend_strength * (confirm * 0.5 - diverge * 0.3)
    else:
        direction = 'neutral'

    return {
        'bonus_score': round(bonus, 2),
        'direction': direction,
        'signal_count': {'buy': buy_count, 'sell': sell_count},
    }
