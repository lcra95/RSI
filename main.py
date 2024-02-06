import os
import time
import numpy as np
from binance.client import Client
import talib
import logging
import requests
import pandas as pd
import mysql.connector
import openai
import json


send__message = 0
api_key = 'iVT1aRRukap9b12jlFqrjU8ix0QOREoffD41Ey1VvLEPRWDDXt0fL2PyYVxQaQrm'
api_secret = '4byprzjIvjJfIbo0bbkg2o27buy1oFzMw0l6DydHe7y1ZdbAxF9XtszR5e5T0IKn'
client = Client(api_key, api_secret)

def mysql_conexion():
    conexion = mysql.connector.connect(
    host='170.239.85.238',            # O la dirección del servidor de base de datos
    user='lrequena',           # Tu usuario de MySQL
    password='18594LCra..',    # Tu contraseña de MySQL
    database='binance_bot'  # El nombre de tu base de datos
        )
    return conexion


def send_telegram_message(message):
    token = os.getenv('TOKEN','6609889311:AAFIVvD_0pJuz7myNLsy0QJzYo5TNDp1kKk')
    chat_id = '5090328284'
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        if send__message == 1:
            response = requests.post(url, data=data)
            return response.json()
        return 'No enviado'
    except Exception as e:
        logging.error(f"Error al enviar mensaje de Telegram: {e}")
        print(f"Error al enviar mensaje de Telegram: {e}")

def get_current_price(symbol):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])


def calculate_percentage_change(current_price, purchase_price):
    if purchase_price:
        return (current_price - purchase_price) / purchase_price * 100
    else:
        return 0


def get_close_prices(symbol, interval, lookback):
    candles = client.get_klines(symbol=symbol, interval=interval, limit=lookback)
    close_prices = [float(candle[4]) for candle in candles]
    return np.array(close_prices)


def calculate_rsi(prices, period=14):
    rsi = talib.RSI(prices, timeperiod=period)
    return rsi


def get_lot_size(client, symbol):
    info = client.get_symbol_info(symbol)
    for filter in info['filters']:
        if filter['filterType'] == 'LOT_SIZE':
            return {
                'minQty': float(filter['minQty']),
                'maxQty': float(filter['maxQty']),
                'stepSize': float(filter['stepSize'])
            }
    return None


def adjust_quantity(quantity, step_size):
    return round(quantity - (quantity % step_size), len(str(step_size).split('.')[1]))


def buy_crypto(client, symbol, amount_usd):
    current_price = get_current_price(symbol)
    lot_size = get_lot_size(client, symbol)

    if lot_size:
        quantity = amount_usd / current_price
        quantity = adjust_quantity(quantity, lot_size['stepSize'])

        if quantity < lot_size['minQty'] or quantity > lot_size['maxQty']:
            logging.error("Cantidad fuera del rango permitido por LOT_SIZE")
            print("Cantidad fuera del rango permitido por LOT_SIZE")
            return None

        try:
            order = client.order_market_buy(symbol=symbol, quantity=quantity)
            logging.info(f"Orden de compra ejecutada: {order}")
            print(f"Orden de compra ejecutada: {order}")
            send_telegram_message(f"Compra de {symbol} a {current_price} la cantidad de {quantity} ")
            return order
        except Exception as e:
            logging.error(f"Error al realizar la compra: {e}")
            print(f"Error al realizar la compra: {e}")
            return None
    else:
        logging.error("No se pudo obtener la información de LOT_SIZE")
        print("No se pudo obtener la información de LOT_SIZE")
        return None


def sell_crypto(client, symbol):
    try:
        balance = client.get_asset_balance(asset=symbol.replace("USDT", ""))
        quantity = float(balance['free'])
        lot_size = get_lot_size(client, symbol)

        if lot_size:
            quantity = adjust_quantity(quantity, lot_size['stepSize'])

            if quantity < lot_size['minQty'] or quantity > lot_size['maxQty']:
                logging.error("Cantidad de venta fuera del rango permitido por LOT_SIZE")
                print("Cantidad de venta fuera del rango permitido por LOT_SIZE")
                return None

            order = client.order_market_sell(symbol=symbol, quantity=quantity)
            logging.info(f"Orden de venta ejecutada: {order}")
            print(f"Orden de venta ejecutada: {order}")
            send_telegram_message(f"Venta {symbol} la cantidad de {quantity}")
            return order
        else:
            logging.error("No se pudo obtener la información de LOT_SIZE para la venta")
            print("No se pudo obtener la información de LOT_SIZE para la venta")
            return None
    except Exception as e:
        logging.error(f"Error al realizar la venta: {e}")
        print(f"Error al realizar la venta: {e}")
        return None


