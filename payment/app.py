import os
import atexit

from flask import Flask, abort, jsonify
import redis
import json
import sys
import os
import requests

app = Flask("payment-service")
gateway_url = os.environ['GATEWAY_URL']
db: redis.Redis = redis.Redis(host=os.environ['REDIS_HOST'],
                              port=int(os.environ['REDIS_PORT']),
                              password=os.environ['REDIS_PASSWORD'],
                              db=int(os.environ['REDIS_DB']))


def close_db_connection():
    db.close()


atexit.register(close_db_connection)


@app.post('/create_user')
def create_user():
    user= {
        "user_id": db.incr("user_id"),
        "credit": 0,
    }

    db.set(user["user_id"], json.dumps(user))

    return jsonify(user), 200


@app.get('/find_user/<user_id>')
def find_user(user_id: str):
    # check if the user exists
    if not db.exists(user_id):
        abort(404, description=f"User with id {user_id} not found")

    # retrieve the user from the database
    user_found = json.loads(db.get(user_id))
    
    # return the user information using dictionary unpacking
    return jsonify(user_found), 200


@app.post('/add_funds/<user_id>/<amount>')
def add_credit(user_id: str, amount: int):
    # Check if user exists
    if not db.exists(user_id):
        # abort(404, description=f"User with id {user_id} not found")
        return jsonify({"done": False}), 404
    
    # retrieve the user from the database
    user_found = json.loads(db.get(user_id))

    # Update the user amount in the dict
    user_found["credit"] = float(user_found["credit"]) + float(amount)

    # Update the database
    db.set(user_found["user_id"], json.dumps(user_found))

    # return the user information using dictionary unpacking
    return jsonify({"done": True}), 200

### Do i need to check that this order id belongs to the user id?
@app.post('/pay/<user_id>/<order_id>/<amount>')
def remove_credit(user_id: str, order_id: str, amount: int):
    # Check if user exists
    if not db.exists(user_id):
        abort(404, description=f"User with id {user_id} not found")
    else:
        # retrieve the user from the database
        user_found = json.loads(db.get(user_id))

    # Check if order exists
    # order_response = requests.get(f"{gateway_url}/orders/find/{order_id}")

    # if order_response.status_code != 200:
    #     abort(order_response.status_code, description=f"Order {order_id} not found")

    # Check if user has sufficient amount to deduct
    if float(user_found['credit']) < float(amount):
        abort(400, description=f"User with id {user_id} does not have sufficient amount to be deducted")

    # Update the user amount in the dict
    user_found["credit"] = int(float(user_found["credit"]) - float(amount))

    # Update the database
    db.set(user_id, json.dumps(user_found))
    
    return jsonify(user_found), 200

@app.post('/cancel/<user_id>/<order_id>')
def cancel_payment(user_id: str, order_id: str):
    # Check if user and order exists
    if not db.exists(user_id):
        abort(404, description=f"User with id {user_id} not found")
    else:
        # retrieve the user from the database
        user_found = json.loads(db.get(user_id))
    
    # Check if order exists
    order_response = requests.get(f"{gateway_url}/orders/find/{order_id}")

    if order_response.status_code != 200:
        abort(order_response.status_code, description=order_response.json()['message'])
    else:
        order_found = order_response.json()
    
    # Refund money back to the user
    user_found["credit"] += order_found["total_cost"]

    data = user_found.update(order_found)

    return jsonify(data), 200

@app.post('/status/<user_id>/<order_id>')
def payment_status(user_id: str, order_id: str):
    # Check if order exists
    order_response = requests.get(f"{gateway_url}/orders/find/{order_id}")

    if order_response.status_code != 200:
        abort(order_response.status_code, description=order_response.json()['message'])
    else:
        order_found = order_response.json()
    
    if order_found["user_id"] != user_id:
        abort(404, description=f"User with id {user_id} not found")
    
    return jsonify({"paid": order_found["paid"]}), 200

    
