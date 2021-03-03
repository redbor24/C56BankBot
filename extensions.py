import requests
import json
from datetime import datetime, timedelta


class APIException(Exception):
    def __init__(self, msg):
        self.msg = msg
        super().__init__(msg)

    def __str__(self):
        return f'{self.msg}'


class BadCurrency(APIException):
    pass


def log_add(msg):
    print(f"{datetime.strftime(datetime.now(), '%d.%m.%Y %H:%M:%S')}: {msg}")


class CurrencyRate:
    try_count = 30

    @staticmethod
    def ask_currency_list(request_date=None):
        """
        :param :request_date: - None или datetime
        Возвращает список валют List на указанную дату :request_date:.
        Если :request_date: is None, то список валют считаывается на текущую дату.
        Если на указанную дату получен пустой List, то дата сдвигается на один день назад и запрашивается новый список.
        Предпринимается 30 попыток.
        Если список не был получен, то возвращается пустой List
        :return: [
            index = 0 - дата запроса
            index = 1 - дата, на которую был получен список валют
            index = 2 - список кодов валют
        ]
        """

        if request_date is None:
            _date = datetime.now()
        else:
            _date = request_date
        http_date = _date.strftime("%Y-%m-%d")

        if request_date is None:
            url = 'https://api.exchangeratesapi.io/latest'
            d = json.loads(requests.get(url).content)
            d = list(d['rates'].keys())
        else:
            _t = timedelta(days=-1)
            template_url = 'https://api.exchangeratesapi.io/history?start_at=<date_from>&end_at=<date_to>'
            n = 0
            while n <= CurrencyRate.try_count:
                url = template_url
                url = str.replace(url, '<date_from>', http_date)
                url = str.replace(url, '<date_to>', http_date)
                d = json.loads(requests.get(url).content)
                # print(f'n: {n}')
                # print(f'  d: {d}')
                # print(f'  url: {url}')

                if 'error' in list(d):
                    log_add(f'ask_currency_list({request_date}): {d["error"]}')
                    raise APIException(f'Ошибка обращения к сервису: {d["error"]}')

                if len(d['rates']) != 0:
                    break
                n += 1
                # то уменьшаем дату на один день и обращаемся снова
                _date += _t
                http_date = _date.strftime("%Y-%m-%d")

            if len(d['rates']) > 0:
                d = list(list(d['rates'].values())[0].keys())
            else:
                d = []

        # Если список не пуст и евро в нём нет
        if 'EUR' not in d and d:
            d.append('EUR')

        log_add(f'ask_currency_list({request_date})')
        return request_date, _date, sorted(d)

    @staticmethod
    def ask_rate(command):
        _date = None

        command_name, *token = list(str.split(command))

        if not (len(token) in (2, 3, 4)):
            raise APIException('Неправильная команда!\n' + command)

        amount = 1
        request_date = None
        # 3-й и 4-ый необязательные параметры
        if len(token) >= 3:
            # 3-й параметр - количество или дата
            # Проверим токен на число
            try:
                amount = float(token[2])
            except ValueError:
                # Если это не число, то проверим токен на дату
                try:
                    request_date = datetime.strptime(token[2], '%d.%m.%Y')
                except ValueError:
                    raise APIException(f'Некорректное значение 3-го параметра: "{token[2]}"')

            # 4-й параметр - может быть только датой при условии, что 3-й параметр является числом
            if len(token) == 4 and type(amount) is float:
                try:
                    request_date = datetime.strptime(token[3], '%d.%m.%Y')
                except ValueError:
                    raise APIException(f'Некорректное значение 4-го параметра: "{token[3]}"')

        # Если дата НЕ задана, то формируем http-запрос с обращением к последнему значению курса указанных валют
        if request_date is None:
            request_date, http_date, c_list = CurrencyRate.ask_currency_list()
            sub_url = 'latest?<curr>'
        # иначе - с обращением к истории с указанием дат
        else:
            _, http_date, c_list = CurrencyRate.ask_currency_list(request_date)
            sub_url = 'history?start_at=<date_from>&end_at=<date_to>'

        # 1-й обязательный параметр - валюта base
        if str.upper(token[0]) not in c_list:
            raise BadCurrency(f'Нет данных о курсе валюты {str.upper(token[0])} к {str.upper(token[1])} на дату {request_date.strftime("%d.%m.%Y")}')
        token[0] = str.upper(token[0])

        # 2-й обязательный параметр - валюта quote
        if str.upper(token[1]) not in c_list:
            raise BadCurrency(f'Нет данных о курсе валюты {str.upper(token[1])} к {str.upper(token[0])} на дату {request_date.strftime("%d.%m.%Y")}')
        token[1] = str.upper(token[1])

        template_url = f'https://api.exchangeratesapi.io/{str.replace(sub_url, "<curr>", f"base={token[0]}&symbols={token[1]}")}'
        url = template_url
        if request_date is not None:
            url = str.replace(url, '<date_from>', http_date.strftime("%Y-%m-%d"))
            url = str.replace(url, '<date_to>', http_date.strftime("%Y-%m-%d"))

        _t = timedelta(days=-1)
        d = json.loads(requests.get(url).content)

        # print(f'DEBUG: {url}')
        # print(f'DEBUG: {d}')

        n = 0
        # если на заданную дату значение курса не найдено
        while len(d['rates']) == 0:
            # то уменьшаем дату на один день и обращаемся снова
            http_date += _t
            url = template_url
            url = str.replace(url, '<date_from>', http_date.strftime("%Y-%m-%d"))
            url = str.replace(url, '<date_to>', http_date.strftime("%Y-%m-%d"))
            d = json.loads(requests.get(url).content)
            if 'error' in list(d):
                log_add(f'ask_rate("{command}"): {d["error"]}')
                raise APIException(f'Ошибка обращения к сервису: {d["error"]}')
            n += 1

            if n == CurrencyRate.try_count:
                raise APIException(f'Курс валюты не найден!')

        log_add(f'ask_rate("{command}"): {d["rates"]}')

        if request_date is None:
            return round(list(d['rates'].values())[0] * amount, 4)
        else:
            return round(list(d['rates'].values())[0][token[1]] * amount, 4)


