import asyncio
import random
import json
import os
import re
import itertools

from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateEmojiStatusRequest, UpdateColorRequest
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import EmojiStatus, InputStickerSetShortName, MessageEntityCustomEmoji, MessageEntityUrl
from telethon import types
from telethon.extensions import markdown
from telethon.errors.rpcerrorlist import DocumentInvalidError

from datetime import datetime
from collections import deque
from itertools import islice

from dotenv import load_dotenv
load_dotenv()
sesion_name = os.getenv('SESSION_NAME')
file_path = os.getenv('EMOJI_FILE_PATH')
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')

# emojis
e_del_list = '[🚫](emoji/5462882007451185227)'  # Всего исключено (no)
e_ban = '[🚫](emoji/5454350746407419714)'  # Было исключено & удалён из статуса (kick)
e_ban2 = '[🚫](emoji/5463358164705489689)'  # ban
e_delete = '[😵](emoji/5463274047771000031)'  # Удалены исключения (frag +1)
e_add = '[✅](emoji/5462956611033117422)'  # добавлен в статус (save)
e_fix = '[🛠](emoji/5462921117423384478)'  # FIX
e_l_error = '[😵](emoji/5465265370703080100)'
e_r_error = e_fix
e_cleared = '[😵](emoji/5226702984204797593)'  # список исключений очищен (wipe)
e_invisible = '[🗿](emoji/5323411714836810037)'
e_omg = '[😵](emoji/5454182632797521992)'  # OMG
e_sad = '[😵](emoji/5463137996091962323)'  # SAD
e_default = 5337323753858685200  # стандартный при пустом json (кубик 20)

banALL = False
ban_list = []

# message colors
# номер ряда (в приложении) - номер цвета в ряду = id
# 1-1 = 5     2-1 = 12     3-1 = 14
# 1-2 = 3     2-2 = 10     3-2 = 15
# 1-3 = 1     2-3 = 8      3-3 = 16
# 1-4 = 0     2-4 = 7      3-4 = 17
# 1-5 = 2     2-5 = 9      3-5 = 18
# 1-6 = 4     2-6 = 11     3-6 = 19
# 1-7 = 6     2-7 = 13     3-7 = 20
default_message_color_id = 9

# profile colors
# номер ряда (в приложении) - номер цвета в ряду = id
# 1-1 = 5    2-1 = 13
# 1-2 = 3    2-2 = 11
# 1-3 = 1    2-3 = 9
# 1-4 = 0    2-4 = 8
# 1-5 = 2    2-5 = 10
# 1-6 = 4    2-6 = 12
# 1-7 = 6    2-7 = 14
# 1-8 = 7    2-8 = 15
default_profile_color_id = 10

# массив с логами последних эмоги
logs = {
    'main': deque(maxlen=100),  # основные эмоги профиля
    'bg': deque(maxlen=100),    # эмоги фона профиля
    'msg': deque(maxlen=100)    # эмоги фона сообщений
}


# links - ссылка на пак : массив из айди эмодзи
# exceptions - ссылка на пак : массив из айди эмодзи
# message_background_emoji - ссылка на пак : массив адаптивных
clean_json = {"links": {}, "exceptions": [], "message_background_emoji": {}}

client = TelegramClient(sesion_name, api_id, api_hash, system_version="Windows 10", app_version='5.13.1 x64', device_model='MS-7B89', system_lang_code='ru-RU', lang_code='en')


