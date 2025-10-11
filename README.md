# t4k3r - TelegramForker
Бот для Телеграмма, автоматически меняющий эмодзи в нике, эмодзи и цвет в фоне профиля, а также эмодзи и цвет в ответах на ваши сообщения (естественно, при наличии у вас **Telegram Premium**)

Возможен бан аккаунта. __Всё на свой страх и риск.__ (За год+ использования на нескольких аккаунтах никаких проблем не было)
## Получение API_ID и API_HASH:
Перейти по ссылке и залогиниться: https://my.telegram.org/auth?to=apps

Создать приложение с любым названием и оставить открытыми `App api_id` и `App api_hash`
## Обновление Ubuntu сервера:
```
apt-get update && apt-get upgrade -y
```

## Установка Docker Compose  :
```
apt install docker-compose-plugin
```


## Установка t4k3r на Ubuntu сервере:

Скачать репозиторий:
```
git clone https://github.com/maqmm/t4k3r.git
```
Открыть папку:
```
cd t4k3r
```

Создать .env:
```
cp .env.example .env
```

Редактирование .env: (если нет, то `apt install nano`):
```
nano .env
```

Заполнить `API_ID =` и `API_HASH =` данными из начала мануала (вставлять на ПКМ)

Сохранить и выйти из редактора: `Ctrl+S` и `Ctrl+X`


Запустить контейнер:
```
docker compose run --rm t4k3r /bin/bash
```

Дождаться сборки и запустить бота:
```
python main.py
```
Залогиниться в аккаунт: ввести номер через +7, код подтверждения и облачный пароль (при наличии)

После строчки `Signed in successfully as <ваш ник>; remember to not break the ToS or you will risk an account ban!` закрываем контейнер `Ctrl+C`

Запускаем контейнер в фоне:
```
docker compose up -d --remove-orphans
```
**Готово!**

**Чтобы узнать актуальные комманды управления нужно в любом чате написать и отправить `.info`**

## Для обновления:
Открыть папку:
```
cd t4k3r
```
Скачать актуальную версию:
```
git pull
```
Собрать и запустить контейнер:
```
docker compose up -d --build
```
**Готово!**

## About structure

_In writing process..._