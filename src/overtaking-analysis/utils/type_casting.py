"""Cast data types of DataFrame columns to specified types."""
from typing import cast

import numpy as np
import numpy.typing as npt
import pandas as pd


def to_np_float(values: pd.DataFrame | None) -> npt.NDArray[np.float64]:
    """Cast a list of values to a numpy array of float64."""
    if values is None:
        raise ValueError("Values must be provided for type casting.")
    return cast(npt.NDArray[np.float64], values.to_numpy())

