"""Data loader module conforming to SOP-QUANT-001 (Section 5: Historical Data Ingestion).

Loads CSV data, preserves raw inputs, performs validation, and formats into standard
OHLCV pandas structures ready for quantitative strategy backtesting.
"""

from pathlib import Path
from typing import Union, BinaryIO, Optional, Tuple
import pandas as pd

from src.data.validator import validate_market_data, DataValidationResult


def load_csv_data(
    file_path_or_buffer: Union[str, Path, BinaryIO],
    source_name: Optional[str] = None
) -> Tuple[pd.DataFrame, DataValidationResult]:
    """Loads market data from a CSV file path or file-like buffer and validates it.
    
    Parameters:
        file_path_or_buffer: Path to CSV or file buffer (e.g., Streamlit UploadedFile).
        source_name: Optional identifier for logging and metrics.
        
    Returns:
        Tuple of (raw_df, DataValidationResult).
    """
    if source_name is None:
        if isinstance(file_path_or_buffer, (str, Path)):
            source_name = str(Path(file_path_or_buffer).name)
        else:
            source_name = getattr(file_path_or_buffer, "name", "in_memory_csv")
            
    try:
        raw_df = pd.read_csv(file_path_or_buffer)
    except Exception as e:
        empty_res = DataValidationResult(
            is_valid=False,
            errors=[f"Failed to read CSV file: {e}"],
            metrics={"source": source_name}
        )
        return pd.DataFrame(), empty_res
        
    validation_res = validate_market_data(raw_df, source_name=source_name)
    return raw_df, validation_res


def load_market_data(
    file_path_or_buffer: Union[str, Path, BinaryIO],
    save_processed_to: Optional[Union[str, Path]] = None,
    source_name: Optional[str] = None
) -> pd.DataFrame:
    """Convenience wrapper that returns validated clean data or raises ValueError.
    
    Parameters:
        file_path_or_buffer: Path or buffer.
        save_processed_to: Optional path to save clean Parquet or CSV.
        source_name: Name of data source.
        
    Returns:
        Clean validated pd.DataFrame with DatetimeIndex and lowercase OHLCV columns.
        
    Raises:
        ValueError if the dataset fails validation.
    """
    _, result = load_csv_data(file_path_or_buffer, source_name=source_name)
    if not result.is_valid:
        raise ValueError(f"Market data validation failed for {result.metrics.get('source')}: {result.errors}")
        
    clean_df = result.clean_data
    if save_processed_to and clean_df is not None:
        out_path = Path(save_processed_to)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.suffix.lower() == ".parquet":
            clean_df.to_parquet(out_path)
        else:
            clean_df.to_csv(out_path)
            
    return clean_df
