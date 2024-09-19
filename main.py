import asyncio
import random
import json
import os
import re

from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateEmojiStatusRequest, UpdateColorRequest
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import EmojiStatus, InputStickerSetShortName, MessageEntityCustomEmoji, MessageEntityUrl
from telethon import types
from telethon.extensions import markdown
# from datetime import datetime

from dotenv import load_dotenv
load_dotenv()
sesion_name = os.getenv('SESSION_NAME')
file_path = os.getenv('EMOJI_FILE_PATH')
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')

# links - ссылка на пак : массив из айди эмодзи
# exceptions - ссылка на пак : массив из айди эмодзи
# message_background_emoji - ссылка на пак : массив адаптивных
clean_json = {"links": {}, "exceptions": [], "message_background_emoji": {}}

client = TelegramClient(sesion_name, api_id, api_hash, system_version="Windows 10", app_version='5.3.1 x64', device_model='MS-7B89', system_lang_code='ru-RU', lang_code='en')


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
        data = load_json(file_path)
        # если просто .del
        if re.match(r'(?i)\.del$', event.message.message):
            exceptions_id = data["exceptions"]
            emoji_chunks = [exceptions_id[i:i + 96] for i in range(0, len(exceptions_id), 96)]  # Разбиваем список на части по 96 элементов
            text = f'[🚫](emoji/5462882007451185227)Всего исключено **{len(exceptions_id)}** эмодзи:'
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

                text1 = f'[🚫](emoji/5454350746407419714)Было исключено **{i}** эмодзи:\n\n'
                await client.edit_message(event.chat_id, event.id, f'{text1}{text2}')
                save_json(file_path, data)

            # (для .add)
            elif re.match(r'(?i)\.add$', event.message.message.split(' ', 1)[0]):
                delete_ids = [exceptions for exceptions in data["exceptions"] if exceptions in document_ids]
                data["exceptions"] = [exceptions for exceptions in data["exceptions"] if exceptions not in document_ids]

                text = f'[😵](emoji/5463274047771000031)Удалены исключения (**{len(delete_ids)}** шт):\n\n'
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
            command_text = ".add"
            bg = " из статуса"
            just = " УЖЕ "
            save_emoji = "[⚰️](emoji/5454350746407419714)"
            add_del = "удалён"

            document_ids = [document.id for document in sticker_set.documents]

            add_or_del = remove_pack
            if re.match(r'(?i)\.add', command):
                add_or_del = add_pack
                save_emoji = '[✅](emoji/5462956611033117422)'
                add_del = "добавлен"
                bg = " в статус"
                command_text = ".del"

            if re.match(r'(?i)\.addbg', command):
                if adaptive is False:
                    fix_emoji = '[🛠](emoji/5462921117423384478)'
                    text = f'{fix_emoji}[Набор должен быть АДАПТИВНЫМ]({url}){fix_emoji}'
                    await client.edit_message(event.chat_id, event.id, text, link_preview=False)
                    return
                array_name = "message_background_emoji"
                command_text = ".delbg"
                bg = " в фон"

            elif re.match(r'(?i)\.delbg', command):
                array_name = "message_background_emoji"
                command_text = ".addbg"
                bg = " из фона"

            state = add_or_del(data, array_name, url, document_ids)

            if state is True:
                just = " "

            text = f'{save_emoji}[Набор{just}{add_del}{bg}]({url}){save_emoji}```{title} ({count} шт)````{command_text} {url}`'

            await client.edit_message(event.chat_id, event.id, text, link_preview=False)
            save_json(file_path, data)

    except Exception as e:
        text = f'[😵](emoji/5465265370703080100)**АШИПКА!**[😵](emoji/5462921117423384478)\n{e}'
        await client.edit_message(event.chat_id, event.id, text)


@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)\.clear'))
async def handler_clear(event):
    data = load_json(file_path)

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
    text = f'[😵](emoji/5226702984204797593){msg}[😵](emoji/5226702984204797593)'
    await client.edit_message(event.chat_id, event.id, text)