# обман чтобы набрать классы (для работы этой конструкции [✅](emoji/5454014806950429357))
class CustomMarkdown:
    @staticmethod
    def parse(text):
        text, entities = markdown.parse(text)
        for i, e in enumerate(entities):
            if isinstance(e, types.MessageEntityTextUrl):
                if e.url == 'spoiler':
                    entities[i] = types.MessageEntitySpoiler(e.offset, e.length)
                elif e.url.startswith('emoji/'):
                    entities[i] = types.MessageEntityCustomEmoji(e.offset, e.length, int(e.url.split('/')[1]))
        return text, entities

    @staticmethod
    def unparse(text, entities):
        for i, e in enumerate(entities or []):
            if isinstance(e, types.MessageEntityCustomEmoji):
                entities[i] = types.MessageEntityTextUrl(e.offset, e.length, f'emoji/{e.document_id}')
            if isinstance(e, types.MessageEntitySpoiler):
                entities[i] = types.MessageEntityTextUrl(e.offset, e.length, 'spoiler')
        return markdown.unparse(text, entities)


client.parse_mode = CustomMarkdown()


# Функция для загрузки данных из файла
def load_json(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as json_file:
            json.dump(clean_json, json_file)

    with open(file_path, 'r') as json_file:
        return json.load(json_file)


# Функция для сохранения данных в файл
def save_json(file_path, data):
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, separators=(", ", ": "))


# Функция для добавления записи
def add_pack(data, array_name, link_name, values_array):
    if link_name in data[array_name]:
        return False

    data[array_name][link_name] = values_array
    return True


# Функция для удаления записи
def remove_pack(data, array_name, link_name, _):
    if link_name in data[array_name]:
        del data[array_name][link_name]
        return True
    return False


@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)\.(add|del)'))
async def handler_add(event):
    try:
        data = await asyncio.to_thread(load_json, file_path)
        # если просто .del
        if re.match(r'(?i)\.del$', event.message.message):
            exceptions_id = data["exceptions"]
            emoji_chunks = [exceptions_id[i:i + 96] for i in range(0, len(exceptions_id), 96)]  # Разбиваем список на части по 96 элементов
            text = f'{e_del_list}Всего исключено **{len(exceptions_id)}** эмодзи:'
            await client.edit_message(event.chat_id, event.id, text)
            # Для каждого чанка создаем новое сообщение
            for chunk in emoji_chunks:
                text = ""
                for emoji in chunk:
                    text += f'[🛠](emoji/{emoji})'
                await client.send_message(event.chat_id, text)
                await asyncio.sleep(random.randint(1, 3))

        # если есть эмоги в сообщении
        elif isinstance(event.entities[0], MessageEntityCustomEmoji):
            document_ids = [entity.document_id for entity in event.entities]
            # (для .del)
            if re.match(r'(?i)\.del$', event.message.message.split(' ', 1)[0]):
                i = 0
                text2 = ""
                for value in document_ids:
                    if value not in data["exceptions"]:
                        data["exceptions"].append(value)
                        text2 += f'[🚫](emoji/{value})'
                        i += 1

                text1 = f'{e_ban}Было исключено **{i}** эмодзи:\n\n'
                await client.edit_message(event.chat_id, event.id, f'{text1}{text2}')
                save_json(file_path, data)

            # (для .add)
            elif re.match(r'(?i)\.add$', event.message.message.split(' ', 1)[0]):
                delete_ids = [exceptions for exceptions in data["exceptions"] if exceptions in document_ids]
                data["exceptions"] = [exceptions for exceptions in data["exceptions"] if exceptions not in document_ids]

                text = f'{e_delete}Удалены исключения (**{len(delete_ids)}** шт):\n\n'
                for emoji in delete_ids:
                    text += f'[🗡](emoji/{emoji})'

                await client.edit_message(event.chat_id, event.id, text)
                save_json(file_path, data)

        # если есть ссылка в сообщении
        elif isinstance(event.entities[0], MessageEntityUrl):
            command = event.message.message.split(' ', 1)[0]
            url = event.message.message.rsplit(' ', 1)[-1]
            sticker_set_name = url.split('addemoji/')[-1]

            sticker_set = await client(GetStickerSetRequest(InputStickerSetShortName(sticker_set_name), hash=0))
            title = sticker_set.set.title
            count = sticker_set.set.count
            adaptive = sticker_set.set.text_color
            array_name = "links"
            command_text = ".add"  # на команду del
            bg = " из статуса"
            just = " УЖЕ "
            save_emoji = e_ban
            add_del = "удалён"

            document_ids = [document.id for document in sticker_set.documents]

            add_or_del = remove_pack
            if re.match(r'(?i)\.add', command):
                add_or_del = add_pack
                save_emoji = e_add
                add_del = "добавлен"
                bg = " в статус"
                command_text = ".add"  # на команду add

            if re.match(r'(?i)\.addbg', command):
                if adaptive is False:
                    text = f'{e_fix}[Набор должен быть АДАПТИВНЫМ]({url}){e_fix}'
                    await client.edit_message(event.chat_id, event.id, text, link_preview=False)
                    return
                array_name = "message_background_emoji"
                command_text = ".addbg"  # на команду addbg
                bg = " в фон"

            elif re.match(r'(?i)\.delbg', command):
                array_name = "message_background_emoji"
                command_text = ".addbg"  # на команду delbg
                bg = " из фона"

            state = add_or_del(data, array_name, url, document_ids)

            if state is True:
                just = " "

            emoji_ids = document_ids[:10]
            emojis = ""

            for emoji_id in emoji_ids:
                emojis += f'[😵](emoji/{emoji_id})'
            # text = f'{save_emoji}[Набор{just}{add_del}{bg}]({url}){save_emoji}```{title} ({count} шт)````{command_text} {url}`'
            text = f'{save_emoji}Набор{just}**{add_del}{bg}**{save_emoji}\n\n{emojis}\n\n[{title} ({count} шт)]({url})\n\n`{command_text} {url}`'

            await client.edit_message(event.chat_id, event.id, text, link_preview=False)
            save_json(file_path, data)

    except Exception as e:
        text = f'{e_l_error}**АШИПКА!**{e_r_error}\n{e}'
        await client.edit_message(event.chat_id, event.id, text)


