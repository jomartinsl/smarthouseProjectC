from datetime import datetime
from random import random
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from smarthouse.persistence import SmartHouseRepository
from pathlib import Path

def setup_database():
    project_dir = Path(__file__).parent.parent
    db_file = project_dir / "data" / "db.sql" # you have to adjust this if you have changed the file name of the database
    print(db_file.absolute())
    return SmartHouseRepository(str(db_file.absolute()))

app = FastAPI()

repo = setup_database()

smarthouse = repo.load_smarthouse_deep()

# http://localhost:8000/welcome/index.html
app.mount("/static", StaticFiles(directory="www"), name="static")


# http://localhost:8000/ -> welcome page
@app.get("/")
def root():
    return RedirectResponse("/static/index.html")


# Health Check / Hello World
@app.get("/hello")
def hello(name: str = "world"):
    return {"hello": name}


# Starting point ...

@app.get("/smarthouse")
def get_smarthouse_info() -> dict[str, int | float]:
    """
    This endpoint returns an object that provides information
    about the general structure of the smarthouse.
    """
    return {
        "no_rooms": len(smarthouse.get_rooms()),
        "no_floors": len(smarthouse.get_floors()),
        "registered_devices": len(smarthouse.get_devices()),
        "area": smarthouse.get_area()
    }

# TODO: implement the remaining HTTP endpoints as requested in
# https://github.com/selabhvl/ing301-projectpartC-startcode?tab=readme-ov-file#oppgavebeskrivelse
# here ...


@app.get("/smarthouse/floor")
def get_floors() -> dict[str, int | float | str]:
    info = {}
    floors = smarthouse.get_floors()  # Antar denne metoden returnerer en liste med etasjer
    for i, floor in enumerate(floors):
        key = f"floor_no {i+1}, no of rooms "
        info[key] = len(floor.rooms)

    return info


@app.get("/smarthouse/floor/{fid}")
def get_floor(fid: int) -> dict[str, int | float | str]:
    floor = smarthouse.get_floors()[fid-1]
    return {
        "floor_no": fid,
        "no_rooms": len(floor.rooms),
    }


@app.get("/smarthouse/floor/{fid}/room")
def get_rooms(fid: int) -> dict[str, int | float | str]:
    floor = smarthouse.get_floors()[fid-1]
    rooms = floor.rooms
    info = {}
    for i, room in enumerate(rooms):
        key = f"room_no {i+1}, room name {room.room_name}, area "
        info[key] = room.room_size
    return info


@app.get("/smarthouse/floor/{fid}/room/{rid}")
def get_room(fid: int, rid: int) -> dict[str, int | float | str]:
    floor = smarthouse.get_floors()[fid-1]
    room = floor.rooms[rid-1]
    return {
        "room_name": room.room_name,
        "room_no": rid,
        "area": room.room_size,
    }


@app.get("/smarthouse/device")
def get_devices():
    info = []
    for i in range(len(smarthouse.get_devices())):
        info.append({"device": i+1, "room": smarthouse.get_devices()[i].room.room_name})

    return info

@app.get("/smarthouse/device/{uuid}")
def get_device(uuid: str):
    for i in range(len(smarthouse.get_devices())):
        if smarthouse.get_devices()[i].id == uuid:
            return {"device": i+1, "room": smarthouse.get_devices()[i].room.room_name}

    return {"error": "device not found"}


@app.get("/smarthouse/sensor/{uuid}/current")
def get_sensor(uuid: str):
    for i in range(len(smarthouse.get_devices())):
        if smarthouse.get_devices()[i].id == uuid:
            return {"device": i+1, "room": smarthouse.get_devices()[i].room.room_name, "temperature": repo.get_latest_reading(smarthouse.get_devices()[i])}
        
    return {"error": "device not found"}


@app.post("/smarthouse/sensor/{uuid}/current")
def post_sensor(uuid: str):
    for i in range(len(smarthouse.get_devices())):
        if smarthouse.get_devices()[i].id == uuid:
            c = repo.conn.cursor()
            c.execute(f"INSERT INTO measurements (device, ts, value, unit) VALUES ('{uuid}', '{datetime.now().isoformat()}', {random() * 10}, '{smarthouse.get_devices()[i].unit}');")
            repo.conn.commit()
            c.close()


@app.get("/smarthouse/sensor/{uuid}/values")
def get_sensor_values(uuid: str, limit: int):

    if limit:
        c = repo.conn.cursor()
        c.execute(f"SELECT ts, value, unit FROM measurements WHERE device = '{uuid}' ORDER BY ts DESC LIMIT {limit};")
    else:
        c = repo.conn.cursor()
        c.execute(f"SELECT ts, value, unit FROM measurements WHERE device = '{uuid}';")
    result = c.fetchall()
    c.close()
    return result


@app.delete("/smarthouse/sensor/{uuid}/oldest")
def delete_sensor_values(uuid: str):
    c = repo.conn.cursor()
    c.execute(f"SELECT ts FROM measurements WHERE device = '{uuid}' ORDER BY ts ASC LIMIT 1;")
    ts_for_oldest_measurement = c.fetchone()[0]
    c.execute(f"DELETE FROM measurements WHERE device = '{uuid}' AND ts = '{ts_for_oldest_measurement}';")
    repo.conn.commit()
    c.close()


@app.get("/smarthouse/actuator/{uuid}/current")
def get_actuator(uuid: str):
    for i in range(len(smarthouse.get_devices())):
        if smarthouse.get_devices()[i].id == uuid:
            c = repo.conn.cursor()
            c.execute(f"SELECT state FROM actuator_state WHERE device_id = '{uuid}';")
            state = c.fetchone()
            c.close()
            return {"device": i+1, "room": smarthouse.get_devices()[i].room.room_name, "state": state}

    return {"error": "device not found"}


@app.put("/smarthouse/device/{uuid}")
def put_device(uuid: str):
    for i in range(len(smarthouse.get_devices())):
        if smarthouse.get_devices()[i].id == uuid:
            repo.update_actuator_state(smarthouse.get_devices()[i])
            return {"device": i+1, "room": smarthouse.get_devices()[i].room.room_name, "state": smarthouse.get_devices()[i].state}

    return {"error": "device not found"}


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000)