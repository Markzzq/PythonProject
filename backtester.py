# -*- coding: utf-8 -*-
"""
回测框架
========
- 逐日推进，避免未来信息泄露（look-ahead bias）
- 记录信号 + 未来N日收益率
- 按信号类型和市场状态分层统计
- 生成回测报告
"""

import numpy as np
import pandas as pd
from market_regime import detect_market_regime


class ETFBacktester:
    """
    ETF评分系统回测器。
    
    使用方式：
        bt = ETFBacktester(price_df, indicator_calculator)
        bt.run()
        report = bt.report()
        bt.report_by_regime()
    """
    
    def __init__(self, price_df, indicator_calculator, lookback_days=120):
        """
        Args:
            price_df: DataFrame, 必须包含 Close, High, Low, Volume 列
            indicator_calculator: 接收当日及之前数据，返回指标值字典的函数
            lookback_days: 回看天数（计算指标所需的最小数据量）
        """
        self.df = price_df.copy()
        self.calculator = indicator_calculator
        self.lookback_days = lookback_days
        
        # 未来N日收益率
        self.forward_days = [1, 3, 5, 10, 20]
        
        # 结果存储
        self.results = []           # 每条记录
        self.daily_signals = {}    # {date: signal_info}
    
    def run(self):
        """执行回测"""
        n = len(self.df)
        if n <= self.lookback_days:
            print(f"[WARN] 数据量不足: {n} <= {self.lookback_days}")
            return
        
        for i in range(self.lookback_days, n):
            # 当前日期及之前的所有数据
            window_df = self.df.iloc[:i + 1]
            current_date = self.df.index[i] if isinstance(self.df.index, pd.DatetimeIndex) else i
            
            # 计算指标
            try:
                indicator_values = self.calculator(window_df)
                regime = detect_market_regime(window_df)
            except Exception as e:
                indicator_values = {}
                regime = {'regime': 'range'}
            
            # 未来N日收益率（避免 look-ahead bias）
            forward_returns = {}
            for fd in self.forward_days:
                future_idx = i + fd
                if future_idx < n:
                    current_close = window_df['Close'].iloc[-1]
                    future_close = self.df['Close'].iloc[future_idx]
                    forward_returns[f'return_{fd}d'] = round(
                        (future_close - current_close) / current_close * 100, 2
                    )
                else:
                    forward_returns[f'return_{fd}d'] = None
            
            record = {
                'date': current_date,
                'close': window_df['Close'].iloc[-1],
                'indicators': indicator_values,
                'regime': regime.get('regime', 'range'),
                'trend_direction': regime.get('trend_direction', 'neutral'),
                'trend_strength': regime.get('trend_strength', 0),
                **forward_returns,
            }
            
            self.results.append(record)
    
    def report(self):
        """
        生成回测报告。
        
        Returns:
            dict，包含各信号类型的收益率统计
        """
        if not self.results:
            return {'summary': '无回测数据', 'by_signal': {}, 'by_regime': {}}
        
        df = pd.DataFrame(self.results)
        
        # 统计各信号类型的未来收益
        report = {
            'total_days': len(self.results),
            'regime_distribution': {},
            'signal_performance': {},
        }
        
        # 市值分布
        if 'regime' in df.columns:
            report['regime_distribution'] = df['regime'].value_counts().to_dict()
        
        # 计算信号性能
        # 需要结合 scoring_engine 的 calculate_total_score 来生成信号
        # 这里预留接口，由外部调用者自行扩展
        
        return report
    
    def report_by_signal(self, signal_results):
        """
        按信号类型统计收益表现。
        
        Args:
            signal_results: 列表，每个元素包含 {date, signal, score, ...}
        
        Returns:
            DataFrame: 按信号分组的统计表
        """
        if not signal_results:
            return pd.DataFrame()
        
        df = pd.DataFrame(signal_results)
        
        # 筛选有信号的行
        signal_df = df[df['signal'] != 'hold'].copy()
        
        if len(signal_df) == 0:
            return pd.DataFrame({'message': ['无有效信号']})
        
        stats = []
        for signal_type in ['strong_buy', 'buy', 'sell', 'strong_sell']:
            subset = signal_df[signal_df['signal'] == signal_type]
            if len(subset) == 0:
                continue
            
            stat = {'signal': signal_type, 'count': len(subset)}
            for fd in self.forward_days:
                col = f'return_{fd}d'
                if col in subset.columns:
                    returns = subset[col].dropna()
                    if len(returns) > 0:
                        stat[f'{fd}d_win_rate'] = round(
                            (returns > 0).sum() / len(returns) * 100, 1
                        )
                        stat[f'{fd}d_avg_return'] = round(returns.mean(), 2)
                        stat[f'{fd}d_max_return'] = round(returns.max(), 2)
                        stat[f'{fd}d_min_return'] = round(returns.min(), 2)
            
            stats.append(stat)
        
        return pd.DataFrame(stats)
    
    def report_by_regime(self, signal_results):
        """
        分层统计：按市场状态 × 信号类型。
        
        Args:
            signal_results: 同 report_by_signal
        
        Returns:
            DataFrame: 分层统计表
        """
        if not signal_results:
            return pd.DataFrame()
        
        df = pd.DataFrame(signal_results)
        signal_df = df[df['signal'] != 'hold'].copy()
        
        if len(signal_df) == 0:
            return pd.DataFrame({'message': ['无有效信号']})
        
        stats = []
        for regime in ['strong_bull', 'bull', 'range', 'bear', 'strong_bear']:
            regime_sub = signal_df[signal_df.get('regime') == regime]
            if len(regime_sub) == 0:
                continue
            
            for signal_type in ['strong_buy', 'buy', 'sell', 'strong_sell']:
                subset = regime_sub[regime_sub['signal'] == signal_type]
                if len(subset) < 2:
                    continue
                
                stat = {'regime': regime, 'signal': signal_type, 'count': len(subset)}
                for fd in self.forward_days:
                    col = f'return_{fd}d'
                    if col in subset.columns:
                        returns = subset[col].dropna()
                        if len(returns) > 0:
                            stat[f'{fd}d_avg'] = round(returns.mean(), 2)
                            stat[f'{fd}d_win%'] = round(
                                (returns > 0).sum() / len(returns) * 100, 1
                            )
                stats.append(stat)
        
        return pd.DataFrame(stats)
    
    def summary_table(self, signal_results):
        """生成汇总表格"""
        signal_report = self.report_by_signal(signal_results)
        regime_report = self.report_by_regime(signal_results)
        
        print("=" * 60)
        print("ETF 评分系统回测报告")
        print("=" * 60)
        print(f"\n回测天数: {len(self.results)}")
        
        if not signal_report.empty and 'message' not in signal_report.columns:
            print("\n--- 信号表现 ---")
            print(signal_report.to_string(index=False))
        
        if not regime_report.empty and 'message' not in regime_report.columns:
            print("\n--- 市场状态分层 ---")
            print(regime_report.to_string(index=False))
        
        print("=" * 60)
        
        return {
            'signal': signal_report,
            'regime': regime_report,
        }
