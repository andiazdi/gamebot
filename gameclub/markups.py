
from datetime import datetime, timedelta
import math

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from .db import (
    get_free_time_slots, 
    find_free_places, 
    get_admins,
    get_worktime,
    get_user_bookings
)


def main_markup(is_admin: bool) -> ReplyKeyboardMarkup:
    keyboard = [
            [
                KeyboardButton(text="Бронирование"),
                KeyboardButton(text="Отменить бронь")
            ],
            [
                KeyboardButton(text="Характеристики"),
                KeyboardButton(text="Время работы"),
                KeyboardButton(text="Список игр")
            ],
            [KeyboardButton(text="Прайс-лист")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="Админ панель")])
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=keyboard,
    )


def day_markup() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора дня

    :return: InlineKeyboardMarkup
    """
    buttons = []
    day_time = datetime.now()
    first_day = 1 if day_time.hour + math.ceil(day_time.minute / 60) in (23, 24)  else 0
    for i in range(first_day, 7):
        day = day_time + timedelta(days=i)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{day.day} {day.strftime('%b')} {day.year}",
                    callback_data=f"day_{day.day}.{day.month}.{day.year}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def time_start_markup(day_str: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора времени начала бронирования

    :param day_str: день в формате "dd.mm.yyyy"
    :return: InlineKeyboardMarkup
    """
    buttons = []
    day = datetime.strptime(day_str, "%d.%m.%Y")
    if day.date() == datetime.today().date():
        day = datetime.now()
    free_time_slots = get_free_time_slots(day)
    if 24 in free_time_slots:
        del free_time_slots[24]
    if 6 in free_time_slots:
        del free_time_slots[6]
    for i in range(0, len(free_time_slots), 3):
        row = []
        for hour, places_ids in list(free_time_slots.items())[i : min(i + 3, len(free_time_slots))]:
            hour_str = f"{hour}:00" if hour >= 10 else f"0{hour}:00"
            if len(places_ids) == 0:
                continue
            callback_data = f"time_start_{hour}" 
            text = f"{hour_str} {len(places_ids)} 🖥"
            row.append(
                InlineKeyboardButton(
                    text=text, callback_data=callback_data)
            )
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
    

def time_finish_markup(time_start: int, day_start: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора времени окончания бронирования

    :param time_start: время начала бронирования
    :param day_start: день в формате "dd.mm.yyyy"
    :return: InlineKeyboardMarkup
    """
    buttons = []
    date_time = datetime.strptime(f"{day_start} {time_start}:00", "%d.%m.%Y %H:%M")
    free_time_slots = get_free_time_slots(date_time)
    worktime = get_worktime(date_time) # worktime is a 
    if date_time.hour < 6:
        free_time_slots = {hour: places for hour, places in free_time_slots.items() if hour <= 6 and hour >= date_time.hour} 
    for i in range(0, len(free_time_slots), 3):
        row = []
        for hour, places_ids in list(free_time_slots.items())[i : min(i + 3, len(free_time_slots))]:
            hour_str = f"{hour}:00" if hour >= 10 else f"0{hour}:00"
            text = f"{hour_str} {len(places_ids)} 🖥"
            callback_data = callback_data=f"time_finish_{hour}"
            if hour == time_start:
                text = f"{hour}:00 ➡️"
                callback_data = " "
            row.append(
                InlineKeyboardButton(text=text, callback_data=callback_data)
            )
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def place_markup(date_time_start_str: str, date_time_finish_str: str) -> InlineKeyboardMarkup:
    date_time_start = datetime.strptime(date_time_start_str, "%d.%m.%Y %H:%M")
    if " 24:00" in date_time_finish_str:
        date_time_finish_str = date_time_finish_str.replace(" 24:00", " 00:00")
        date_time_finish = datetime.strptime(date_time_finish_str, "%d.%m.%Y %H:%M") + timedelta(days=1)
    else:
        date_time_finish = datetime.strptime(date_time_finish_str, "%d.%m.%Y %H:%M")
    buttons = []
    free_places = find_free_places(date_time_start, date_time_finish)
    for i in range(0, len(free_places), 3):
        row = []
        for place in free_places[i : min(i + 3, len(free_places))]:
            row.append(
                InlineKeyboardButton(
                    text=f"№{place.id} зал {place.hall}", callback_data=f"place_{place.id}_{place.hall}"
                )
            )
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_markup(is_main_admin) -> ReplyKeyboardMarkup:
    keyboard = [
            [KeyboardButton(text="Список бронирований")],
            [KeyboardButton(text="Изменить время работы")],
        ]
    if is_main_admin:
        keyboard.append([KeyboardButton(text="Добавить админа"),
                         KeyboardButton(text="Удалить админа")])
    keyboard.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=keyboard,
    )

def is_new_admin_super_markup() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Да", callback_data="new_admin_true"),
            InlineKeyboardButton(text="Нет", callback_data="new_admin_false"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admins_to_remove() -> InlineKeyboardMarkup:
    buttons = []
    admins = get_admins()
    for i in range(0, len(admins), 3):
        row = []
        for admin in admins[i : min(i + 3, len(admins))]:
            row.append(
                InlineKeyboardButton(
                    text=f"{admin[1]}", callback_data=f"remove_{admin[0]}"
                )
            )
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="clear")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def weekdays_list_markup(callback_data, need_forever_button=False) -> InlineKeyboardMarkup:
    # write function to make weekdays list with dates
    buttons = []
    for i in range(0, 7):
        date = datetime.now() + timedelta(days=i)
        day = f"0{date.day}" if date.day < 10 else f"{date.day}"
        month = f"0{date.month}" if date.month < 10 else f"{date.month}"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{day}.{month}.{date.year}",
                    callback_data=f"{callback_data}_{day}.{month}.{date.year}",
                )
            ]
        )
    if need_forever_button:
        buttons.append([InlineKeyboardButton(text="Всегда", callback_data=f"{callback_data}_forever")])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="clear")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def is_weekday_or_weekend_markup() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Будни", callback_data="is_weekday_weekday"),
            InlineKeyboardButton(text="Выходные", callback_data="is_weekday_weekend"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cancel_markup() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Отмена", callback_data="clear"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_bookings_markup(user_id: int) -> InlineKeyboardMarkup:
    user_bookings = get_user_bookings(user_id)
    buttons = []
    for i in range(0, len(user_bookings), 3):
        row = []
        for booking in user_bookings[i : min(i + 3, len(user_bookings))]:
            *text, booking_id = booking.split()
            text = ' '.join(text)
            row.append(
                InlineKeyboardButton(
                    text=f"{text}", callback_data=f"cancel_booking_{booking_id}" # type: ignore 
                )
            )
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="clear")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)