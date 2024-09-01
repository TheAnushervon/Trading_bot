from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import os
import requests 
import re
from dotenv import load_dotenv
from requests import Response
from typing import Dict
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CUR_CONV_TOKEN = os.getenv('CUR_CONV_TOKEN')
GROUP_LINK = os.getenv('GROUP_LINK')
url = "https://api.binance.com/api/v3/ticker/price"
cur_conv_url = "https://api.freecurrencyapi.com/v1/latest"
def start(update, context):
    update.message.reply_text("Hi I am cryptocurrency manager!")
    context.job_queue.run_once(follow_up_message,2, context=update.message.chat_id)

def follow_up_message(context): 
    desc = "Give the pair like : BTCUSDT to provide you current price of it."
    context.bot.send_message(chat_id = context.job.context,text=desc)
    
def currency_converter(data:dict) -> str: 
    headers = {"apikey":CUR_CONV_TOKEN}
    params ={
        "base_currency": "USD",
        "currencies":"RUB" 
    }
    exchange_rate = requests.get(cur_conv_url, params=params,headers=headers)
    exchange_data = exchange_rate.json()
    
    value = int(float(data.get('price'))) * exchange_data["data"]["RUB"]
    return str(value)

def format_money(value):
    return "{:,.2f}".format(value)

def send_recap_to_channel(context, pair, buy_price, current_price, alert_type, margin):
    recap_text = (f"Symbol: {pair}\n"
                  f"Buy Price: {buy_price:.2f}\n"
                  f"Current Price: {current_price:.2f}\n"
                  f"Alert Type: {alert_type}\n"
                  f"Margin: {margin:.2f}%")
    context.bot.send_message(chat_id=GROUP_LINK, text=recap_text)

def check_price_change(context):
    job = context.job
    pair = job.context['pair']
    chat_id = job.context['chat_id']
    params = {"symbol":pair}
    initial_price = job.context.get('initial_price')
    try: 
        response = requests.get(url, params)
        data = response.json()
        current_price = round(float(data.get('price')), 3)
        print()
        print(current_price)
        if initial_price is not None:
            percentage_change = (current_price - initial_price)/initial_price * 100
            print(percentage_change)
            if abs(percentage_change) > 0.0102:
                prepared_text = (f"{pair} has changed by {percentage_change:.2f}%\nFrom {initial_price:.2f}$ to {current_price:.2f}$")
                context.bot.send_message(chat_id = chat_id, text =prepared_text)
                alert_type = "↑" if percentage_change > 0 else "↓"
                send_recap_to_channel(context, pair, initial_price, current_price, alert_type, percentage_change)
                context.job.schedule_removal()
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text="Error occurred while checking price.")
        print(f"Error: {e}")
def print_current_price(response: Response) -> str: 
    data = response.json()
    result = currency_converter(data)
    choosed = f"Info for pair: {data.get('symbol')}"

    dollars = format_money(float(data.get('price')))
    rubles = format_money(float(result))
    current_price = f"Current price:\n{dollars}$\n{rubles}rub\n"

    return choosed + "\n"  + current_price

def price(update, context):
   
    pair=update.message.text.upper()
    # print(update.message.text)
    if is_valid_trading_pair(pair):
        params = {"symbol": pair}
        try: 
            response = requests.get(url, params=params)
            print(response.json())
            update.message.reply_text(print_current_price(response))
            chat_id = update.message.chat_id
            initial_price =round(float(response.json().get('price')), 3)
            # update.message.reply_text(update.message.chat_id)
            context.job_queue.run_repeating(check_price_change, interval=3, first=0.1, context ={"pair":pair, "chat_id": chat_id, "initial_price":initial_price})
        except Exception as e:
            update.message.reply_text("Error occured while processing.")
            print(f"Error: {e}")

def is_valid_trading_pair(pair: str)->bool: 
    pattern = r'^[A-Z]{3,}$'
    return re.match(pattern, pair) is not None
def main():
    # Replace 'YOUR_TOKEN_HERE' with your bot's tokens
    updater = Updater(BOT_TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, price))

    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