if __name__ == '__main__':
    # print(f"ask_rate: {CurrencyRate.ask_rate('/rate usd ')}")  # error: Неправильная команда!
    # print(f"ask_rate: {CurrencyRate.ask_rate('/rate usd rub')}")  # Ok
    # print(f"ask_rate: {CurrencyRate.ask_rate('/rate usd rub q')}")  # error: Некорректное значение 3-го параметра: "q"
    # print(f"ask_rate: {CurrencyRate.ask_rate('/rate usd rub 1')}")  # Ok
    # print(f"ask_rate: {CurrencyRate.ask_rate('/rate usd rub 01.07.2018')}")  # Ok
    # print(f"ask_rate: {CurrencyRate.ask_rate('/rate usd rub 1 йцу')}")  # error: Некорректное значение 4-го параметра: "йцу"
    # print(f"ask_rate: {CurrencyRate.ask_rate('/rate usd rub 10 01.01.2000')}")  # Ok
    # print(f"ask_rate: {CurrencyRate.ask_rate('/rate usd rub 01.01.2000 1')}")  # Ok

    # print(f'ask_currency_list(): {CurrencyRate.ask_currency_list()}')
    print(f'ask_currency_list(): {CurrencyRate.ask_currency_list(datetime.strptime("02.01.2000", "%d.%m.%Y"))}')
    # print(f'ask_currency_list(): {CurrencyRate.ask_currency_list(datetime.strptime("02.01.2000", "%d.%m.%Y"))}')
    # print(f'ask_currency_list(): {CurrencyRate.ask_currency_list(datetime.strptime("01.05.2000", "%d.%m.%Y"))}')

# https://api.exchangeratesapi.io/history?start_at=2018-01-01&end_at=2018-01-01&base=USD&symbols=RUB - нет курса
# https://api.exchangeratesapi.io/latest?base=USD&symbols=RUB&start_at=2018-01-01&end_at=2018-01-01 - есть курс