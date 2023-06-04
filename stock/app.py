import os
import atexit

from flask import Flask, abort, request
import redis
import json
from collections import Counter

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
    item_found["price"]= float(item_found["price"])
    item_found["stock"]= int(item_found["stock"])
    # return the item information using dictionary unpacking
    return {"CODE": 200, **item_found}
    


@app.post('/add/<item_id>/<amount>')
def add_stock(item_id: str, amount: int):
    # check if the item exists
    if not db.exists(item_id):
        abort(404, description=f"Item with id {item_id} not found")


    item_found = json.loads(db.get(item_id))
    item_found["stock"] = int(item_found["stock"])
    item_found["stock"] += int(amount)
    db.set(item_id, json.dumps(item_found))
    # return {"CODE": 200}
    # return {"status_code":200}
    response = app.response_class(
        response=item_found,
        status=200,
        mimetype='application/json'
    )
    return response
    # return '', 200




@app.post('/subtract/<item_id>/<amount>')
def remove_stock(item_id: str, amount: int):
    # check if the item exists
    if not db.exists(item_id):
        abort(404, description=f"Item with id {item_id} not found")

    remove_stock_lock = db.lock(f'remove_stock_lock:{item_id}')
    if remove_stock_lock.acquire():
        try:
            item_found = json.loads(db.get(item_id))
            item_found["stock"] = int(item_found["stock"])
            if item_found["stock"] < int(amount):
                abort(404, description=f"Not enough stock for item with id {item_id}")
            else:
                item_found["stock"] -= int(amount)
                db.set(item_id, json.dumps(item_found))
                response = app.response_class(
                response="",
                status=200,
                mimetype='application/json'
            )

            return response
        except Exception as e:
            remove_stock_lock.release()
            # Handle exception here
            abort(500, description="Internal Server Error")
        finally:
            remove_stock_lock.release()
    else:
        abort(503, description="Service Unavailable: Could not acquire lock")

@app.post('/check/<order_id>')
def check_stock(order_id: str):
    # check if all thems are available
    items = dict(request.json)

    for item_id , item_num in items.items():
        if not db.exists(item_id):
            abort(404, description=f"Item with id {item_id} not found")
        item_found = json.loads(db.get(item_id))
        item_found["stock"] = int(item_found["stock"])
        if item_found["stock"] < int(item_num):
            abort(404, description=f"Not enough stock for item with id {item_id}")

    return f"All items are available for order {order_id}"

@app.post('/update/<order_id>')
def remove_all_stocks(order_id):
    items = dict(request.json)
    for item_id , item_num in items.items():
        remove_stock(item_id, item_num)
    return f"Order {order_id} is completed"