@client.on(events.NewMessage(outgoing=True, pattern=r'(?i)\.info'))
async def handler_commands(event):
    text = f'''
<code>.add </code><em>[ссылка на пак]</em> — добавить пак для статуса
<code>.add </code><em>[эмодзи]</em> — удалить эмозди из исключений
<code>.addbg </code><em>[ссылка на пак]</em> — добавить пак в фон сообщений

<code>.del</code> — список общих исключений
<code>.del </code><em>[ссылка на пак]</em> — удалить пак из статуса
<code>.del </code><em>[эмодзи]</em> — исключить эмозди
<code>.delbg </code><em>[ссылка на пак]</em> — удалить пак из фона сообщений

<code>.all</code> — показать все наборы для статуса
<code>.allbg</code> — показать все наборы для фона сообщений

<code>.clearstatus</code> — очистить список статуса
<code>.clearexc</code> — очистить список исключений
<code>.clearbg</code> — очистить список фона
<code>.clearall</code> — очистить ВСЕ списки

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
    text1 = text1.replace('🟫', '[🗿](emoji/5323411714836810037)')
    text2 = text2.replace('🟫', '[🗿](emoji/5323411714836810037)')
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
    data = load_json(file_path)

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
    for values in data[array_name].values():
        total_count += len(values)

    if total_count == 0:
        emoji_sad = '[😵](emoji/5463137996091962323)'  # SAD
        text = f'{emoji_sad}Всего **{total_count}** эмоджи**{status_or_bg}**{emoji_sad}\n'
        await client.edit_message(event.chat_id, event.id, text)
        return

    emoji_omg = '[😵](emoji/5454182632797521992)'  # OMG
    text = f'{emoji_omg}Всего **{total_count}** эмоджи**{status_or_bg}**{emoji_omg}\n\n'

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


async def get_random_ids(data, array_name):
    all_items = []

    # Собираем все элементы из всех массивов
    for array in data[array_name].values():
        all_items.extend(array)

    filtered_items = [num for num in all_items if num not in data['exceptions']]
    random.shuffle(filtered_items)

    return (filtered_items)


# Функция для подгонки массива
async def generate_array(length, num):
    arr2 = list(range(num))  # Генерируем второй массив от 0 до num-1
    result = []
    while len(result) < length:
        result.extend(random.sample(arr2, len(arr2)))  # Добавляем элементы arr2 в случайном порядке
    return result[:length]  # Обрезаем лишние элементы


async def change_status_emoji():
    try:
        while True:
            data = load_json(file_path)

            random_elements = await get_random_ids(data, "links")
            if not random_elements:
                random_elements = [5462921117423384478]

            for emoji_id in random_elements:
                time_sleep = random.randint(15, 30)
                if random_elements == [5462921117423384478]:
                    time_sleep = random.randint(55, 75)

                emoji = emoji_id
                # time = datetime.now().strftime("%H:%M:%S")
                # print(f'{time} {emoji}')
                status = EmojiStatus(emoji)
                # Отправляем запрос на обновление статуса
                await client(UpdateEmojiStatusRequest(status))
                # Ждем 30 секунд
                await asyncio.sleep(time_sleep)

    except Exception as e:
        print(e)
        await asyncio.sleep(300)


# профиль эмозди и цвет
async def change_profile_background_emoji_colors():
    try:
        await asyncio.sleep(random.randint(1, 7))
        while True:
            data = load_json(file_path)

            random_elements = await get_random_ids(data, "message_background_emoji")
            colors_ids = await generate_array(len(random_elements), 16)
            if not random_elements:
                random_elements = [5337323753858685200]  # кубик 20
                colors_ids = [10]  # фиолетово-КАКОЙ ТО Я ДАЛЬТОНИК

            for index, emoji_id in enumerate(random_elements, start=0):
                await client(UpdateColorRequest(
                    for_profile=True,
                    color=colors_ids[index],
                    background_emoji_id=emoji_id))
                await asyncio.sleep(random.randint(300, 600))  # время смены профиля фона эмозди и цвета

    except Exception as e:
        print(e)
        await asyncio.sleep(300)


# сообщения фон и эмоги
async def change_message_colors_and_emoji():
    try:
        await asyncio.sleep(random.randint(1, 7))
        while True:
            data = load_json(file_path)

            random_elements = await get_random_ids(data, "message_background_emoji")
            colors_ids = await generate_array(len(random_elements), 21)
            if not random_elements:
                random_elements = [5337323753858685200]  # кубик 20
                colors_ids = [9]  # фиолетово-КАКОЙ ТО Я ДАЛЬТОНИК

            for index, emoji_id in enumerate(random_elements, start=0):
                await client(UpdateColorRequest(
                    for_profile=None,
                    color=colors_ids[index],
                    background_emoji_id=emoji_id))
                await asyncio.sleep(random.randint(100, 150))  # время смены фона сообщений

    except Exception as e:
        print(e)
        await asyncio.sleep(300)


async def main():
    await client.start()
    asyncio.create_task(change_status_emoji())
    asyncio.create_task(change_profile_background_emoji_colors())
    asyncio.create_task(change_message_colors_and_emoji())

    await client.run_until_disconnected()


client.loop.run_until_complete(main())
