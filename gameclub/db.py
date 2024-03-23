import math
from datetime import datetime, timedelta
import peewee
import pandas as pd
from .bot import bot
from typing import Union


db = peewee.MySQLDatabase(
    database="gamebot",
    user="gamebot",
    password="gamebot",
    host="mysql",
    port=3306,
)
# connection to sqlite3
# db = peewee.SqliteDatabase("gamebot.db")

class BaseModel(peewee.Model):
    class Meta:
        database = db


class Place(BaseModel):
    hall = peewee.TextField()
    device_type = peewee.TextField()


class Schedule(BaseModel):
    booked_at = peewee.DateTimeField()
    booked_until = peewee.DateTimeField()
    place = peewee.ForeignKeyField(Place, backref="schedule")
    booked_by = peewee.TextField()


class Admin(BaseModel):
    user_id = peewee.TextField()
    is_super_admin = peewee.BooleanField(default=False)
    username = peewee.TextField(null=True)


class WorkTime(BaseModel):
    weekday = peewee.TextField()
    weekend = peewee.TextField()
    date = peewee.DateField(null=True)


def get_worktime(day: datetime):
    worktime = WorkTime.select().where(WorkTime.date == day.date())
    if not worktime.exists():
        worktime =  WorkTime.select().where(WorkTime.date == None)
    if day.weekday() < 5:
        return map(lambda x: int(x.split(":")[0]), worktime.get().weekday.split())
    return map(lambda x: int(x.split(":")[0]), worktime.get().weekend.split())


def update_worktime(time_start: str, time_finish: str, date: str, is_weekday: Union[bool, None] = None):
    worktime_ = WorkTime.select().where(WorkTime.date == None)
    if worktime_.exists() and date == "forever":
        worktime = worktime_.get()
        worktime.update(
            weekday=f"{time_start} {time_finish}" if is_weekday else f"{worktime.weekday.split()[0]} {worktime.weekday.split()[1]}",
            weekend=f"{time_start} {time_finish}" if not is_weekday else f"{worktime.weekend.split()[0]} {worktime.weekend.split()[1]}",
        ).execute()
        return 
    worktime_ = WorkTime.select().where(WorkTime.date == date)
    if not worktime_.exists():
        worktime = WorkTime.select().where(WorkTime.date == None).get()
        WorkTime.insert(
            date=date,
            weekday=f"{time_start} {time_finish}",
            weekend=f"{time_start} {time_finish}",
        ).execute()
    else:
        worktime = worktime_.get()
        worktime.update(
            weekday=f"{time_start} {time_finish}" if is_weekday else f"{worktime.weekday.split()[0]} {worktime.weekday.split()[1]}",
            weekend=f"{time_start} {time_finish}" if not is_weekday else f"{worktime.weekend.split()[0]} {worktime.weekend.split()[1]}",
        ).execute()


def get_free_time_slots(day: datetime):
    free_time_slots = {}
    place_count = Place.select().count()
    hour = math.ceil(day.hour + day.minute / 60)
    left_hour, right_hour = get_worktime(day)
    if left_hour > right_hour:
        for hour_ in range(hour, right_hour + 1):
            free_time_slots[hour_] = []
            for place in range(1, place_count + 1):
                free_time_slots[hour_].append(place)
        for hour_ in range(max(hour, left_hour), 25):
            free_time_slots[hour_] = []
            for place in range(1, place_count + 1):
                free_time_slots[hour_].append(place)
    else:
        for hour_ in range(left_hour, right_hour):
            free_time_slots[hour_] = []
            for place in range(1, place_count + 1):
                free_time_slots[hour_].append(place)

    left_range = datetime(year=day.year, month=day.month, day=day.day, hour=hour)  # microseconds
    if left_hour > right_hour:
        right_range = datetime(
            year=day.year, month=day.month, day=day.day, hour=right_hour
        ) # microseconds
    else:
        right_range = datetime(
                year=day.year, month=day.month, day=(day + timedelta(days=1)).day, hour=right_hour
        )  # microseconds
    for timeslot in Schedule.select().where(
        ((Schedule.booked_at <= right_range) & (Schedule.booked_until >= left_range))
        | ((Schedule.booked_at <= right_range) & (Schedule.booked_until >= left_range))
        | (Schedule.booked_at >= right_range)
    ):
        duration = (timeslot.booked_until - timeslot.booked_at).hour
        timeslot_hour = timeslot.booked_at.hour
        for hour in range(timeslot_hour, timeslot_hour + duration):
            if hour in free_time_slots:
                free_time_slots[hour].remove(timeslot.place.id)
    return free_time_slots


def find_free_places(date_time_start: datetime, date_time_finish: datetime):
    free_places = [i for i in Place.select()]
    left_range = date_time_start
    right_range = date_time_finish
    for timeslot in Schedule.select().where(
        ((Schedule.booked_at <= right_range) & (Schedule.booked_until >= left_range))
        | ((Schedule.booked_at <= right_range) & (Schedule.booked_until >= left_range))
        | (Schedule.booked_at >= right_range)
    ):
        for i in range(len(free_places)):
            if timeslot.place.id == free_places[i].id:
                del free_places[i]
                break
    return free_places


