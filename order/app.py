import os
import atexit
import json

from flask import Flask, abort
import redis


gateway_url = os.environ['GATEWAY_URL']

app = Flask("order-service")

db: redis.Redis = redis.Redis(host=os.environ['REDIS_HOST'],
                              port=int(os.environ['REDIS_PORT']),
                              password=os.environ['REDIS_PASSWORD'],
                              db=int(os.environ['REDIS_DB']))


def close_db_connection():
    db.close()


atexit.register(close_db_connection)


@app.post('/create/<user_id>')
def create_order(user_id):
    order= {
        "order_id": db.incr("order_id"),
        "user_id": user_id,
        "items": [],
        "paid": False,
        "total_cost": 0,
    }
    db.set(order["order_id"], json.dumps(order))
    return {
        "CODE": 200,
        "order_id": order["order_id"],
    }



@app.delete('/remove/<order_id>')
def remove_order(order_id):
    # check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    
    # delete the order from the database
    db.delete(order_id)
    
    return {"CODE": 200}



@app.post('/addItem/<order_id>/<item_id>')
def add_item(order_id, item_id):
    # check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")

    order_found = json.loads(db.get(order_id))
    order_found["items"].append(item_id)
    db.set(order_id, json.dumps(order_found))

    return {"CODE": 200}





@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    
    order_found = json.loads(db.get(order_id))
    if item_id not in order_found["items"]:
        abort(404, description=f"Item with id {item_id} not found in order with id {order_id}")
    else:
        order_found["items"].remove(item_id)
        db.set(order_id, json.dumps(order_found))
        return {"CODE": 200}


@app.get('/find/<order_id>')
def find_order(order_id):
    # check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    # retrieve the order from the database
    order_found = json.loads(db.get(order_id))
    
    # return the order information using dictionary unpacking
    return {"CODE": 200, **order_found}


@app.post('/checkout/<order_id>')
def checkout(order_id):
    pass
