import telebot

bot = telebot.TeleBot("8341758119:AAEi9sEFUUMWWe4OxuGoHekPb_91iy5XYXI")

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Bot ishladi! 👋")

bot.polling()
