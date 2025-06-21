from pathlib import Path
from typing import List
import logging, warnings, joblib
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import random
import sys
import yaml
import json


import tensorflow as tf
from tensorflow import keras
from keras.layers import LSTM
from preprocess import feature_engineering
from sklearn.metrics            import mean_absolute_error, mean_squared_error, r2_score
from statsmodels.tsa.seasonal import seasonal_decompose


warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
tf.config.run_functions_eagerly(False)
tf.keras.utils.set_random_seed(42)

# ════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
## Auxiliares LSTM
def sliding_window_lstm(Xdata_df: pd.DataFrame, ydata_df: pd.Series, window_size: int, optional_cols: List[str] = None):
    X, y = [], []
    dict_col_array = {}

    #Create a sliding window
    for i in range(window_size, len(ydata_df)):
        X.append(ydata_df.iloc[i-window_size:i].values) # Agregamos ydata para entrenar y predecir un paso en el futuro
        y.append(ydata_df.iloc[i])

    if optional_cols is not None and len(optional_cols) > 0:
        for col in optional_cols:
            aux_arr = []
            for i in range(window_size, len(Xdata_df)):
                aux_arr.append(Xdata_df.iloc[i-window_size:i][col].values)
                
            aux_arr = np.array(aux_arr)
            dict_col_array[col] = aux_arr
            

    X, y = np.array(X), np.array(y)

    if optional_cols is not None and len(optional_cols) > 0:
        X = X.reshape(X.shape[0], X.shape[1], 1)

        for _, val in dict_col_array.items():
            X = np.insert(X, -1, val, axis=2)
    else:
        X = np.reshape(X, (X.shape[0], X.shape[1], 1 ))

    return X, y

def get_seasonal_decompose_data(data_df: pd.DataFrame, target_col: str = "Valor"):
    res_decompose = seasonal_decompose(data_df[target_col], model='additive', extrapolate_trend='freq')

    data_df["seasonal"] = res_decompose.seasonal
    data_df["trend"] = res_decompose.trend
    data_df["resid"] = res_decompose.resid

    return data_df

def plot_decompose_data(data_decomposed_df: pd.DataFrame, observed_col: str = "Valor", v_line: float = 0):
    # res_decompose = seasonal_decompose(full_sc["Valor"], model='additive', extrapolate_trend='freq')

    fig, axs = plt.subplots(nrows=4, ncols=1, figsize=(18, 12), sharex=True)
    data_decomposed_df[observed_col].plot(ax=axs[0])
    axs[0].set_title('Serie original', fontsize=12)
    axs[0].grid()

    data_decomposed_df["trend"].plot(ax=axs[1])
    axs[1].set_title('Tendencia', fontsize=12)
    axs[1].grid()

    data_decomposed_df["seasonal"].plot(ax=axs[2])
    axs[2].set_title('Estacionalidad', fontsize=12)
    axs[2].grid()

    data_decomposed_df["resid"].plot(ax=axs[3])
    axs[3].set_title('Residuos', fontsize=12)
    axs[3].grid()

    if v_line > 0:
        for i in range(len(axs)):
            xmin, xmax = axs[i].get_xlim()
            x_position = xmin + (xmax - xmin) * 0.8
            axs[i].axvline(x=x_position, color='r', linestyle='--')


    fig.suptitle('Descomposición de la serie original vs serie diferenciada', fontsize=14)
    fig.tight_layout()

def lstm_model(input_shape):
    # Build the Model
    model = keras.models.Sequential()

    model.add(keras.layers.LSTM(64, return_sequences=True, input_shape=input_shape))
    model.add(keras.layers.LSTM(64, return_sequences=False))
    model.add(keras.layers.Dense(128, activation="relu"))
    model.add(keras.layers.Dense(1))

    # model.summary()
    model.compile(optimizer="adam",
                loss="mae",
                metrics=[keras.metrics.RootMeanSquaredError()])
    
    return model

