from aiogram import Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile

from .config import TOKEN
from .markups import (
    day_markup,
    main_markup,
    time_finish_markup,
    time_start_markup,
    place_markup,
    admin_markup,
    is_new_admin_super_markup,
    admins_to_remove,
    weekdays_list_markup,
    cancel_markup,
    is_weekday_or_weekend_markup,
    user_bookings_markup
)
from .messages_text import PLACE_TEXT  # noqa F401
from .messages_text import (
    DAY_TEXT,
    GAMES_TEXT,
    HELLO_TEXT,
    SPECIFICATIONS_TEXT,
    TIME_FINISH_TEXT,
    TIME_START_TEXT,
    WORKING_HOURS_TEXT
)

from .db import (
    book_place,
    is_admin,
    remove_admin,
    add_admin,
    is_admin,
    is_main_admin,
    dump_to_excel,
    update_worktime,
    cancel_booking
)

from .bot import bot
dp = Dispatcher()


class BookingPlace(StatesGroup):
    choosing_day = State()
    choosing_start_time = State()
    choosing_finish_time = State()
    choosing_place = State()

class AdminPanel(StatesGroup):
    addding_id = State()
    is_new_admin_super = State()
    removing_admin = State()
    changing_worktime = State()
    choosing_date_for_worktime = State()
    is_weekday_or_weekend = State()

@dp.message(Command("start"))
async def start(message: types.Message):
    assert message.from_user is not None
    await message.answer(HELLO_TEXT, reply_markup=main_markup(await is_admin(message.from_user.id)))


@dp.message(F.text == "Время работы")
async def working_hours(message: types.Message):
    await message.answer(WORKING_HOURS_TEXT)


@dp.message(F.text == "Список игр")
async def game_list(message: types.Message):
    await message.answer_document(FSInputFile("static/games.pdf"), caption=GAMES_TEXT)


@dp.message(F.text == "Характеристики")
async def properties(message: types.Message):
    await message.answer(SPECIFICATIONS_TEXT)


@dp.message(F.text == "Прайс-лист")
async def price_list(message: types.Message):
    await message.answer_photo(FSInputFile("static/pricelist.jpg"))


@dp.message(F.text == "Отменить бронь")
async def user_bookings(message: types.Message, state: FSMContext):
    await message.answer("Выберите бронь", 
                         reply_markup=user_bookings_markup(message.chat.id))


@dp.callback_query(F.data.startswith("cancel_booking_"))
async def cancel_booking_callback(call: types.CallbackQuery):
    assert call.data is not None and call.message is not None
    booking_id = int(call.data.split("_")[-1])
    cancel_booking(booking_id)
    await bot.edit_message_text(
        text="Бронь отменена",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )


@dp.message(F.text == "Админ панель")
async def admin_panel(message: types.Message):
    assert message.from_user is not None
    if not await is_admin(message.from_user.id):
        return
    await message.answer("Вы вошли в админ панель", reply_markup=admin_markup(is_main_admin(message.from_user.id)))
    

@dp.message(F.text == "Изменить время работы")
async def change_worktime(message: types.Message, state: FSMContext):
    assert message.from_user is not None
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите новое время работы в формате HH:00-HH:00", reply_markup=cancel_markup())
    await state.set_state(AdminPanel.changing_worktime)


@dp.message(AdminPanel.changing_worktime)
async def change_worktime_(message: types.Message, state: FSMContext):
    assert message is not None and message.text is not None and message.from_user is not None
    if not await is_admin(message.from_user.id):
        return
    if len(message.text.split("-")) != 2:
        await message.answer("Введите корректное время работы")
        return

    time_start, time_finish = message.text.split("-")
    if time_start.endswith(":00") is False or time_finish.endswith(":00") is False:
        await message.answer("Введите корректное время работы")
        return
    time_start_ = time_start.split(":")[0]
    time_finish_ = time_finish.split(":")[0]
    if not time_start_.isdigit() or not time_finish_.isdigit():
        await message.answer("Введите корректное время работы")
        return
    time_start_ = int(time_start_)
    time_finish_ = int(time_finish_)
    if time_start_ < 0 or time_start_ > 24 or time_finish_ < 0 or time_finish_ > 24:
        await message.answer("Введите корректное время работы")
        return
    await state.set_data({"time_start": time_start, "time_finish": time_finish})
    await state.set_state(AdminPanel.choosing_date_for_worktime)
    await message.answer("Введите дату, на которую хотите изменить время работы", reply_markup=weekdays_list_markup(callback_data="change_worktime", need_forever_button=True))