@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)\.clear'))
async def handler_clear(event):
    data = await asyncio.to_thread(load_json, file_path)

    if re.match(r'(?i)\.clearstatus$', event.message.message):
        data["links"] = clean_json["links"]
        msg = "Список **статуса** очищен"

    elif re.match(r'(?i)\.clearexc$', event.message.message):
        data["exceptions"] = clean_json["exceptions"]
        msg = "Список **исключений** очищен"

    elif re.match(r'(?i)\.clearbg$', event.message.message):
        data["message_background_emoji"] = clean_json["message_background_emoji"]
        msg = "Список **фона** очищен"

    elif re.match(r'(?i)\.clearall$', event.message.message):
        data = clean_json
        msg = "**ВСЕ** cписки очищены"

    else:
        await asyncio.sleep(1)
        await client.delete_messages(event.chat_id, [event.id, event.id])
        return

    save_json(file_path, data)
    text = f'{e_cleared}{msg}{e_cleared}'
    await client.edit_message(event.chat_id, event.id, text)


@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^\.ban(?:\s+(\d+)|(?:\s+@(\w+))|all)$'))
async def handler_bans(event):
    is_banall = event.text.lower().endswith('all')  # Проверка на .banall
    if is_banall:
        if banALL:
            await client.edit_message(event.chat_id, event.id, f"{e_ban2} **Все** запросы уже заблокированы")
            return
        await ban_function("all", event.chat_id, event.id)
    else:
        username = event.pattern_match.group(2)   # Юзернейм (если есть @)
        try:
            if username:
                user = await client.get_entity(username)
            else:
                user_id = event.pattern_match.group(1)  # Число (если есть)
                user = await client.get_entity(int(user_id))
        except Exception as e:
            await client.edit_message(event.chat_id, event.id, e)
        if user.id in ban_list:
            await client.edit_message(event.chat_id, event.id, f"{e_ban2} Пользователь **УЖЕ** в бане")
            return
        await ban_function("list", event.chat_id, event.id, user=user)