def Xy_split(train_df: pd.DataFrame, target_col: str = "Valor"):
    X_train = train_df.drop(columns=[target_col])
    y_train = train_df[target_col]

    return X_train, y_train

def get_df(file_name: str, in_path: str, teq_type: str = "teq") -> pd.DataFrame:
    """
    Carga los DataFrames de entrenamiento y prueba desde las rutas especificadas.
    """
    input = Path(in_path)
    dataframe = pd.read_csv(input / f"{file_name}_{teq_type}_full.csv", encoding="utf-8")
    
    return dataframe

def increment_months(data_df: pd.DataFrame, prediction_horizon: int, target_col: str = "Valor"):

    # Add a new row to the DataFrame with the datetime incremented by one month
    data_df["Fecha"] = pd.to_datetime(
        data_df["Year"].astype(str) + "-" + data_df["Mes"].astype(str).str.zfill(2)
    )
    data_df["Mes"] = data_df["Fecha"].dt.month

    last_date = data_df['Fecha'].tail(1).iloc[0]

    new_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=prediction_horizon, freq='MS')
    data_df.drop('Fecha', axis=1, inplace=True)
    
    # Create a dataframe for future dates
    future_df = pd.DataFrame({
        'Year': new_dates.year,
        'Mes': new_dates.month,
        'Valor': np.zeros(prediction_horizon)
    })

    # Combine with the original dataframe
    df_extended = pd.concat([data_df, future_df], ignore_index=True)

    print(df_extended)
    return df_extended

def process_data(data_df: pd.DataFrame, indx: int, target_col: str, training_window: int, test_window: int, low_var: float = 0.01, high_corr: float = 0.9):
    # Split into train-test sets
    train_data = data_df[indx : indx + training_window]
    test_data = data_df[indx + training_window : indx + training_window + test_window]

    train_data, ohe, minmax_sc = feature_engineering(train_data, "", target_col, low_var, high_corr, ignore_lags=True)
    test_data, _, _ = feature_engineering(test_data, "", target_col, low_var, high_corr, ohe, minmax_sc, train_data.columns.to_list(), ignore_lags=True)

    train_data = train_data.set_index('Fecha')
    test_data = test_data.set_index('Fecha')

    # Decompose
    train_dec_df = get_seasonal_decompose_data(train_data, target_col)
    
    # ════════════════════════════════════════════════════ Prediccion con Trend y Seasonal ═══════════════════════════════════════
    # Divide into X and y
    X_train, y_train,  = Xy_split(train_dec_df, target_col)
    X_test, y_test = Xy_split(test_data, target_col)

    return X_train, y_train, X_test, y_test