def media_movil_data(symbol, interval, lookback):
    klines = client.get_historical_klines(symbol, interval, limit=lookback)
    data = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])

    # Convertir a float los datos necesarios
    data[['close']] = data[['close']].astype(float)
    return data


def calcular_sma(data, periodo):
    """
    Calcula la Media Móvil Simple (SMA) para un DataFrame de pandas.

    :param data: DataFrame de pandas con la columna 'Close'.
    :param periodo: Número de periodos para calcular la SMA.
    :return: Serie de pandas con la SMA calculada.
    """
    return data['close'].rolling(window=periodo).mean()


def determinar_tendencia(data):
    """
    Determina si la tendencia es alcista o bajista basándose en la SMA.

    :param data: DataFrame de pandas con la columna 'Close'.
    :return: String indicando la tendencia ('Alcista', 'Bajista', 'Indeterminada').
    """
    # Calcular la SMA rápida y lenta
    sma_rapida = calcular_sma(data, 30)
    sma_lenta = calcular_sma(data, 120)

    # Comparar las últimas SMA
    sma_rapida_ultima = sma_rapida.iloc[-1]
    sma_lenta_ultima = sma_lenta.iloc[-1]

    if sma_rapida_ultima > sma_lenta_ultima:
        return {"tendencia" : 2, "lenta": sma_lenta_ultima, "rapida": sma_rapida_ultima}
        
    elif sma_rapida_ultima < sma_lenta_ultima:
        return {"tendencia" : 1, "lenta": sma_lenta_ultima, "rapida": sma_rapida_ultima}
    else:
        return {"tendencia" : 0, "lenta": sma_lenta_ultima, "rapida": sma_rapida_ultima}


