import os
import atexit

from flask import Flask, abort, jsonify
import redis
import json
import requests
import uuid


app = Flask("stock-service")
# gateway_url = os.environ['GATEWAY_URL']
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
        "item_id": str(uuid.uuid4()),
        "price": price,
        "stock": 0
    }

    db.set(item["item_id"], json.dumps(item))
    return jsonify(item), 200

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
    return jsonify(item_found), 200
    


@app.post('/add/<item_id>/<amount>')
def add_stock(item_id: str, amount: int):

    stock_lock = db.lock("stock_lock", timeout=10)

    # check if the item exists
    if not db.exists(item_id):
        stock_lock.release()
        abort(404, description=f"Item with id {item_id} not found")
    
    item_found = json.loads(db.get(item_id))

    if stock_lock.acquire():
        try:
            item_found["stock"] = int(item_found["stock"])
            item_found["stock"] += int(amount)
            db.set(item_id, json.dumps(item_found))
        except Exception as e:
            return "Exception at add stock occured", 400
        finally:
            stock_lock.release()
   
    return jsonify(item_found), 200


@app.post('/subtract/<item_id>/<amount>')
def remove_stock(item_id: str, amount: int):
    item_found = json.loads(db.get(item_id))

    stock_lock = db.lock("stock_lock", timeout=10)

    item_found["stock"] = int(item_found["stock"])
    if item_found["stock"] < int(amount):
        stock_lock.release()
        return "Not enough stock for item", 404
    
    if stock_lock.acquire():
        try:
            item_found["stock"] -= int(amount)
            db.set(item_id, json.dumps(item_found))
        except Exception as e:
            return "Exception at remove stock occured", 400
        finally:
            stock_lock.release()
        
    return jsonify(item_found), 200