async def ban_function(type, chat_id, msg_id, user=None):
    global banALL, ban_list
    time = random.randint(900, 1800)
    if type == "all":
        banALL = True
        text = f"{e_ban2} **Все** запросы заблокированы на {time} с"
        await client.edit_message(chat_id, msg_id, text)
        await asyncio.sleep(time)
        banALL = False

    if type == "list":
        ban_list.append(user.id)
        last_name = f" {user.last_name}" if user.last_name else ""
        username = f" @{user.username}" if user.username else ""
        name = user.first_name + last_name + username
        text = f"{e_ban2} Запросы **{name}** заблокированы на {time} с"
        await client.edit_message(chat_id, msg_id, text)
        await asyncio.sleep(time)
        ban_list.remove(user.id)


@client.on(events.NewMessage(pattern=r'(?i)^\.(logs|logsbg|logsmsg)(?:\s+(\d+)|\s+@(\w+)(?:\s+(\d+))?)?$'))
async def handler_logs(event):
    if event.from_id is None:
        pass
    else:
        if banALL or event.from_id.user_id in ban_list:
            return

    me = await client.get_me()
    sender = await event.get_sender()
    # .logs @username 10
    # command - .logs
    # num1 - число после logs если без @username
    # username_msg - @username
    # num2 - 10
    command = event.pattern_match.group(1)
    num1 = event.pattern_match.group(2)
    username_msg = event.pattern_match.group(3)
    num2 = event.pattern_match.group(4)

    # если сообщение не от себя и есть @username(чьи логи хотят) и (число) и человек в контактах
    if event.out is False and username_msg == me.username and sender.contact:
        if num2 is None:
            count = 5
        else:
            count = int(num2)
        type = "send"

    # если сообщение от себя и нет @username
    elif event.out is True and username_msg is None:
        if num1 is None:
            count = 5
        else:
            count = int(num1)
        type = "edit"

    else:
        return

    if not 0 < count < 101:
        count = 5

    # фильтры на типы логов
    if command == ".logsbg":
        last_logs = islice(logs["bg"], max(0, len(logs["bg"]) - count), None)
        if len(logs["bg"]) < count:
            count = len(logs["bg"])
        text = f"{count} эмоджи **фона профиля**:\n"

    elif command == "logsmsg":
        last_logs = islice(logs["msg"], max(0, len(logs["msg"]) - count), None)
        if len(logs["msg"]) < count:
            count = len(logs["msg"])
        text = f"{count} эмоджи **фона сообщений**:\n"
    else:
        last_logs = islice(logs["main"], max(0, len(logs["main"]) - count), None)
        if len(logs["main"]) < count:
            count = len(logs["main"])
        text = f"{count} эмоджи **профиля**:\n"

    text += '\n'.join(map(str, last_logs))

    if type == "edit":
        await client.edit_message(event.chat_id, event.id, text)
    elif type == "send":
        await client.send_message(event.chat_id, text)


# узнать количество эмоги и наборов в data.json
async def count_emoji():
    data = await asyncio.to_thread(load_json, file_path)
    array_names = ["links", "message_background_emoji", "exceptions"]
    numbers = []

    for array_name in array_names:
        total_count = 0
        total_packs = len(data[array_name])
        if not array_name == "exceptions":
            for values in data[array_name].values():
                total_count += len(values)
            numbers.append(total_count)
            numbers.append(total_packs)
        else:
            numbers.append(total_packs)
    return numbers


@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)\.backup'))
async def handler_backup(event):
    counts = await count_emoji()
    date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    text = f"""
<em>{date}</em>

<b>В статусе</b>:
<b>{counts[0]}</b> эмодзи (<b>{counts[1]}</b> packs)

<b>В фоне</b>:
<b>{counts[2]}</b> эмодзи (<b>{counts[3]}</b> packs)

<b>Исключено</b>:
<b>{counts[4]}</b> эмодзи
"""
    await client.edit_message(event.chat_id, event.id, text, file=file_path, parse_mode='html')