@dp.callback_query(F.data.startswith("change_worktime_"))
async def change_worktime_date(call: types.CallbackQuery, state: FSMContext):
    assert call.message is not None
    date = call.data.split("_")[-1] # type: ignore
    await state.update_data({"date": date})
    await bot.delete_message(call.message.chat.id, call.message.message_id) 
    await state.set_state(AdminPanel.is_weekday_or_weekend)
    if (await state.get_data())["date"] != "forever":
        await state.update_data({"is_weekday": "for_given_date"})
        return await is_weekday_or_weekend_callback(call, state)
    await call.message.answer("Это будний день?", reply_markup=is_weekday_or_weekend_markup()) # type: ignore


@dp.callback_query(F.data.startswith("is_weekday_"))
async def is_weekday_or_weekend_callback(call: types.CallbackQuery, state: FSMContext):
    assert call.data is not None and call.message is not None
    data = await state.get_data()
    is_weekday = data.get("is_weekday", call.data.split("_")[-1] == "weekday")
    data = await state.get_data()
    time_start = data["time_start"]
    time_finish = data["time_finish"]
    date = data["date"]
    update_worktime(time_start, time_finish, date, is_weekday)
    if is_weekday == "for_given_date":
        await call.message.answer( # type: ignore
            text="Время работы изменено"
        )
        await state.clear()
        return
    await bot.edit_message_text(
        text="Время работы изменено",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    await state.clear()

@dp.message(F.text == "Добавить админа")
async def add_admin_panel(message: types.Message, state: FSMContext):
    assert message.from_user is not None
    if not is_main_admin(message.from_user.id):
        return
    await message.answer("Введите user_id пользователя (/get_id), которого хотите сделать админом", reply_markup=cancel_markup())
    await state.set_state(AdminPanel.addding_id)


@dp.message(AdminPanel.addding_id)
async def add_admin_(message: types.Message, state: FSMContext):
    assert message is not None and message.text is not None
    if not is_main_admin(message.from_user.id): # type: ignore
        return
    if not message.text.isdigit():
        await message.answer("Введите корректный user_id")
        return
    await state.set_state(AdminPanel.is_new_admin_super)
    await state.update_data({"user_id": int(message.text)}) 
    await message.answer("Этот пользователь будет супер админом?", reply_markup=is_new_admin_super_markup())


@dp.callback_query(F.data.startswith("new_admin_"))
async def is_new_admin_super_callback(call: types.CallbackQuery, state: FSMContext):
    assert call.data is not None and call.message is not None
    is_super: str = call.data.split("_")[-1]
    data: dict = await state.get_data()
    username = None
    if is_super == "true":
        add_admin(data["user_id"], username, True)
    else:
        add_admin(data["user_id"], username, False)
    await bot.edit_message_text(
        text="Пользователь добавлен в админы",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    await state.clear()


@dp.message(F.text == "Удалить админа")
async def remove_admin_panel(message: types.Message, state: FSMContext):
    assert message.from_user is not None
    if not is_main_admin(message.from_user.id):
        return
    await message.answer("Выберите админа из списка", reply_markup=admins_to_remove())
    await state.set_state(AdminPanel.removing_admin)


@dp.callback_query(F.data.startswith("remove_"))
async def remove_admin_(call: types.CallbackQuery):
    assert call.data is not None and call.message is not None
    if not is_main_admin(call.message.chat.id):
        return
    user_id: int = int(call.data.split("_")[-1]) 
    remove_admin(user_id)
    await bot.edit_message_text( # type: ignore
        text="Пользователь удален из админов",
        chat_id=call.message.chat.id, # type: ignore
        message_id=call.message.message_id # type: ignore
    )


@dp.message(F.text == "⬅️ Назад")
async def back(message: types.Message, state: FSMContext):
    assert message.from_user is not None and message is not types.InaccessibleMessage
    if not await is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(text=HELLO_TEXT, reply_markup=main_markup(True))


@dp.message(F.text == "Список бронирований")
async def bookings_list(message: types.Message):
    assert message.from_user is not None
    if not await is_admin(message.from_user.id):
        return
    await message.answer("Выберите дату для выгрузки", reply_markup=weekdays_list_markup(callback_data="dump"))


@dp.callback_query(F.data.startswith("dump_"))
async def date_callback(call: types.CallbackQuery):
    assert call.data is not None and call.message is not None and call.message is not types.InaccessibleMessage
    date: str = call.data.split("_")[1]
    await dump_to_excel(date)
    await call.message.answer_document(FSInputFile(f"./bookings_dumps/{date}.xlsx")) # type: ignore
    await call.message.delete() # type: ignore


@dp.message(F.text == "Бронирование")
async def book(message: types.Message, state: FSMContext):
    await state.set_state(BookingPlace.choosing_day)
    await message.answer(DAY_TEXT, reply_markup=day_markup())


@dp.callback_query(F.data.startswith("day_"))
async def day_callback(call: types.CallbackQuery, state: FSMContext):
    assert call.data is not None and call.message is not None
    date: str = call.data.split("_")[1]
    day, month, year = date.split(".")
    if int(day) < 10:
        day = f"0{day}"
    if int(month) < 10:
        month = f"0{month}"
    date: str = f"{day}.{month}.{year}"
    await state.set_data({"day": date})
    await state.set_state(BookingPlace.choosing_start_time)
    await bot.edit_message_text(
        text=TIME_START_TEXT,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=time_start_markup(date),
    )


@dp.callback_query(F.data.startswith("time_start_"))
async def time_finish_callback(call: types.CallbackQuery, state: FSMContext):
    assert call.data is not None and call.message is not None
    time_start: str = call.data.split("_")[-1]
    if int(time_start) < 10:
        time_start = f"0{time_start}"
    await state.update_data({"start_time": time_start})
    await state.set_state(BookingPlace.choosing_finish_time)
    await bot.edit_message_text(
        text=TIME_FINISH_TEXT,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=time_finish_markup(int(time_start), (await state.get_data())["day"]),
    )


@dp.callback_query(F.data.startswith("time_finish_"))
async def place_callback(call: types.CallbackQuery, state: FSMContext):
    assert call.data is not None and call.message is not None
    finish_time: str = call.data.split("_")[-1]
    if int(finish_time) < 10:
        finish_time = f"0{finish_time}"
    await state.update_data({"finish_time": finish_time})
    await state.set_state(BookingPlace.choosing_place)
    data = await state.get_data()
    date_start = f"{data['day']} {data['start_time']}:00"
    date_finish = f"{data['day']} {data['finish_time']}:00"
    await bot.edit_message_text(
        text=PLACE_TEXT,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=place_markup(date_start, date_finish),
    )


@dp.callback_query(F.data.startswith("place_"))
async def finish_booking(call: types.CallbackQuery, state: FSMContext):
    assert call.data is not None and call.message is not None
    data_: list[str] = call.data.split("_")[1:]
    await state.update_data({
        "place_id": int(data_[0]),
        "hall": data_[1],
        "user_id": call.from_user.id,
        })
    data: dict = await state.get_data()
    book_place(data)
    # await bot.send_message(
    #     CHAT_ID, 
    #     f"Компьютер №{data['place_id']} забронирован на время "
    #     f"{data['day']} {data['start_time']}:00 - {data['day']} "
    #     f"{data['finish_time']}:00"
    #     )
    await bot.edit_message_text(
        text=f"Вы забронировали компьютер №{data['place_id']} в зале "
            f"<b>{data['hall']}</b> на время: <b>{data['day']} "
            f"{data['start_time']}:00 - {data['day']} "
            f"{data['finish_time']}:00</b>",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
        )
    await state.clear()


@dp.callback_query(F.data == "back")
async def back_callback(call: types.CallbackQuery, state: FSMContext):
    assert call.data is not None and call.message is not None
    state_ = await state.get_state()
    data: dict = await state.get_data()
    if state_ == BookingPlace.choosing_day:
        await state.clear()
    elif state_ == BookingPlace.choosing_start_time:
        await state.set_state(BookingPlace.choosing_day)
        await state.set_data({})
        await state.set_state(BookingPlace.choosing_day)
        await call.message.edit_text(DAY_TEXT, reply_markup=day_markup())  # type: ignore
    elif state_ == BookingPlace.choosing_finish_time:
        await state.set_state(BookingPlace.choosing_start_time)
        await state.set_data({"day": data["day"], "start_time": data["start_time"]})
        await bot.edit_message_text(
            text=TIME_START_TEXT,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=time_start_markup(data["day"]),
        )
    elif state_ == BookingPlace.choosing_place:
        await state.set_state(BookingPlace.choosing_finish_time)
        await state.set_data(
            {
                "day": data["day"],
                "start_time": data["start_time"],
                "finish_time": data["finish_time"],
            }
        )
        await bot.edit_message_text(
            text=TIME_FINISH_TEXT,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=time_finish_markup(data["start_time"], data["day"]),
        )
    elif state_ == AdminPanel.changing_worktime:
        await state.clear()


@dp.callback_query(F.data == "clear")
async def clear_callback(call: types.CallbackQuery, state: FSMContext):
    assert call.message is not None
    await state.clear()
    await bot.edit_message_text(
        text=HELLO_TEXT,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

@dp.message(Command("get_id"))
async def get_id(message: types.Message):
    assert message is not None
    await message.answer(f"Ваш id - <code>{message.from_user.id}</code>") # type: ignore


async def main():
    await dp.start_polling(bot)
