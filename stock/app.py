import os
import atexit

from flask import Flask abort
import redis


app = Flask("stock-service")

db: redis.Redis = redis.Redis(host=os.environ['REDIS_HOST'],
                              port=int(os.environ['REDIS_PORT']),
                              password=os.environ['REDIS_PASSWORD'],
                              db=int(os.environ['REDIS_DB']))


def close_db_connection():
    db.close()


atexit.register(close_db_connection)


@app.post('/item/create/<price>')
def create_item(price: int):
    item = {
    "item_id": db.incr("item_id"),
    "price": price,
    "stock": 0
    }

    db.set(item["item_id"], json.dumps(item))
    return {
        "CODE": 200,
        "item_id": item["item_id"],
    }

@app.get('/find/<item_id>')
def find_item(item_id: str):
    # check if the item exists
    if not db.exists(item_id):
        abort(404, description=f"Item with id {item_id} not found")    
    # retrieve the item from the database
    item_found = json.loads(db.get(item_id))
    # return the item information using dictionary unpacking
    return {"CODE": 200, **item_found}
    


@app.post('/add/<item_id>/<amount>')
def add_stock(item_id: str, amount: int):
    # check if the item exists
    if not db.exists(item_id):
        abort(404, description=f"Item with id {item_id} not found")
    item_found = json.loads(db.get(item_id))
    item_found["stock"] += amount
    db.set(item_id, json.dumps(item_found))
    return {"CODE": 200}



@app.post('/subtract/<item_id>/<amount>')
def remove_stock(item_id: str, amount: int):
    # check if the item exists
    if not db.exists(item_id):
        abort(404, description=f"Item with id {item_id} not found")
    item_found = json.loads(db.get(item_id))
    if item_found["stock"] < amount:
        abort(404, description=f"Not enough stock for item with id {item_id}")
    else:
        item_found["stock"] -= amount
        db.set(item_id, json.dumps(item_found))
        return {"CODE": 200}