def walk_forward_validation(data_df: pd.DataFrame, target_col: str = "Valor", training_window: int = 36, test_window: int = 1, low_var: float = 0.01, high_corr: float = 0.9):
    """
    Walk-forward validation for time series forecasting.
    """
    actuals = []
    predictions = []
    prediction_seas_trends = []
    prediction_resids = []
    metrics_trend_season = []
    sliding_window_size = 24

    optional_seatrend = ["seasonal", "trend"]
    optional_resid = ['Mes_Aug', 'Mes_Dec', 'Mes_Feb', 'Mes_Jan', 'Mes_Jul', 'Mes_Jun', 'Mes_Mar', 'Mes_May', 'Mes_Nov', 'Mes_Oct', 'Mes_Sep', "seasonal", "trend"]

    model = lstm_model((sliding_window_size, len(optional_seatrend) + 1))
    model_resid = lstm_model((sliding_window_size, len(optional_resid) + 1))

    for i in range(0,
                   len(data_df) - training_window - test_window,
                    test_window):
        
        # Split into train-test sets
        train_data = data_df[i:i + training_window]
        test_data = data_df[i + training_window : i + training_window + test_window]

        train_data, ohe, minmax_sc = feature_engineering(train_data, "", target_col, low_var, high_corr, ignore_lags=True)
        test_data, _, _ = feature_engineering(test_data, "", target_col, low_var, high_corr, ohe, minmax_sc, train_data.columns.to_list(), ignore_lags=True)

        train_data = train_data.set_index('Fecha')
        test_data = test_data.set_index('Fecha')

        # Decompose
        train_dec_df = get_seasonal_decompose_data(train_data, target_col)
        train_dec_df["sea_trend"] = train_dec_df["seasonal"] + train_dec_df["trend"]
        
        # ════════════════════════════════════════════════════ Prediccion con Trend y Seasonal ═══════════════════════════════════════
        # Divide into X and y
        X_train, y_train,  = Xy_split(train_dec_df, "sea_trend")
        _, y_test = Xy_split(test_data, target_col)    

        # Create sliding window
        X_train_sw, y_train_sw = sliding_window_lstm(X_train, y_train, window_size=sliding_window_size, optional_cols=optional_seatrend)

        # Create the model and fit for the data using seasonal and trend data
        model.fit(X_train_sw, y_train_sw, epochs=50, batch_size=32, verbose=0)
        # Make a Prediction
        last_sample = tf.convert_to_tensor(np.expand_dims(X_train_sw[-1], axis=0), dtype=tf.float32)
        ltsm_predictions_seas_trend = model.predict(last_sample)        
        unscaled_prediction_seatrend = minmax_sc.inverse_transform(np.pad(ltsm_predictions_seas_trend, ((0, 0), (0, len(minmax_sc.feature_names_in_) - 1)), mode='constant'))
        # ════════════════════════════════════════════════════ Prediccion del residuo (ruido) ═══════════════════════════════════════
        X_train, y_train,  = Xy_split(train_dec_df, "resid")

        # Create sliding window
        X_train_sw, y_train_sw = sliding_window_lstm(X_train, y_train, window_size=sliding_window_size, optional_cols=optional_resid)

        # Create the model and fit for the data using seasonal and trend data
        model_resid.fit(X_train_sw, y_train_sw, epochs=20, batch_size=32, verbose=0)

        # Make a Prediction
        last_sample_resid = tf.convert_to_tensor(np.expand_dims(X_train_sw[-1], axis=0), dtype=tf.float32)
        ltsm_predictions_resid = model_resid.predict(last_sample_resid)
        unscaled_prediction_resid = minmax_sc.inverse_transform(np.pad(ltsm_predictions_resid, ((0, 0), (0, len(minmax_sc.feature_names_in_) - 1)), mode='constant'))

        yhat = ltsm_predictions_seas_trend + ltsm_predictions_resid
        unscaled_prediction = minmax_sc.inverse_transform(np.pad(yhat, ((0, 0), (0, len(minmax_sc.feature_names_in_)-1)), mode='constant'))
        
        prediction_seas_trend = unscaled_prediction_seatrend[0, 0:1]
        prediction_resid = unscaled_prediction_resid[0, 0:1]
        prediction = unscaled_prediction[0, 0:1]

        predictions.extend(prediction)
        prediction_seas_trends.extend(prediction_seas_trend)
        prediction_resids.extend(prediction_resid)
        actuals.extend(y_test.values)

    # return predictions, actuals, metrics_trend_season, metrics_resid
    return {
        "predictions": {
            "seas_trend": prediction_seas_trends,
            "resid": prediction_resids,
            "total": predictions
        },
        "actuals": actuals,
        "metrics_trend_season": metrics_trend_season
    }

def results_to_df(data_df: pd.DataFrame, results, window_size: int, prediction_size: int) -> pd.DataFrame:
    new_df = data_df[window_size:].copy()
    new_df = new_df.iloc[:-prediction_size]

    new_df["Fecha"] = pd.to_datetime(
            new_df["Year"].astype(str) + "-" + new_df["Mes"].astype(str).str.zfill(2)
        )
    new_df = new_df.set_index('Fecha')

    new_df['seas_trend'] = results['predictions']['seas_trend']
    new_df['resid'] = results['predictions']['resid']
    new_df['total'] = results['predictions']['total']
    new_df['prediccion'] = results['predictions']['total']

    return new_df

