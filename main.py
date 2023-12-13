import os
import time
import numpy as np
from binance.client import Client
import talib
import logging

logging.basicConfig(filename='FUNUSDT.log', level=logging.INFO, format='%(asctime)s - %(message)s')

api_key = 'iVT1aRRukap9b12jlFqrjU8ix0QOREoffD41Ey1VvLEPRWDDXt0fL2PyYVxQaQrm'
api_secret = '4byprzjIvjJfIbo0bbkg2o27buy1oFzMw0l6DydHe7y1ZdbAxF9XtszR5e5T0IKn'
client = Client(api_key, api_secret)


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
            return order
        else:
            logging.error("No se pudo obtener la información de LOT_SIZE para la venta")
            print("No se pudo obtener la información de LOT_SIZE para la venta")
            return None
    except Exception as e:
        logging.error(f"Error al realizar la venta: {e}")
        print(f"Error al realizar la venta: {e}")
        return None


def main():
    symbol = 'FUNUSDT'
    interval = Client.KLINE_INTERVAL_1MINUTE
    lookback = 500
    in_position = False
    purchase_price = 0

    while True:
        try:
            close_prices = get_close_prices(symbol, interval, lookback)
            rsi = calculate_rsi(close_prices)
            current_price = get_current_price(symbol)

            logging.info(f"RSI Actual: {rsi[-1]}, Precio Actual: {current_price}")
            print(f"RSI Actual: {rsi[-1]}, Precio Actual: {current_price}")

            if not in_position and 30 <= rsi[-1] <= 35:
                order = buy_crypto(client, symbol, 40)
                if order:
                    purchase_price = current_price
                    in_position = True
                    logging.info(f"Comprado {symbol} a {purchase_price} USD")
                    print(f"Comprado {symbol} a {purchase_price} USD")

            elif in_position and rsi[-1] > 35:
                percentage_change = calculate_percentage_change(current_price, purchase_price)
                if percentage_change > 2:
                    order = sell_crypto(client, symbol)
                    if order:
                        in_position = False
                        logging.info(f"Vendido {symbol}. Detalles de la orden: {order}")
                        print(f"Vendido {symbol}. Detalles de la orden: {order}")

            time.sleep(60)

        except Exception as e:
            logging.error(f"Error: {e}")
            print(f"Error: {e}")
            time.sleep(60)


if __name__ == '__main__':
    main()
