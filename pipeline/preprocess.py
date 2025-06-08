from __future__ import annotations
import os
import sys

# ═════════════ IMPORTS & CONFIG ═════════════════════════════════════════
import logging, warnings, joblib
from pathlib import Path
from typing import Dict, List, Tuple
import yaml

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.feature_selection import VarianceThreshold, chi2, f_classif
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler


def getDataSet(inputFolder, fileName):
    """
    This should be the last dataset we got from the previous step
    """
    filePath = os.path.join(inputFolder, fileName)
    dataframe = pd.read_csv(filePath, encoding="utf-8")
    sys.stderr.write(f"The input data frame {fileName} size is {dataframe.shape}\n")

    return dataframe


def saveTransformedDataFrame(transformedDF: pd.DataFrame, outputFolder, fileName):
    outputPath = os.path.join(outputFolder, fileName)

    transformedDF.to_csv(outputPath, index=False)
    sys.stderr.write(f"Dataframe [{fileName}] saved on {outputPath}\n")


def saveOneHotEncoder(
    one_hot_encoder: OneHotEncoder, file_name: str, out_path: str
) -> None:
    """
    Save the OneHotEncoder to a file.
    """
    os.makedirs(out_path, exist_ok=True)

    file_pkl = f"{file_name}_ohe.pkl"
    outputPath = os.path.join(out_path, file_pkl)

    joblib.dump(one_hot_encoder, outputPath)
    sys.stderr.write(f"OneHotEncoder saved as {file_pkl}\n")


def saveMinMaxScaler(
    minmax_scaler: MinMaxScaler, file_name: str, out_path: str
) -> None:
    """
    Save the MinMaxScaler to a file.
    """
    os.makedirs(out_path, exist_ok=True)

    file_pkl = f"{file_name}_minmax.pkl"
    outputPath = os.path.join(out_path, file_pkl)

    joblib.dump(minmax_scaler, outputPath)
    sys.stderr.write(f"MinMaxScaler saved as {file_pkl}\n")


# ═════════════ FUNCIONES AUXILIARES ════════════════════════════════════════════════
def _chi2_anova(df, cat, num):
    y_disc = pd.qcut(df[num], 4, labels=False, duplicates="drop")
    return (
        chi2(pd.get_dummies(df[cat]), y_disc)[1].min(),
        f_classif(pd.get_dummies(df[cat]), df[num])[1].min(),
    )


def _remove_high_corr(df_num, target_col: str, high_corr: float):
    c = df_num.corr().abs()
    up = c.where(np.triu(np.ones(c.shape), 1).astype(bool))
    return [col for col in up.columns if any(up[col] > high_corr) and col != target_col]


def moving_avg(s, win=3):
    return s.rolling(win, 1).mean()


