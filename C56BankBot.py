from extensions import *
import telebot
from config import TOKEN

bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')
msg_list = []


def day_part(time=None):
    if time is None:
        h = datetime.timetuple(datetime.now())[3]
    else:
        h = datetime.timetuple(time)[3]

    if 0 <= h < 6:
        return 0
    elif 6 <= h <= 10:
        return 1
    elif 10 < h <= 18:
        return 2
    elif 18 < h <= 23:
        return 3


def day_part_hello(time=None):
    h = day_part(time)
    if h == 0:
        return 'Доброй ночи'
    elif h == 1:
        return 'Доброе утро'
    elif h == 2:
        return 'Добрый день'
    elif h == 3:
        return 'Добрый вечер'


def send_msg(message, msg):
    msg_list.append(bot.send_message(message.chat.id, msg).message_id)


@bot.message_handler(content_types=['text'])
def main_hook(message):
    log_add(f'{str(message.message_id)} "{message.text}"')
    command = str.split(message.text, ' ')[0]
    if command == '/start':
        log_add(f'{str(message.message_id)} "{message.text}"')
        send_welcome(message)
        send_help(message)
    elif command == '/help':
        send_help(message)
    elif command == '/values':
        send_currency_list(message)
    elif command == '/rate':
        get_rate(message)
    elif command == '/dbg':
        send_msg(message, str(msg_list))
    elif command == '/clr':
        clear_chat(message)
    else:
        if message.text[0] == '/':
            send_msg(message, f'Команда "{message.text}" мне не знакома\nНаберите `/help` для получения справки')
            # send_help(message)


def clear_chat(message):
    for m in msg_list:
        bot.delete_message(message.chat.id, m)
        log_add(f'clear_chat: {str(m)}')


def send_welcome(message):
    msg = f'{day_part_hello()}, `{message.chat.username}`!!!\n'
    if day_part() == 0 and message.chat.username == 'redbor24':
        msg += 'Чо не спишь, программер? Затянула опасная трясина? xD\n'
    msg += '\n'
    send_msg(message, msg)


def send_help(message):
    msg = f'`/start`, `/help` - справка\n'
    msg += f'`/values` _[date]_ - список валют, доступных для получения курсов, на дату. Если дата не задана, то на сегодня\n'
    msg += f'`/rate` - *base quote* _[param1] [param2]_ (через пробел, регистр не важен)\n'
    msg += f'Возвращает курс валюты *base* в валюте *quote*.'
    msg += f'  Если _param1_ задан и является числом (разделитель дробной части точка "."), то курс умножается на _param1_\n'
    msg += f'  Если _param1_ задан и является датой в формате "дд.мм.гггг", то курс берётся на указанную дату\n'
    msg += f'  _param2_ может быть только датой в формате "дд.мм.гггг"\n'
    msg += f'Примеры команд:\n'
    msg += f'  `/rate usd RUB 1` - стоимость доллара в рублях (курс рубля к доллару) на сегодняшнюю дату\n'
    msg += f'  `/rate USD eur 5` - стоимость 5 долларов в евро по курсу на сегодняшнюю дату\n'
    msg += f'  `/rate usd Rub 01.03.2010` - курс доллара к рублю на дату 01.03.2010\n'
    msg += f'  `/rate eur rUB 1 01.03.2010` - стоимость 5 долларов в рублях по курсу на дату 01.03.2010\n'
    msg += f'  `/rate uSd rub 10 01.03.2010` - стоимость 10 долларов по курсу к рублю на дату 01.03.2010\n'
    send_msg(message, msg)


def send_currency_list(message):
    _, *token = list(str.split(message.text))
    http_date = None

    if len(token) > 0:
        # проверим токен на дату
        try:
            http_date = datetime.strptime(token[0], '%d.%m.%Y')
        except ValueError:
            raise APIException(f'Некорректное значение даты: "{token[0]}"')

    try:
        dt, dt2, lst = CurrencyRate.ask_currency_list(http_date)
        if lst:
            if http_date is None:
                send_msg(message, f'{message.text}\nСписок валют на {datetime.now().strftime("%d.%m.%Y")}:\n' + ', '.join(lst))
            else:
                send_msg(message, f'{message.text}\nСписок валют на {dt.strftime("%d.%m.%Y")}:\n' + ', '.join(lst))
        else:
            send_msg(message, f'{message.text}\nСписок валют на {dt.strftime("%d.%m.%Y")} пуст')
    except APIException as e:
        send_msg(message, e)


def get_rate(message):
    log_add(f'get_rate(message): {str(message.chat.id)} "{message.text}"')
    try:
        send_msg(message, CurrencyRate.ask_rate(message.text))
    except BadCurrency as bc:
        send_msg(message, bc)
        # send_currency_list(message)
    except APIException as ae:
        send_msg(message, ae)
        send_help(message)
    except Exception as e:
        send_msg(message, f'Упс!.. Что-то пошло не так. Или не туда...\n{e}')


bot.polling(none_stop=True)
