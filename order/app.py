import os
import atexit
import json
import requests
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
def create_order(user_id):
    order= {
        "order_id": db.incr("order_id"),
        "user_id": user_id,
        "items": [],
        "payment_status": "Pending",
        "total_cost": 0,
        "paid_amount": 0,
    }
    db.set(order["order_id"], json.dumps(order))

    response = app.response_class(
            response= order,
            status=200,
            mimetype='application/json'
        )
    return jsonify(order), 200

    # return {
    #     "CODE": 200,
    #     "order_id": order["order_id"],
    # }



@app.delete('/remove/<order_id>')
def remove_order(order_id):
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
def add_item(order_id, item_id):
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
def find_order(order_id):
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
    return response


@app.post('/checkout/<order_id>')
def checkout(order_id):
    # check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")
    
    # retrieve the order from the database
    order_found = json.loads(db.get(order_id))
    
    # transform list of items into a dictionary
    items_count = Counter(order_found["items"])
    checkout_possible = True
    # query the stock service to check if the items are available
    for item_id, count in items_count.items():
        response = requests.get(f"{gateway_url}/stock/find/{item_id}")
        if response.status_code != 200:
            abort(response.status_code, description=response.json())
        if response.json()["stock"] < count:
            checkout_possible = False
            break
    
    if not checkout_possible:
        abort(400, description="Not enough stock for some items")
    else:
        # query payment service to check if the user has enough balance
        total_cost = order_found["total_cost"]
        response = requests.post(f"{gateway_url}/payment/pay/{order_found['user_id']}/{order_id}/{total_cost}")
        if response.status_code != 200:
            # revert the stock information
            abort(response.status_code, description=response.json())
        else:
            
            # update the stock information
            for item_id, count in items_count.items():
                requests.post(f"{gateway_url}/stock/remove/{item_id}/{count}")

            # update the order information    
            order_found["paid"] = True
            order_found["total_cost"] = total_cost

            response = app.response_class(
                response=json.dumps(order_found),
                status=200,
                mimetype='application/json'
            )
            return response
            # return {"CODE": 200, "status": "Order paid successfully"}
    