def insertar_analisis_tecnico(simbolo, precio, rsi, msa_lenta_120, msa_rapida_30, estocastico):
    try:
        conexion = mysql_conexion()
        cursor = conexion.cursor()

        # Consulta para obtener la última fecha de inserción para el símbolo dado
        consulta_ultima_insercion = """
        SELECT fecha FROM analisis_tecnico 
        WHERE simbolo = %s 
        ORDER BY fecha DESC 
        LIMIT 1
        """
        cursor.execute(consulta_ultima_insercion, (simbolo,))
        resultado = cursor.fetchone()

        # Verifica si es necesario insertar un nuevo registro
        tiempo_actual = time.time()
        if resultado:
            ultima_insercion = resultado[0]
            if (tiempo_actual - ultima_insercion.timestamp()) < 59:
                #print(f"No se insertará el registro para {simbolo} ya que no ha pasado el tiempo suficiente desde la última inserción.")
                return

        # Consulta SQL para insertar datos
        consulta_insercion = """
        INSERT INTO analisis_tecnico 
        (simbolo, precio, rsi, msa_lenta_120, msa_rapida_30, estocastico) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        # Valores a insertar
        valores = (simbolo, precio, rsi, msa_lenta_120, msa_rapida_30, estocastico)

        # Ejecuta la consulta de inserción
        cursor.execute(consulta_insercion, valores)
        conexion.commit()
        #print(f"Registro insertado correctamente para {simbolo}")

    except mysql.connector.Error as error:
        print("Error al insertar los datos: ", error)

    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()


def consulta_y_exporta_excel(symbol):
    try:
        # Crea una conexión usando SQLAlchemy
        conexion = mysql_conexion()
        cursor = conexion.cursor()

        # Consulta SQL para obtener los últimos 50 registros
        consulta = f"SELECT simbolo, fecha, rsi, msa_lenta_30, msa_rapida_120, estocastico FROM analisis_tecnico WHERE simbolo = '{symbol}'ORDER BY id DESC LIMIT 30"

        # Ejecuta la consulta
        cursor.execute(consulta)

        # Itera sobre los resultados y formatea el texto
        resultados_texto = []
        for (simbolo, fecha, rsi, msa_lenta_30, msa_rapida_120, estocastico) in cursor:
            texto = f"{simbolo} - Momento:{fecha}, RSI: {rsi}, MSA rapida 30: {msa_lenta_30}, MSA lenta 120: {msa_rapida_120}, Estocástico: {estocastico}"
            resultados_texto.append(texto)

        # Une todos los textos con un salto de línea
        texto_final = "\n".join(resultados_texto)

        return texto_final

    except mysql.connector.Error as error:
        print("Error al realizar la consulta: ", error)

    finally:
        if conexion.is_connected():
            conexion.close()


def get_data_estocastico(symbol, interval, lookback):
    klines = client.get_historical_klines(symbol, interval, limit=lookback)
    data = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])

    # Convertir a float los datos necesarios
    data[['close', 'high', 'low']] = data[['close', 'high', 'low']].astype(float)

    return data


def calcular_estocastico(data, periodo=14):
    try:
        min_low = data['low'].rolling(window=periodo).min()
        max_high = data['high'].rolling(window=periodo).max()
        estocastico = 100 * ((data['close'] - min_low) / (max_high - min_low))
        return estocastico
    except Exception as e:
        print(f"Error al procesar estocastico: {e}")


def prompt_context(simbolo, datos):
    data = []
    base = f"""
            "Eres un experto en trading de criptomonedas con alta capacidad de analisis tecnico y experiencia ganadora, Con el objetivo de realizar un análisis técnico preciso, 
            te proporcionaré datos históricos detallados de los últimos 30 minutos de operaciones para el símbolo de criptomoneda {simbolo}. 
            Utiliza estos datos para evaluar si es un buen momento para entrar en una posición de compra o venta, basándote en la siguiente estrategia de trading:

            Configuración de los Indicadores:

            Medias Móviles: MA de 30 minutos (rápida) y MA de 12 minutos (lenta).
            RSI: Periodo de 14 minutos.
            Estocástico: Configuración estándar (14, 3, 3).
            Estrategia de Entrada:

            Compra: MA rápida cruza por encima de la MA lenta, RSI < 30, Estocástico confirma sobreventa.
            Venta: MA rápida cruza por debajo de la MA lenta, RSI > 70, Estocástico confirma sobrecompra.
            Estrategia de Salida:

            Cerrar Compra: RSI acerca o supera 70, Estocástico en sobrecompra, stop-loss bajo el último mínimo significativo.
            Cerrar Venta: RSI cae por debajo de 30, Estocástico en sobreventa, stop-loss sobre el último máximo significativo.
            Considera el contexto actual del mercado y los siguientes indicadores técnicos, teniendo en cuenta que los datos representan una serie temporal de los últimos 30 minutos hasta la fecha [Fecha del Momento]:

            Precio Actual: [Precios durante los últimos 30 minutos]
            Índice de Fuerza Relativa (RSI): [Valores del RSI durante los últimos 30 minutos]
            Media Móvil Simple (MSA) de 30 y 120 minutos: [Valores de las MSAs durante los últimos 30 minutos]
            Estocástico: [Valores del Estocástico durante los últimos 30 minutos]
            Basándote en este análisis de datos históricos detallados y la estrategia de trading proporcionada, proporciona una recomendación en un formato que simule un JSON. El JSON debe incluir los siguientes campos:

            compra: Indica con un '1' si se recomienda comprar y con un '2' si se recomienda no comprar.
            resumen: Proporciona un breve resumen de no más de 3 líneas, explicando la razón de la recomendación, considerando las tendencias actuales, los riesgos y la volatilidad inherente al mercado de criptomonedas."
            """
    data.append({'role': 'system', 'content': base})
    data.append({"role": "user", "content" : datos})

    return data


def chatGpt(prompt):
    openai.api_key = "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"
    
    respuestas = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=prompt,
            temperature = 0.7,
            max_tokens = 200
        )
    respuesta_actual = respuestas['choices'][0]['message']['content']
    return respuesta_actual

def get_positive_balance_symbols():
    # Obtener información de todos los tickers
    tickers = client.get_ticker()
    positive_balance_symbols = [ticker['symbol'] for ticker in tickers if ticker['symbol'].endswith('USDT') and float(ticker['priceChangePercent']) > 5]

    return positive_balance_symbols

def main():
    print("HELLO EVERITING IS RUNNING")
    #symbols = get_positive_balance_symbols()
    symbols = ['ENSUSDT', 'CKBUSDT','RONINUSDT', 'HBARUSDT' , 'PENDLEUSDT']  # Lista de símbolos a monitorear
    symbol_data = {symbol: {'in_position': False, 'purchase_price': 0, 'last_stop_loss_time': 0} for symbol in symbols}
    logging.basicConfig(filename=f'file.log', level=logging.INFO, format='%(asctime)s - %(message)s')
    interval = Client.KLINE_INTERVAL_1MINUTE
    lookback = 500
    stop_loss_percentage = 3
    sell_percentage = 2.5
    amount_usdt = 50
    rsi_limit = 25
    activar_gpt = 0
    print(symbols)
    
    while True:
        
        for symbol in symbols:
            try:
                close_prices = get_close_prices(symbol, interval, lookback)
                rsi = calculate_rsi(close_prices)
                current_price = get_current_price(symbol)
                media_movil = media_movil_data(symbol, interval, 500)
                tendencia = determinar_tendencia(media_movil)
                price = get_current_price(symbol)
                data = get_data_estocastico(symbol, interval, 500)
                estocastico = calcular_estocastico(data)
                insertar_analisis_tecnico(symbol, price, rsi[-1],tendencia["lenta"], tendencia["rapida"], estocastico.iloc[-1])

                logging.info(f"RSI Actual para {symbol}: {rsi[-1]}, Precio Actual: {current_price}")
                print(f"RSI Actual para {symbol}: {rsi[-1]}, Precio Actual: {current_price} Estocastico: {estocastico.iloc[-1]} - Tendencia {tendencia['tendencia']}")

                if not symbol_data[symbol]['in_position'] and (time.time() - symbol_data[symbol]['last_stop_loss_time']) >= 2400 and rsi[-1] < rsi_limit:
                    #pregunto a chatgpt si es conviene comprar
                    if activar_gpt == 1:
                        result = consulta_y_exporta_excel(symbol)
                        prompt = prompt_context(symbol, result)
                        respuesta = chatGpt(prompt)
                        gpt_recomendation = json.loads(respuesta)
                        print(gpt_recomendation['resumen'])
                        if gpt_recomendation["compra"] == 1:#compra si chatgpt dice que si 
                        
                            order = buy_crypto(client, symbol, amount_usdt)
                            if order:
                                symbol_data[symbol]['purchase_price'] = current_price
                                symbol_data[symbol]['in_position'] = True
                                logging.info(f"Comprado {symbol} a {current_price} USD")
                    else:
                        order = buy_crypto(client, symbol, amount_usdt)
                        if order:
                            symbol_data[symbol]['purchase_price'] = current_price
                            symbol_data[symbol]['in_position'] = True
                            logging.info(f"Comprado {symbol} a {current_price} USD")


                elif symbol_data[symbol]['in_position'] and rsi[-1] > rsi_limit:
                    percentage_change = calculate_percentage_change(current_price, symbol_data[symbol]['purchase_price'])
                    #if rsi[-1] > rsi_sell:# vendo por rsi no por porcentaje de ganancia
                    if percentage_change > sell_percentage: #vendo por porcentaje de ganancia
                        order = sell_crypto(client, symbol)
                        if order:
                            symbol_data[symbol]['in_position'] = False
                            logging.info(f"Vendido {symbol}. Detalles de la orden: {order}")

                if symbol_data[symbol]['in_position']:
                    current_change = calculate_percentage_change(current_price, symbol_data[symbol]['purchase_price'])
                    if current_change <= -stop_loss_percentage:
                        order = sell_crypto(client, symbol)
                        if order:
                            symbol_data[symbol]['last_stop_loss_time'] = time.time()
                            symbol_data[symbol]['in_position'] = False
                            send_telegram_message(f"Stop Loss en {symbol}")
                            logging.info(f"Stop loss activado en {symbol}. Detalles de la orden: {order}")

            except Exception as e:
                logging.error(f"Error en {symbol}: {e}")
                print(f"Error en {symbol}: {e}")

        time.sleep(6)  # Tiempo de espera entre cada ciclo de revisión

if __name__ == '__main__':
    main()
