import telebot

bot = telebot.TeleBot('1206228272:AAFpEDuDi8ROgwobeuEBLt1_lydu_BUT1kA')
busy = False
user = {
    'id': '',
    'first_name': '',
    'last_name': '',
    'username': ''
}

keyboard1 = telebot.types.ReplyKeyboardMarkup(True)
keyboard1.row('BS ON', 'BS OFF')

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Бот запущен', reply_markup=keyboard1)


@bot.message_handler(content_types=['text'])
def send_text(message):
    global busy
    global user

    print(message)

    if message.text == 'BS ON' and busy is not True:

        user['id'] = message.from_user.id
        if message.from_user.first_name is not None:
            user['first_name'] = message.from_user.first_name
        else:
            user['first_name'] = ''

        if message.from_user.last_name is not None:
            user['last_name'] = message.from_user.last_name
        else:
            user['last_name'] = ''

        if message.from_user.username is not None:
            user['username'] = '(@' + message.from_user.username + ')'
        else:
            user['username'] = ''

        bot.send_message(message.chat.id,
                         f"""Работа с BrowserStack НАЧАТА.
Пользователь - {user['first_name']} {user['last_name']} {user['username']}"""
                         )
        busy = True

    elif message.text == 'BS ON' and busy is True:

        bot.send_message(message.chat.id,
                         f"""Вы не можете воспользоваться сервисом BrowserStack. 
В даный момент он используется пользователем 
{user['first_name']} {user['last_name']} {user['username']} """
                         )

    elif message.text == 'BS OFF' and busy is not True:
        bot.send_message(message.chat.id,
                         f"""Сервис BrowserStack в данный момент свободен."""
                         )

    elif message.text == 'BS OFF':
        if message.from_user.id == user['id']:
            bot.send_message(message.chat.id,
                             f"""Работа с BrowserStack ЗАКОНЧЕНА.
Пользователь - {user['first_name']} {user['last_name']} {user['username']}"""
                             )
            busy = False
        else:
            bot.send_message(message.chat.id,
                             f"""Вы не можете завершить работу
с сервисом BrowserStack.
В данный момент он используется пользователем 
{user['first_name']} {user['last_name']} {user['username']} """
                             )


bot.polling(none_stop=True)