def graph_predictions(data_df: pd.DataFrame, output_name: str, prediction_horizon: int, out_path: str):
    graph_name = f"grafico_wf_validation_{output_name}_{prediction_horizon}_steps.png"
    graph_title = f"Walk-Forward validation of {output_name} with an horizon of {prediction_horizon} months"

    plt.figure(figsize=(12,8))
    plt.plot(data_df.index, data_df['Valor'], label="Train (Actual)")
    plt.plot(data_df.index, data_df['seas_trend'], label="Predictions LSTM Seasonality + Trend")
    plt.plot(data_df.index, data_df['total'], label="Predictions LSTM Seasonality + Trend + Residuals")
    plt.title(graph_title)
    plt.xlabel("Date")
    plt.ylabel("Valor")
    plt.grid()
    plt.legend()
    plt.savefig(Path(out_path) / "graphs" / graph_name)
    plt.show()

def main():
    params = yaml.safe_load(open("params.yaml"))["wf_train_and_predict"]
    walking_forward = params["walking_forward"]
    
    window_size = walking_forward["window_size"]
    predict_window = walking_forward["predict_window"]
    months_to_predict = params["months_to_predict"]
    low_var = params["low_var"]
    high_corr = params["high_corr"]
    export_graphs = params["export_graphs"]
    files = params["files"]
   
    # window_size = 36
    # predict_window = 1
    # low_var = 0.01
    # high_corr = 0.95
    # export_graphs = True
    # files = ["consumodeagavetotal"]

    if len(sys.argv) != 3:
        sys.stderr.write("Arguments error. Usage:\n")
        sys.stderr.write("\tpython prepare.py data-file\n")
        sys.exit(1)

    # Create output directory if it doesn't exist
    os.makedirs(os.path.join("data", "pipeline", "wf_validation"), exist_ok=True)
    os.makedirs(os.path.join("data", "pipeline", "wf_validation", "graphs"), exist_ok=True)
    os.makedirs(os.path.join("data", "pipeline", "wf_validation", "predictions"), exist_ok=True)

    in_path = sys.argv[1]  # previous step folder
    out_path = sys.argv[2]  # output folder

    # in_path = "data/pipeline/prepared"
    # out_path = "data/pipeline/wf_validation"

    for file in files:
        # ══════════════════════════════════ Iterate through types of tequila ═════════════════════
        logging.info(f"··· Processing file: {file.upper()} ···")
        teq_df = get_df(file, in_path, "teq")
        teq100_df = get_df(file, in_path, "teq100")

        # ══════════════════════════════════ TEQUILA ══════════════════════════════════
        file_being_processed = f"{file}_teq"
        result = walk_forward_validation(teq_df, target_col="Valor", training_window=window_size, test_window=predict_window, low_var=low_var, high_corr=high_corr)
        results_df = results_to_df(teq_df, results=result, window_size=window_size, prediction_size=predict_window)

        results_df.to_csv(
                os.path.join(
                    out_path,
                    "predictions",
                    f"{file_being_processed}_walk_forward_validation.csv"
                ), index=False)

        graph_predictions(results_df, file_being_processed, predict_window, out_path)
        
        # ══════════════════════════════════ TEQUILA 100 ══════════════════════════════
        file_being_processed = f"{file}_teq100"
        result = walk_forward_validation(teq100_df, target_col="Valor", training_window=window_size, test_window=predict_window, low_var=low_var, high_corr=high_corr)

        results_df = results_to_df(teq100_df, results=result, window_size=window_size, prediction_size=predict_window)
        
        results_df.to_csv(
                os.path.join(
                    out_path,
                    "predictions",
                    f"{file_being_processed}_walk_forward_validation.csv"
                ), index=False)
        
        graph_predictions(results_df, file_being_processed, predict_window, out_path)


if __name__ == "__main__":
    main()