@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)\.info'))
async def handler_commands(event):
    text = f'''
<code>.add </code><em>[ссылка на набор]</em> — добавить набор в статус профиля
<code>.add </code><em>[эмодзи]</em> — удалить эмодзи из исключений
<code>.addbg </code><em>[ссылка на набор]</em> — добавить набор в фон профиля и сообщений

<code>.del</code> — список общих исключений
<code>.del </code><em>[ссылка на набор]</em> — удалить набор из статуса профиля
<code>.del </code><em>[эмодзи]</em> — исключить эмодзи
<code>.delbg </code><em>[ссылка на набор]</em> — удалить набор из фона профиля и сообщений

<code>.all</code> — показать все наборы статуса профиля
<code>.allbg</code> — показать все наборы фона профиля и сообщений

<code>.clearstatus</code> — удалить все наборы из статуса
<code>.clearexc</code> — удалить все эмодзи-исключения
<code>.clearbg</code> — удалить все наборы из фона
<code>.clearall</code> — удалить ВСЕ наборы эмодзи

<code>.backup</code> — выгрузить файл со всеми наборами

<code>.logs </code><em>[N]</em> — показать последние N (до 100) эмодзи профиля
<code>.logsmsg </code><em>[N]</em> — показать последние N (до 100) эмодзи фона сообщений
<code>.logsbg </code><em>[N]</em> — показать последние N (до 100) эмодзи фона профиля

<code>.logs </code><em>@username [N]</em> — показать последние N (до 100) эмодзи профиля данного пользователя
<code>.logsmsg </code><em>@username [N]</em> — показать последние N (до 100) эмодзи фона сообщений данного пользователя
<code>.logsbg </code><em>@username [N]</em> — показать последние N (до 100) эмодзи фона профиля данного пользователя

<code>.ban </code><em>@username</em> — временно запретить пользователю запрашивать ваши последние эмодзи
<code>.banall</code> — временно запретить ВСЕМ пользователям запрашивать ваши последние эмодзи

<code>.🗿</code> — чертила
    '''
    await client.edit_message(event.chat_id, event.id, text, parse_mode='html')


@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)\.🗿'))
async def handler_stone(event):
    text1 = '''
🟫🟫🟫🟫🟫🟥🟥🟫
🟫🟥🟥🟫🟫🟫🟫🟫
🟫🟫🟫🟫🟫🟫🟫🟫
🟫🟫🟥🟫🟫🟥🟫🟫
🟫🟫🟥🟫🟫🟥🟫🟫
🟫🟫🟫🟫🟫🟫🟫🟫
🟫🟥🟥🟥🟥🟥🟥🟫'''

    text2 = '''
🟫🟥🟥🟫🟫🟫🟫🟫
🟫🟫🟫🟫🟫🟥🟥🟫
🟫🟫🟫🟫🟫🟫🟫🟫
🟫🟫🟥🟫🟫🟥🟫🟫
🟫🟫🟥🟫🟫🟥🟫🟫
🟫🟫🟫🟫🟫🟫🟫🟫
🟫🟥🟥🟥🟥🟥🟥🟫'''
    text1 = text1.replace('🟫', e_invisible)
    text2 = text2.replace('🟫', e_invisible)
    text = [text1, text2, text1, text2, text1]

    stone = [5796270094954794959, 5796528609036341197, 5796151871685006544, 5794130221988844552, 5796154775082896990, 5794315425273614049, 5794405619586829877, 5796637413442850695, 5796181768952352381, 5794036222334603423, 5796662569066303188, 5794254763155525471, 5796149316179463874, 5796173161837891411, 5796578963232920077, 5794204000937055520, 5796658467372536325, 5796656182449933846, 5793905539364687563, 5796303239217418190, 5794380773201022246, 5794051787296084051, 5796141404849705080, 5794038760660274509, 5794180571890455776, 5794120871845040459, 5796694424838737320, 5796382747652001425, 5794287142913969546, 5794135015172345363, 5794109782239482498, 5796503277319228628, 5796582124328849695, 5794163374841401278, 5794129105297348415, 5796334970435800723, 5796211743529111404, 5796636618873900998, 5794401062626529888, 5796615676613365556, 5213305508034783384, 5172645971766543291, 5208878706717636743, 5208601921845208724, 5192683149548605430]

    random.shuffle(stone)
    stone = stone[:4]
    stone.append(5442983582882601962)

    for index, emoji in enumerate(text, start=0):
        message = text[index].replace('🟥', f'[🗿](emoji/{stone[index]})')
        await client.edit_message(event.chat_id, event.id, message)
        await asyncio.sleep(1)


