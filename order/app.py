import os
import atexit
import json
import requests
from uuid import uuid4
from collections import Counter

from flask import Flask, abort, jsonify
import redis


# gateway_url = os.environ['GATEWAY_URL']
stock_service = os.environ['STOCK_SERVICE_URL']
payment_service = os.environ['USER_SERVICE_URL']

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

    # update total cost
    item_price = int(requests.get(f"{stock_service}/find/{item_id}").json()["price"])
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
        item_price = int(requests.get(f"{stock_service}/find/{item_id}").json()["price"])
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


# @app.post('/checkout/<order_id>')
# def checkout(order_id):
#     # Check if the order exists
#     if not db.exists(order_id):
#         abort(404, description=f"Order with id {order_id} not found")
    
#     # Retrieve the order from the database
#     order_found = json.loads(db.get(order_id))

#     if order_found["paid"]:
#         abort(400, description="Order has already been paid")
#     # Transform list of items into a dictionary
#     items_count = Counter(order_found["items"])
#     # Query the stock service to check if the items are available
#     for item_id, count in items_count.items():
#         response = requests.get(f"{gateway_url}/stock/find/{item_id}")
#         if response.json()["stock"] < count:
#             abort(400, description=f"Not enough stock for item {item_id}")

#     # Query payment service to check if the user has enough balance
#     # total_cost = int(order_found["total_cost"])
#     if 'total_cost' not in order_found:
#         abort(400, description="Total cost not found")
#     response= requests.post(f"{gateway_url}/payment/pay/{order_found['user_id']}/{order_id}/{int(order_found['total_cost'])}")
#     if response.status_code >= 500:
#         abort(response.status_code, description=f"Payment service error with url {response.url}, order: {order_found}")
#     elif response.status_code >= 400:
#         abort(response.status_code, description=f"Not enough balance, order: {order_found}")
#     else:
#         print("Payment successful")

#     # Update the stock information and order information    
#     for item_id, count in items_count.items():
#         with requests.post(f"{gateway_url}/stock/subtract/{item_id}/{count}") as response:
#             if response.status_code != 200:
#                 abort(response.status_code, description="Stock update failed")

#     order_found["paid"] = True
#     # order_found["total_cost"] = total_cost
#     db.set(order_id, json.dumps(order_found))

#     return {"status": "success"}, 200


@app.post('/checkout/<order_id>')
def checkout(order_id:str):
    # Check if the order exists
    if not db.exists(order_id):
        abort(404, description=f"Order with id {order_id} not found")

    # Retrieve the order from the database
    order_found = json.loads(db.get(order_id))

    if order_found["paid"]:
        abort(400, description="Order has already been paid")

    # Transform list of items into a dictionary
    items_count = Counter(order_found["items"])

    # Call the coordinator service to start a new transaction
    response = requests.post(f"{gateway_url}/start_tx")
    if response.status_code != 200:
        abort(response.status_code, description="Failed to start the transaction")

    transaction_data = response.json()
    conn_id = transaction_data['conn_id']

    try:
        # Call the coordinator service to prepare the transaction
        response = requests.post(f"{gateway_url}/prepare/{conn_id}")
        if response.status_code != 200:
            abort(response.status_code, description="Failed to prepare the transaction")
        # Query the stock service to check if the items are available
        for item_id, count in items_count.items():
            response = requests.get(f"{gateway_url}/stock/find/{item_id}")
            if response.status_code != 200:
                abort(response.status_code, description=f"Failed to check stock for item {item_id}")
            stock_data = response.json()
            if stock_data["stock"] < count:
                abort(400, description=f"Not enough stock for item {item_id}")
        # Call the coordinator service to acknowledge the transaction
        response = requests.post(f"{gateway_url}/acknowledge/{conn_id}")
        if response.status_code != 200:
            abort(response.status_code, description="Failed to acknowledge the transaction")
        # Query the payment service to process the payment
        response = requests.post(f"{gateway_url}/payment/pay/{order_found['user_id']}/{order_id}/{int(order_found['total_cost'])}")
        if response.status_code != 200:
            abort(response.status_code, description="Payment failed")
        # Call the coordinator service to commit the transaction
        response = requests.post(f"{gateway_url}/commit_tx/{conn_id}")
        if response.status_code != 200:
            abort(response.status_code, description="Failed to commit the transaction")
        # Update the stock information and order information
        for item_id, count in items_count.items():
            response = requests.post(f"{gateway_url}/stock/subtract/{item_id}/{count}")
            if response.status_code != 200:
                abort(response.status_code, description="Stock update failed")
        # Mark the order as paid
        order_found["paid"] = True
        db.set(order_id, json.dumps(order_found))
        return {"status": "success"}, 200
    except:
        # If any error occurs, cancel the transaction
        response = requests.post(f"{gateway_url}/cancel_tx/{conn_id}")
        if response.status_code != 200:
            abort(response.status_code, description="Failed to cancel the transaction")

        abort(500, description="Transaction aborted")

