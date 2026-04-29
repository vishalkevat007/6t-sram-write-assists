from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


def format_labels(values: List[float], decimals: Optional[int] = None) -> str:
    """
    Format numeric values for LaTeX ticklabels without losing distinct values.
    """
    formatted = []
    for v in values:
        v = float(v)

        if decimals is None:
            s = f"{v}"
        else:
            s = f"{v:.{decimals}f}"

        # remove trailing zeros cleanly
        if "." in s:
            s = s.rstrip("0").rstrip(".")

        formatted.append(s)

    return ",".join(formatted)


def infer_axis_label(
    param_name: str,
    label_map: Optional[Dict[str, str]] = None,
) -> str:
    """
    Return axis label from a user-provided map if available,
    otherwise return the parameter name itself.
    """
    if label_map and param_name in label_map:
        return label_map[param_name]
    return param_name


def parse_cadence_csv_general(
    csv_path: str | Path,
    x_param: str,
    y_param: str,
    pass_param: str = "Pass",
    output_csv: str | Path = "shmoo_matrix.csv",
    flip_pass_fail: bool = False,
    scale_factors: Optional[Dict[str, float]] = None,
    label_map: Optional[Dict[str, str]] = None,
    x_decimals: Optional[int] = None,
    y_decimals: Optional[int] = None,
    title: str = "SRAM Write Shmoo Plot",
    caption: str = "Write shmoo plot.",
) -> pd.DataFrame:
    """
    Generalized parser for Cadence sweep CSV.

    Parameters
    ----------
    csv_path : input Cadence CSV
    x_param : parameter name for x-axis, e.g. "PW"
    y_param : parameter name for y-axis, e.g. "Vdd"
    pass_param : pass/fail result field, default "Pass"
    output_csv : cleaned matrix CSV for LaTeX
    flip_pass_fail : invert pass/fail if needed
    scale_factors : optional numeric scaling, e.g. {"PW": 1e12}
    label_map : optional axis-label text map,
                e.g. {"PW": "WL Pulse Width (ps)", "Vdd": "VDD (V)"}
    x_decimals : optional decimal formatting for x tick labels
    y_decimals : optional decimal formatting for y tick labels
    title : LaTeX plot title
    caption : LaTeX figure caption
    """

    csv_path = Path(csv_path)
    output_csv = Path(output_csv)

    rows: List[Dict[str, object]] = []
    point_data: Dict[str, Dict[str, object]] = {}

    x_param_l = x_param.lower()
    y_param_l = y_param.lower()
    pass_param_l = pass_param.lower()

    with csv_path.open("r", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header

        for raw in reader:
            if not raw:
                continue

            raw = raw + [""] * (4 - len(raw))
            point, output, nominal, pass_fail = [x.strip() for x in raw[:4]]

            # Ignore descriptive line
            if point.startswith("Parameters:") or point.startswith('"Parameters:'):
                continue

            if not point or not output:
                continue

            try:
                point_int = int(point)
            except ValueError:
                continue

            if point not in point_data:
                point_data[point] = {"Point": point_int}

            output_l = output.lower()

            try:
                if output_l == x_param_l:
                    point_data[point][x_param] = float(nominal)

                elif output_l == y_param_l:
                    point_data[point][y_param] = float(nominal)

                elif output_l == pass_param_l:
                    value_str = nominal if nominal else pass_fail
                    point_data[point][pass_param] = int(float(value_str))

            except ValueError:
                continue

    for _, data in point_data.items():
        if {"Point", x_param, y_param, pass_param} <= data.keys():
            rows.append(data)

    if not rows:
        raise ValueError(
            f"No valid sweep points found for x='{x_param}', y='{y_param}', pass='{pass_param}'."
        )

    df = pd.DataFrame(rows)

    if flip_pass_fail:
        df[pass_param] = 1 - df[pass_param]

    # Optional scaling
    scale_factors = scale_factors or {}
    if x_param in scale_factors:
        df[x_param] = df[x_param] * scale_factors[x_param]
    if y_param in scale_factors:
        df[y_param] = df[y_param] * scale_factors[y_param]

    # Sort by y then x for matrix layout
    df = df.sort_values([y_param, x_param]).reset_index(drop=True)

    x_unique = sorted(df[x_param].unique())
    y_unique = sorted(df[y_param].unique())

    x_map = {x: i + 1 for i, x in enumerate(x_unique)}
    y_map = {y: i + 1 for i, y in enumerate(y_unique)}

    df["Xidx"] = df[x_param].map(x_map)
    df["Yidx"] = df[y_param].map(y_map)

    out = df[["Xidx", "Yidx", x_param, y_param, pass_param]].sort_values(["Yidx", "Xidx"])
    out.to_csv(output_csv, index=False)

    # Labels for LaTeX
    x_tick_labels = format_labels(x_unique, decimals=x_decimals)
    y_tick_labels = format_labels(y_unique, decimals=y_decimals)
    x_axis_label = infer_axis_label(x_param, label_map=label_map)
    y_axis_label = infer_axis_label(y_param, label_map=label_map)

    latex_call = (
        f"\\ShmooPlot{{{output_csv.as_posix()}}}"
        f"{{{len(x_unique)}}}"
        f"{{{len(y_unique)}}}"
        f"{{{x_tick_labels}}}"
        f"{{{y_tick_labels}}}"
        f"{{{x_axis_label}}}"
        f"{{{y_axis_label}}}"
        f"{{{title}}}"
        f"{{{caption}}}"
    )

    print(f"Wrote {output_csv}")
    print()
    print("Detected settings")
    print("-----------------")
    print(f"x-axis parameter : {x_param}")
    print(f"y-axis parameter : {y_param}")
    print(f"pass parameter   : {pass_param}")
    print()
    print("Detected values")
    print("---------------")
    print(f"x unique values  : {x_unique}")
    print(f"y unique values  : {y_unique}")
    print()
    print("Recommended LaTeX values")
    print("------------------------")
    print(f"num_x_points     : {len(x_unique)}")
    print(f"num_y_points     : {len(y_unique)}")
    print(f"x_tick_labels    : {x_tick_labels}")
    print(f"y_tick_labels    : {y_tick_labels}")
    print(f"x_label          : {x_axis_label}")
    print(f"y_label          : {y_axis_label}")
    print()
    print("Final LaTeX command")
    print("-------------------")
    print(latex_call)

    return out


def main() -> None:
    # ===============================
    # USER SETTINGS
    # ===============================
    input_csv = "vddcol_BLBvdd_8ps.csv"

    input_path = Path(input_csv)
    output_csv = f"shmoo_matrix_{input_path.stem}.csv"

    params = {
        "PW": {
            "scale": 1e12,
            "label": "WL Pulse Width (ps)",
            "decimals": None,
        },
        "Vdd": {
            "scale": 1.0,
            "label": "Circuit Voltage - Vdd (V)",
            "decimals": None,
        },
        "Vdd_col": {
            "scale": 1.0,
            # "label": "Circuit Voltage - Vdd (V)",
            "label": "Column Voltage - Vdd_col (V)",
            "decimals": None,
        },
        "BLB_Vdd": {
            "scale": 1.0,
            "label": "Bitline Voltage (V)",
            "decimals": None,
        },
        "Pass": {
            "label": "Pass/Fail",
        },
    }

    x_param = "Vdd_col"
    y_param = "BLB_Vdd"
    pass_param = "Pass"

    # Figure text
    flip_pass_fail = False
    title = ""
    caption = "Shmoo Plot for various operating voltage Vdd of the circuit"

    scale_factors = {
        x_param: params[x_param]["scale"],
        y_param: params[y_param]["scale"],
    }

    label_map = {
        x_param: params[x_param]["label"],
        y_param: params[y_param]["label"],
        pass_param: params[pass_param]["label"],
    }

    # Optional tick formatting
    x_decimals = params[x_param].get("decimals")
    y_decimals = params[y_param].get("decimals")


    parse_cadence_csv_general(
        csv_path=input_csv,
        x_param=x_param,
        y_param=y_param,
        pass_param=pass_param,
        output_csv=output_csv,
        flip_pass_fail=flip_pass_fail,
        scale_factors=scale_factors,
        label_map=label_map,
        x_decimals=x_decimals,
        y_decimals=y_decimals,
        title=title,
        caption=caption,
    )


if __name__ == "__main__":
    main()