@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)\.all'))
async def handler_all(event):
    data = await asyncio.to_thread(load_json, file_path)

    if re.match(r'(?i)\.allbg', event.message.message.split(' ', 1)[0]):
        array_name = "message_background_emoji"
        dot_add_del = ".delbg"
        status_or_bg = " для фона"
    else:
        array_name = "links"
        dot_add_del = ".del"
        status_or_bg = " в статусе"

    link_names = list(data[array_name].keys())

    total_count = 0
    total_packs = len(data[array_name])  # вывод количества наборов в .all
    for values in data[array_name].values():
        total_count += len(values)

    if total_count == 0:
        text = f'{e_sad}Всего **{total_count}** эмоджи**{status_or_bg}**{e_sad}'
        await client.edit_message(event.chat_id, event.id, text)
        return

    text = f'{e_omg}Всего **{total_count}** эмоджи**{status_or_bg}**{e_omg}\n{e_invisible}From **{total_packs}** packs\n\n'  # вывод количества наборов в .all

    for index, url in enumerate(link_names, start=1):
        emoji_ids = data[array_name][url][:5]
        emojis = ""

        for emoji_id in emoji_ids:
            emojis += f'[😵](emoji/{emoji_id})'

        text += f'{index}. {emojis}\n{url}\n`{dot_add_del} {url}`\n\n'

        if index % 19 == 0:
            if index == 19:  # Если это первое сообщение
                await client.edit_message(event.chat_id, event.id, text, link_preview=False)
            else:
                await client.send_message(event.chat_id, text, link_preview=False)
            text = ""
            await asyncio.sleep(random.randint(1, 3))

    if text:
        if index < 19:
            await client.edit_message(event.chat_id, event.id, text, link_preview=False)
        else:
            await client.send_message(event.chat_id, text, link_preview=False)


async def get_random_ids(data, array_name, max_len=27000):  # ~неделя неповтораящихся
    exceptions = set(data['exceptions'])
    all_items = itertools.chain.from_iterable(
        (num for num in array if num not in exceptions)
        for array in data[array_name].values())

    all_items = list(all_items)  # Materialize only once
    if len(all_items) <= max_len:
        random.shuffle(all_items)
        return all_items

    return random.sample(all_items, max_len)


# Функция для подгонки массива
async def generate_array(length, num):
    arr2 = list(range(num))  # Генерируем второй массив от 0 до num-1
    result = []
    while len(result) < length:
        result.extend(random.sample(arr2, len(arr2)))  # Добавляем элементы arr2 в случайном порядке
    return result[:length]  # Обрезаем лишние элементы


# удаление из json наборов которых больше нет (владелец удалил)
async def remove_deleted_packs(emoji_id, array_name):
    data = await asyncio.to_thread(load_json, file_path)
    for url, ids in data[array_name].items():
        if emoji_id in ids:
            remove_pack(data, array_name, url, None)
            save_json(file_path, data)
            for log in logs.values():
                log.append(f"Удалён набор: {url}")
            print(f"Удалён набор: {url}")
            break


