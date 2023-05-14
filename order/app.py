import os
import atexit
import json
import requests
from uuid import uuid4
from collections import Counter

from flask import Flask, abort, jsonify
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
def create_order(user_id:str):
    order= {
        "order_id": str(uuid4()),
        "user_id": user_id,
        "items": [],
        "paid": False,
        "total_cost": 0,
    }
    db.set(order["order_id"], json.dumps(order))

    response = app.response_class(
            response= order,
            status=200,
            mimetype='application/json'
        )
    return jsonify(order), 200


@app.delete('/remove/<order_id>')
def remove_order(order_id:str):
    # check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    
    # delete the order from the database
    db.delete(order_id)
    
    response = app.response_class(
            response= f"{order_id} order has been deleted",
            status=200,
            mimetype='application/json'
        )
    return f"{order_id} order has been deleted", 200



@app.post('/addItem/<order_id>/<item_id>')
def add_item(order_id:str, item_id):
    # check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")

    order_found = json.loads(db.get(order_id))
    order_found["items"].append(item_id)

    # Decrease item dict stock level? TODO:


    # update total cost
    item_price = int(requests.get(f"{gateway_url}/stock/find/{item_id}").json()["price"])
    order_found["total_cost"] += item_price
    db.set(order_id, json.dumps(order_found))

    response = app.response_class(
            response=json.dumps(order_found),
            status=200,
            mimetype='application/json'
        )
    return response



@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    
    order_found = json.loads(db.get(order_id))
    if item_id not in order_found["items"]:
        abort(404, description=f"Item with id {item_id} not found in order with id {order_id}")
    else:
        order_found["items"].remove(item_id)
        # update total cost
        item_price = int(requests.get(f"{gateway_url}/stock/find/{item_id}").json()["price"])
        order_found["total_cost"] -= item_price
        db.set(order_id, json.dumps(order_found))

        response = app.response_class(
            response=json.dumps(order_found),
            status=200,
            mimetype='application/json'
        )
        return response



@app.get('/find/<order_id>')
def find_order(order_id:str):
    # check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    # retrieve the order from the database
    order_found = json.loads(db.get(order_id))
    
    # return the order information using dictionary unpacking
    response = app.response_class(
            response=json.dumps(order_found),
            status=200,
            mimetype='application/json'
        )
    return jsonify(order_found), 200


@app.post('/checkout/<order_id>')
def checkout(order_id:str):
    # Check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    
    # Retrieve the order from the database
    order_found = json.loads(db.get(order_id))

    if order_found["paid"]:
        return "Order has already been paid", 400

    items_count = Counter(order_found["items"])

    resp = requests.post(f"{gateway_url}/stock/check/{order_id}", json=items_count)

    if resp.status_code != 200:
        return "Stock check failed", 400
    
    # call payment service
    user_id, amount = str(order_found["user_id"]), int(order_found["total_cost"])
    resp = requests.post(f"{gateway_url}/payment/pay/{user_id}/{order_id}/{amount}")
    if resp.status_code != 200:
        abort(400, description="Payment failed")

    # update stocks in stock service
    resp = requests.post(f"{gateway_url}/stock/update/{order_id}", json=items_count)
    if resp.status_code != 200:
        return "Stock update failed", 400
    
    # update order status
    order_found["paid"] = True
    db.set(order_id, json.dumps(order_found))

    return f"Order {order_id} paid successfully", 200


