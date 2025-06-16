import os
from pathlib import Path
import random
import sys
from typing import List

import pandas as pd
import yaml
from pandas import DataFrame

def disproportionateSampling(dataframe: DataFrame, target: str = ""):
    dataframe.groupby("Grade", group_keys=False).apply(lambda x: x.sample(2))

def remove_totals(df: DataFrame, column: str):
    """
    Remove totals from the dataframe as they are redundant data we can't use.
    """
    return df[df[column] != "Total"]

def separate_subcategories(df: DataFrame, column: str = "", subcategoria: List[str] = ["Tequila 100%", "Tequila"]):
    """
    Returns two dataframes: one for Tequila 100% and another for Tequila.

    subcategoria is a list of two values, the first is for Tequila 100% and the second is for Tequila.
    """
    teq_100_df = remove_columns(df[df[column] == subcategoria[0]].copy(), column)
    teq_df = remove_columns(df[df[column] == subcategoria[1]].copy(), column)
    return teq_100_df, teq_df

def isolate_country_data(dafa_df: DataFrame, country: str = ""):
    """
    Isolate data for a specific country.
    """
    isolated_df = dafa_df[dafa_df["NombrePais"] == country].copy()
    return isolated_df

def remove_columns(df: DataFrame, columns: list):
    """
    Remove specified columns from the dataframe.
    """
    return df.drop(columns=columns, errors='ignore')

def split_test_train(df: DataFrame, trainSplit=0.8):
    CUT = int(len(df) * trainSplit)
    train_df, test_df = df.iloc[:CUT], df.iloc[CUT:]

    return train_df, test_df

def format_df_to_specific_order(data_df: pd.DataFrame):
    new_order = ['Valor','Year','Mes']
    data_df = data_df[new_order]
    return data_df


def main():
    params = yaml.safe_load(open("params.yaml"))["prepare"]
    file_params = params["files"]

    if len(sys.argv) != 1:
        sys.stderr.write("Arguments error. Usage:\n")
        sys.stderr.write("\tpython prepare.py data-file\n")
        sys.exit(1)

    # Create output directory if it doesn't exist
    os.makedirs(os.path.join("data", "pipeline", "prepared"), exist_ok=True)
    input = Path("data/")

    for file in file_params:
        is_pais_dataset = True if "exportaciones_pais" in file["path"] else False
        category_column = file["subcategoria_col"]

        print(f"Processing file: {file['path']} (Is Pais Dataset: {is_pais_dataset} || Category Column: {category_column})")
        # ========================= Read CSV =========================================
        dataframe = pd.read_csv(input / file["path"], encoding="utf-8")
        file_name = f"{file["path"].replace("consolidado_", "").replace(".csv", "")}"

        # ======================== Remove unncesary data from dataset ========================
        if not is_pais_dataset:
            dataframe = remove_totals(dataframe, category_column)
            dataframe = remove_columns(dataframe, ["AñoArchivo"])
        else:
            # ====================== Aislar datos de un país específico ======================
            dataframe = isolate_country_data(dataframe, "ESTADOS UNIDOS DE AMERICA")
            dataframe = dataframe[dataframe["Clase"] == "BLANCO"].copy()
            dataframe = remove_columns(dataframe, ["Total_Pais_Mes", "Clase", "Litros 40 % Alc. Vol", "NombrePais"])
            dataframe = dataframe.rename(columns={'Total_Categoria_Mes': 'Valor', 'AñoArchivo': 'Year'})

        # ======================== Separar en dos categorias ========================
        if not is_pais_dataset:
            teq_100_df, teq_df = separate_subcategories(dataframe, "SubCategoria", ["Tequila 100%", "Tequila"])
            teq_100_df = format_df_to_specific_order(teq_100_df)
            teq_df = format_df_to_specific_order(teq_df)

            teq_100_train_df, teq_100_test_df = split_test_train(teq_100_df, 0.8)

            output_train_path = os.path.join(
                "data",
                "pipeline",
                "prepared"
            )

            # Save the train and test dataframes for Tequila 100%
            teq_100_train_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq100_train.csv"
                ), index=False)
            teq_100_test_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq100_test.csv"
                ), index=False)
            
            # Save the train and test dataframes for Tequila
            teq_train_df, teq_test_df = split_test_train(teq_df, 0.8)

            teq_train_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq_train.csv"
                ), index=False)
            teq_test_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq_test.csv"
                ), index=False)
            
            # Save complete dataset with no division
            teq_100_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq100_full.csv"
                ), index=False)
            teq_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq_full.csv"
                ), index=False)
        else:
            teq_100_df, teq_df = separate_subcategories(dataframe, category_column, ["TEQUILA 100% DE AGAVE", "TEQUILA"])
            teq_100_df = format_df_to_specific_order(teq_100_df)
            teq_df = format_df_to_specific_order(teq_df)

            teq_100_train_df, teq_100_test_df = split_test_train(teq_100_df, 0.8)

            output_train_path = os.path.join(
                "data",
                "pipeline",
                "prepared"
            )


            # Save the train and test dataframes for Tequila 100%
            teq_100_train_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq100_train.csv"
                ), index=False)
            teq_100_test_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq100_test.csv"
                ), index=False)
            
            # Save the train and test dataframes for Tequila
            teq_train_df, teq_test_df = split_test_train(teq_df, 0.8)

            teq_train_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq_train.csv"
                ), index=False)
            teq_test_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq_test.csv"
                ), index=False)
            
            # Save complete dataset with no division
            teq_100_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq100_full.csv"
                ), index=False)
            teq_df.to_csv(
                os.path.join(
                    output_train_path,
                    f"{file_name}_teq_full.csv"
                ), index=False)


if __name__ == "__main__":
    main()