# профиль эмозди
async def change_status_emoji():
    array_name_in_json = "links"
    while True:
        try:
            data = await asyncio.to_thread(load_json, file_path)

            random_elements = await get_random_ids(data, array_name_in_json)
            if not random_elements:
                random_elements = [e_default]

            for emoji_id in random_elements:
                time_sleep = random.randint(15, 30)  # время смены эмоги в профиле
                if random_elements == [e_default]:
                    time_sleep = random.randint(55, 75)

                time = datetime.now().strftime("%H:%M:%S")
                status = EmojiStatus(emoji_id)
                # Отправляем запрос на обновление статуса
                await client(UpdateEmojiStatusRequest(status))
                logs["main"].append(f"[🗿](emoji/{emoji_id}) – {time}")
                # Ждем 15-30 секунд
                await asyncio.sleep(time_sleep)

        except DocumentInvalidError as e:
            print(datetime.now(), e)
            await remove_deleted_packs(emoji_id, array_name_in_json)
            await asyncio.sleep(5)
        except Exception as e:
            print(datetime.now(), e)
            await asyncio.sleep(300)


# профиль фон эмозди и цвет
async def change_profile_background_emoji_colors():
    array_name_in_json = "message_background_emoji"
    await asyncio.sleep(random.randint(2, 4))
    while True:
        try:
            data = await asyncio.to_thread(load_json, file_path)

            random_elements = await get_random_ids(data, array_name_in_json)
            colors_ids = await generate_array(len(random_elements), 16)
            if not random_elements:
                random_elements = [e_default]  # кубик 20
                colors_ids = [default_profile_color_id]

            for index, emoji_id in enumerate(random_elements, start=0):
                time = datetime.now().strftime("%H:%M:%S")
                await client(UpdateColorRequest(
                    for_profile=True,
                    color=colors_ids[index],
                    background_emoji_id=emoji_id))
                logs["bg"].append(f"[🗿](emoji/{emoji_id}) – {time}")
                await asyncio.sleep(random.randint(300, 600))  # время смены профиля фона эмозди и цвета

        except DocumentInvalidError as e:
            print(datetime.now(), e)
            await remove_deleted_packs(emoji_id, array_name_in_json)
            await asyncio.sleep(5)
        except Exception as e:
            print(datetime.now(), e)
            await asyncio.sleep(300)


# сообщения фон и эмоги
async def change_message_colors_and_emoji():
    array_name_in_json = "message_background_emoji"
    await asyncio.sleep(random.randint(3, 9))
    while True:
        try:
            data = await asyncio.to_thread(load_json, file_path)

            random_elements = await get_random_ids(data, "message_background_emoji")
            colors_ids = await generate_array(len(random_elements), 21)
            if not random_elements:
                random_elements = [e_default]
                colors_ids = [default_message_color_id]

            for index, emoji_id in enumerate(random_elements, start=0):
                time = datetime.now().strftime("%H:%M:%S")
                await client(UpdateColorRequest(
                    for_profile=None,
                    color=colors_ids[index],
                    background_emoji_id=emoji_id))
                logs["msg"].append(f"[🗿](emoji/{emoji_id}) – {time}")
                await asyncio.sleep(random.randint(100, 150))  # время смены фона сообщений

        except DocumentInvalidError as e:
            print(datetime.now(), e)
            await remove_deleted_packs(emoji_id, array_name_in_json)
            await asyncio.sleep(5)
        except Exception as e:
            print(datetime.now(), e)
            await asyncio.sleep(300)


async def main():
    await client.start()
    asyncio.create_task(change_status_emoji())
    asyncio.create_task(change_profile_background_emoji_colors())
    asyncio.create_task(change_message_colors_and_emoji())

    await client.run_until_disconnected()


client.loop.run_until_complete(main())