def get_user_bookings(user_id: int) -> list[str]:
    bookings = []
    for record in Schedule.select().where(Schedule.booked_by == user_id):
        start = record.booked_at.strftime("%d.%m.%Y %H:%M")
        finish = record.booked_until.strftime("%d.%m.%Y %H:%M")
        place = record.place.id
        if record.booked_until < datetime.now():
            Schedule.delete().where(Schedule.id == record.id).execute()
            continue
        bookings.append(f"{start} - {finish} {place} {record.id}")

    return bookings


def cancel_booking(booking_id: int):
    booking_exists = Schedule.select().where(
        Schedule.id == booking_id
    ).exists()
    if booking_exists:
        Schedule.delete().where(
            Schedule.id == booking_id
        ).execute()


def book_place(data: dict):
    date_time_start = datetime.strptime(
        f"{data['day']} {data['start_time']}:00", "%d.%m.%Y %H:%M"
    )
    if " 24:00" in f"{data['day']} {data['finish_time']}:00":
        date_time_finish = datetime.strptime(
            f"{data['day']} 00:00:00", "%d.%m.%Y %H:%M:%S"
        ) + timedelta(days=1)
    else:
        date_time_finish = datetime.strptime(
            f"{data['day']} {data['finish_time']}:00", "%d.%m.%Y %H:%M"
        )
    Schedule.insert(
        booked_at=date_time_start,
        booked_until=date_time_finish,
        place=data['place_id'],
        booked_by=data["user_id"],
    ).execute()


def add_admin(user_id: int, username: str | None, is_main_admin: bool):
    if Admin.select().where(Admin.user_id == user_id).exists():
        return
    if is_main_admin:
        Admin.insert(user_id=user_id, username=username, is_super_admin=True).execute()
    else:
        Admin.insert(user_id=user_id, username=username).execute()


def remove_admin(user_id: int):
    Admin.delete().where(Admin.user_id == user_id).execute()
    

async def is_admin(user_id: int):
    admin = Admin.select().where(Admin.user_id == user_id)
    if admin.exists() and admin.get().username is None:
        await update_admin(admin, user_id)

    return admin.exists()


async def update_admin(admin: Admin, user_id: int):
    admin.get().update(username=(await bot.get_chat(user_id)).username)

def is_main_admin(user_id: int):
    return Admin.select().where((Admin.user_id == user_id) & (Admin.is_super_admin == True)).exists()


def get_admins() -> list[tuple[int, str]]:
    admins = []
    for admin in Admin.select():
        if admin.username:
            admins.append((admin.user_id, admin.username))
        else:
            admins.append((admin.user_id, admin.user_id))
    return admins


def get_username_by_id(user_id: int):
    return Admin.get(Admin.user_id == user_id).username


async def dump_to_excel(date_: str):
    date = datetime.strptime(date_, "%d.%m.%Y")
    # Get all places
    places = Place.select()

    # Create a DataFrame with time slots as rows and places as columns
    day = date.date()
    # Add rows for each hour from 00:00 to 24:00 inclusive
    df = pd.DataFrame(index=pd.date_range(day, periods=24, freq="h"))
    df.index = df.index.strftime("%H:%M")  # type: ignore

    # Add columns for each place
    for place in places:
        column_name = f"{place.id}/{place.hall}"
        df[column_name] = ""
    df.loc["24:00"] = ""

    # Save the DataFrame to an Excel file with the date in the filename

    # Filter Schedule records for the given date
    left_range = datetime(year=date.year, month=date.month, day=date.day)
    right_range = datetime(year=date.year, month=date.month, day=date.day + 1)
    schedule_records = Schedule.select().where(
        (Schedule.booked_at >= left_range) &
        (Schedule.booked_at < right_range)
    )

    # Fill the intersection with user_id if the place is booked if not then save it empty
    for record in schedule_records:
        start = record.booked_at.strftime("%H:%M")
        finish = record.booked_until.strftime("%H:%M")
        column_name = f"{record.place.id}/{record.place.hall}"
        try:
            booker = f"@{(await bot.get_chat(record.booked_by)).username}"
        except:
            booker = record.booked_by
        if finish == "00:00":
            df.loc[start: "24:00", column_name] = booker


    # Save the DataFrame to an Excel file
    filename = f"bookings_dumps/{day.strftime("%d.%m.%Y")}.xlsx"
    df.to_excel(filename, index_label="Time")


db.create_tables([Schedule,
                  Place,
                  Admin,
                  WorkTime
])
for i in range(5):
    Place.create(
        hall="W",
        place_type="PC"
    )
for i in range(5):
    Place.create(
        hall="Q",
        place_type="PC"
    )
Place.create(hall="Зал", place_type="PS4")
for i in range(2):
    Place.create(hall="Зал", place_type="VR")
Admin.create(
    user_id="418366711",
    username="@andiazdi",
    is_super_admin=True
)
Admin.create(
    user_id="7154123064",
    username="@Innogame_admin",
    is_super_admin=True
)

Admin.create(
    user_id="309797223",
    username="@freeman_5k",
    is_super_admin=False
)
Admin.create(
    user_id="5325261723",
    username="@YWdvbnk",
    is_super_admin=False
)
Admin.create(
    user_id="1093614043",
    username="@mfzuker",
    is_super_admin=False
)

WorkTime.create(
    weekday="18:00 06:00",
    weekend="12:00 06:00"
)