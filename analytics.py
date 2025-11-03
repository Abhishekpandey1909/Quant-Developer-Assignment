"""
Analytics module for computing quantitative metrics and statistical analysis.
Includes price stats, OLS regression, hedge ratios, spread, z-score, ADF test, and correlation.
"""

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import adfuller
from statsmodels.regression.linear_model import OLS
from typing import Tuple, Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

# Optional import for robust regression
try:
    from sklearn.linear_model import HuberRegressor
    HUBER_AVAILABLE = True
except ImportError:
    HUBER_AVAILABLE = False
    logger.warning("sklearn not available, robust regression disabled")


class AnalyticsEngine:
    """Engine for computing various quantitative analytics."""
    
    @staticmethod
    def compute_price_stats(df: pd.DataFrame, price_col: str = 'price') -> Dict:
        """
        Compute basic price statistics.
        
        Args:
            df: DataFrame with price data
            price_col: Column name containing prices
            
        Returns:
            Dictionary of statistics
        """
        if df.empty or price_col not in df.columns:
            return {}
        
        prices = df[price_col]
        
        return {
            'mean': float(prices.mean()),
            'std': float(prices.std()),
            'min': float(prices.min()),
            'max': float(prices.max()),
            'median': float(prices.median()),
            'skew': float(prices.skew()),
            'kurtosis': float(prices.kurtosis()),
            'count': int(len(prices))
        }
    
    @staticmethod
    def compute_ols_regression(x: pd.Series, y: pd.Series,
                               robust: bool = False) -> Dict:
        """
        Compute OLS regression for hedge ratio estimation.
        
        Args:
            x: Independent variable (e.g., price of asset 1)
            y: Dependent variable (e.g., price of asset 2)
            robust: Use robust regression (Huber)
            
        Returns:
            Dictionary with regression results including hedge ratio
        """
        if len(x) < 2 or len(y) < 2 or len(x) != len(y):
            return {'error': 'Insufficient data for regression'}
        
        # Remove NaN values
        mask = ~(x.isna() | y.isna())
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 2:
            return {'error': 'Insufficient valid data'}
        
        try:
            if robust:
                # Robust regression using Huber (from sklearn)
                if not HUBER_AVAILABLE:
                    logger.warning("Robust regression requested but sklearn not available, using OLS instead")
                    robust = False
                else:
                    reg = HuberRegressor()
                    reg.fit(x_clean.values.reshape(-1, 1), y_clean.values)
                    hedge_ratio = float(reg.coef_[0])
                    intercept = float(reg.intercept_)
                    r_squared = None  # Huber doesn't provide R-squared easily
            
            if not robust:
                # Standard OLS
                x_with_const = pd.DataFrame({'x': x_clean, 'const': 1})
                model = OLS(y_clean, x_with_const).fit()
                hedge_ratio = float(model.params['x'])
                intercept = float(model.params['const'])
                r_squared = float(model.rsquared)
                pvalue = float(model.pvalues['x']) if 'x' in model.pvalues else None
                std_err = float(model.bse['x']) if 'x' in model.bse else None
            
            # Calculate spread (residuals)
            predicted = hedge_ratio * x_clean + intercept
            residuals = y_clean - predicted
            spread_mean = float(residuals.mean())
            spread_std = float(residuals.std())
            
            result = {
                'hedge_ratio': hedge_ratio,
                'intercept': intercept,
                'spread_mean': spread_mean,
                'spread_std': spread_std,
                'n_observations': int(len(x_clean))
            }
            
            if r_squared is not None:
                result['r_squared'] = r_squared
            if 'pvalue' in locals():
                result['pvalue'] = pvalue
            if 'std_err' in locals():
                result['std_err'] = std_err
                
            return result
            
        except Exception as e:
            logger.error(f"Error in OLS regression: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def compute_spread(df1: pd.DataFrame, df2: pd.DataFrame,
                      price_col: str = 'close',
                      hedge_ratio: Optional[float] = None) -> pd.Series:
        """
        Compute spread between two price series.
        
        Args:
            df1: First price DataFrame
            df2: Second price DataFrame
            price_col: Column name for prices
            hedge_ratio: Optional hedge ratio for spread calculation
            
        Returns:
            Series of spread values
        """
        if df1.empty or df2.empty:
            return pd.Series()
        
        # Merge on timestamp
        merged = pd.merge_asof(
            df1[['timestamp', price_col]].sort_values('timestamp'),
            df2[['timestamp', price_col]].sort_values('timestamp'),
            on='timestamp',
            suffixes=('_1', '_2')
        )
        
        if hedge_ratio:
            spread = merged[f'{price_col}_2'] - hedge_ratio * merged[f'{price_col}_1']
        else:
            spread = merged[f'{price_col}_2'] - merged[f'{price_col}_1']
        
        return spread
    
    @staticmethod
    def compute_zscore(series: pd.Series, window: int = 20) -> pd.Series:
        """
        Compute rolling z-score.
        
        Args:
            series: Time series data
            window: Rolling window size
            
        Returns:
            Series of z-scores
        """
        if series.empty:
            return pd.Series()
        
        rolling_mean = series.rolling(window=window).mean()
        rolling_std = series.rolling(window=window).std()
        
        # Avoid division by zero
        zscore = (series - rolling_mean) / rolling_std.replace(0, np.nan)
        
        return zscore
    
    @staticmethod
    def compute_adf_test(series: pd.Series, maxlag: Optional[int] = None) -> Dict:
        """
        Perform Augmented Dickey-Fuller test for stationarity.
        
        Args:
            series: Time series data
            maxlag: Maximum lag order
            
        Returns:
            Dictionary with test results
        """
        if series.empty or len(series) < 10:
            return {'error': 'Insufficient data for ADF test'}
        
        try:
            # Remove NaN values
            series_clean = series.dropna()
            if len(series_clean) < 10:
                return {'error': 'Insufficient valid data'}
            
            result = adfuller(series_clean, maxlag=maxlag)
            
            return {
                'adf_statistic': float(result[0]),
                'pvalue': float(result[1]),
                'critical_values': {k: float(v) for k, v in result[4].items()},
                'n_lags': int(result[2]),
                'n_observations': int(result[3]),
                'is_stationary': result[1] < 0.05  # p-value < 0.05
            }
        except Exception as e:
            logger.error(f"Error in ADF test: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def compute_rolling_correlation(x: pd.Series, y: pd.Series,
                                     window: int = 20) -> pd.Series:
        """
        Compute rolling correlation between two series.
        
        Args:
            x: First time series
            y: Second time series
            window: Rolling window size
            
        Returns:
            Series of correlation coefficients
        """
        if x.empty or y.empty or len(x) != len(y):
            return pd.Series()
        
        # Merge on index
        merged = pd.DataFrame({'x': x, 'y': y})
        
        rolling_corr = merged['x'].rolling(window=window).corr(merged['y'])
        
        return rolling_corr
    
    @staticmethod
    def resample_data(df: pd.DataFrame, timeframe: str,
                      price_col: str = 'price',
                      volume_col: str = 'size') -> pd.DataFrame:
        """
        Resample tick data to OHLC format.
        
        Args:
            df: DataFrame with tick data
            timeframe: Resampling period ('1s', '1m', '5m')
            price_col: Column name for price
            volume_col: Column name for volume
            
        Returns:
            DataFrame with OHLC data
        """
        if df.empty or 'timestamp' not in df.columns:
            return pd.DataFrame()
        
        df = df.set_index('timestamp')
        
        # Map timeframe to pandas frequency
        freq_map = {
            '1s': '1S',
            '1m': '1T',
            '5m': '5T'
        }
        
        freq = freq_map.get(timeframe, '1T')
        
        # Resample to OHLC
        ohlc = df[price_col].resample(freq).ohlc()
        volume = df[volume_col].resample(freq).sum()
        
        result = ohlc.copy()
        result['volume'] = volume
        result = result.dropna()
        result = result.reset_index()
        
        return result
    
    @staticmethod
    def compute_liquidity_metrics(df: pd.DataFrame) -> Dict:
        """
        Compute liquidity metrics.
        
        Args:
            df: DataFrame with trade data
            
        Returns:
            Dictionary of liquidity metrics
        """
        if df.empty:
            return {}
        
        total_volume = float(df['size'].sum()) if 'size' in df.columns else 0
        trade_count = len(df)
        avg_trade_size = float(df['size'].mean()) if 'size' in df.columns else 0
        
        return {
            'total_volume': total_volume,
            'trade_count': trade_count,
            'avg_trade_size': avg_trade_size
        }