# ═════════════ 1. FEATURE ENGINEERING ═══════════════════════════════════
def feature_engineering(
    df: pd.DataFrame,
    nombre: str,
    target_col: str,
    low_var: float,
    high_corr: float,
    one_hot_encoder: OneHotEncoder = None,
    minmax_scaler: MinMaxScaler = None,
    train_columns: List[str] = None,
    ignore_lags: bool = False,
) -> Tuple[pd.DataFrame, OneHotEncoder]:
    logging.info(f"··· FE: {nombre.upper()} ···")
    df["Fecha"] = pd.to_datetime(
        df["Year"].astype(str) + "-" + df["Mes"].astype(str).str.zfill(2)
    )
    df["Mes"] = df["Fecha"].dt.month

    # lags / MA / estacionalidad
    if not ignore_lags:
        df["Lag_1"] = df[target_col].shift(1)
        df["Lag_12"] = df[target_col].shift(12)
    df["MA_4"] = moving_avg(df[target_col], 4)
    df["MA_12"] = moving_avg(df[target_col], 12)
    df["Month_sin"] = np.sin(2 * np.pi * df["Mes"] / 12)
    df["Month_cos"] = np.cos(2 * np.pi * df["Mes"] / 12)
    df["Mes"] = pd.to_datetime(df["Mes"], format="%m").dt.strftime("%b")

    # OneHotEncoder
    categorical_cols = df.select_dtypes(include=["category", "object"]).columns.tolist()
    numerical_cols = df.select_dtypes(include=['number']).columns.tolist()

    ohe: OneHotEncoder = None

    if one_hot_encoder is None:
        print("Creating new OneHotEncoder")
        ohe = OneHotEncoder(drop="first", sparse_output=False, handle_unknown="ignore")
    else:
        ohe = one_hot_encoder

    df = df.join(
        pd.DataFrame(
            ohe.fit_transform(df[categorical_cols]),
            columns=ohe.get_feature_names_out(categorical_cols),
            index=df.index,
        )
    )
    df = df.drop(columns=categorical_cols)

    if train_columns:
        # Ensure the dataframe has the same columns as the training set
        drop_known_cols = [item for item in train_columns if item in df.columns.tolist()]
        df = df[drop_known_cols].copy()
    else:
        # # filtros numéricos
        num = df.select_dtypes("number").fillna(0)
        keep = num.columns[VarianceThreshold(low_var).fit(num).get_support()]
        df = df[keep.tolist() + [c for c in df.columns if c not in num.columns]]
        high_corr_cols = _remove_high_corr(df.select_dtypes("number"), target_col, high_corr)
        df = df.drop(
            columns=high_corr_cols
        )
        df = df.dropna()

    # MinMaxScaler
    filtered_numerical = [item for item in numerical_cols if item in df.select_dtypes(include=['number']).columns.tolist()]

    if minmax_scaler is None:
        print("Creating new MinMaxScaler")
        minmax_sc = MinMaxScaler()
        minmax_sc = minmax_sc.fit(df[filtered_numerical])
    else:
        minmax_sc = minmax_scaler

    df = pd.concat([
        pd.DataFrame(minmax_sc.transform(df[filtered_numerical]), columns=filtered_numerical, index=df.index),
        df.drop(columns=filtered_numerical)
    ], axis=1)

    return df, ohe, minmax_sc

    # df.to_csv(FE_BASE_PATH/f"{nombre}_features.csv", index=False, encoding="utf-8")


# ═══════════════════════════════════════════ MAIN ════════════════════════════════════════════════
def main():
    params = yaml.safe_load(open("params.yaml"))["preprocess"]
    np.set_printoptions(suppress=True)

    if len(sys.argv) != 3:
        sys.stderr.write("Arguments error. Usage:\n")
        sys.stderr.write("\tpython featurization.py data-dir-path features-dir-path\n")
        sys.exit(1)

    in_path = sys.argv[1]  # previous step folder
    out_path = sys.argv[2]  # output folder
    target_col = params["target"]
    low_var = params["low_var"]
    high_corr = params["high_corr"]
    file_params = params["files"]

    os.makedirs(out_path, exist_ok=True)

    # ═════════════════════════════════════ Iterate through data ═════════════════════════════════
    for file in file_params:
        file_name = file["file_name"]

        # ═════════════════════════════════ Iterate through types of tequila ═════════════════════
        for teq_type in ["teq100", "teq"]:
            file_name_and_type = f"{file_name}_{teq_type}"

            teq_file_train = f"{file_name_and_type}_train.csv"
            teq_file_test = f"{file_name_and_type}_test.csv"

            sys.stderr.write(f"Processing file: {file_name_and_type}\n")

            # Get the dataset
            train_df = getDataSet(in_path, teq_file_train)
            test_df = getDataSet(in_path, teq_file_test)

            # ════════════════════════════════════════════════════════════════════════════════════

            train_df, one_hot_encoder, minmax_scaler = feature_engineering(
                train_df, file_name_and_type, target_col, low_var, high_corr
            )

            test_df, _, _ = feature_engineering(
                test_df,
                file_name_and_type,
                target_col,
                low_var,
                high_corr,
                one_hot_encoder,
                minmax_scaler,
                train_df.columns.to_list()
            )

            # ═════════════════════════════════ Save transformed dataframes ═════════════════════
            saveTransformedDataFrame(
                train_df, out_path, f"{file_name_and_type}_train_features.csv"
            )
            saveTransformedDataFrame(
                test_df, out_path, f"{file_name_and_type}_test_features.csv"
            )

            saveOneHotEncoder(one_hot_encoder, file_name_and_type, out_path)
            saveMinMaxScaler(minmax_scaler, file_name_and_type, out_path)

    sys.stderr.write("---Pipeline finished---\n")


if __name__ == "__main__":
    main()
