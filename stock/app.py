import os
import atexit

from flask import Flask, abort, jsonify
import redis
import json
import requests


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
    


# @app.post('/add/<item_id>/<amount>')
# def add_stock(item_id: str, amount: int):
#     # check if the item exists
#     if not db.exists(item_id):
#         abort(404, description=f"Item with id {item_id} not found")
#     item_found = json.loads(db.get(item_id))
#     item_found["stock"] = int(item_found["stock"])
#     item_found["stock"] += int(amount)
#     db.set(item_id, json.dumps(item_found))
#     # return {"CODE": 200}
#     # return {"status_code":200}
#     response = app.response_class(
#         response=item_found,
#         status=200,
#         mimetype='application/json'
#     )
#     return response
#     # return '', 200

@app.post('/add/<item_id>/<amount>')
def add_stock(item_id: str, amount: int):
    # check if the item exists
    if not db.exists(item_id):
        abort(404, description=f"Item with id {item_id} not found")
    
    conn_id = requests.post('http://coord-service/start_tx').json().get('conn_id')
    
    try:
        payload = {
            'command': f'INCRBY {item_id}:stock {amount}'
        }
        response = requests.post(f'http://coord-service/exec/{conn_id}', json=payload)
        if response.status_code != 200:
            abort(response.status_code, description=response.json().get('error'))
    except Exception as e:
        requests.post(f'http://coord-service/cancel_tx/{conn_id}')
        abort(500, description=str(e))
    
    response = requests.post(f'http://coord-service/commit_tx/{conn_id}')
    if response.status_code != 200:
        abort(response.status_code, description=response.json().get('error'))
    
    return jsonify({
        "CODE": 200,
        "message": "Stock added successfully",
    })


# @app.post('/subtract/<item_id>/<amount>')
# def remove_stock(item_id: str, amount: int):
#     # check if the item exists
#     if not db.exists(item_id):
#         abort(404, description=f"Item with id {item_id} not found")
#     item_found = json.loads(db.get(item_id))
#     item_found["stock"] = int(item_found["stock"])
#     if item_found["stock"] < int(amount):
#         abort(404, description=f"Not enough stock for item with id {item_id}")
#     else:
#         item_found["stock"] -= int(amount)
#         db.set(item_id, json.dumps(item_found))
#         response = app.response_class(
#         response="",
#         status=200,
#         mimetype='application/json'
#     )
#     return response
#         # return {"CODE": 200}
#         # return {"status_code":200}
        
# @app.post('/subtract/<item_id>/<amount>')
# def remove_stock(item_id: str, amount: int):
#     # check if the item exists
#     if not db.exists(item_id):
#         abort(404, description=f"Item with id {item_id} not found")

#     conn_id = requests.post('http://coord-service/start_tx').json().get('conn_id')

#     try:
#         current_stock = db.get(f"{item_id}:stock")
#         if current_stock is None:
#             abort(404, description=f"Item with id {item_id} has no stock")
#         current_stock = int(current_stock)
#         if current_stock < amount:
#             abort(400, description=f"Not enough stock for item with id {item_id}")
        
#         payload = {
#             'command': f'DECRBY {item_id}:stock {amount}'
#         }
#         response = requests.post(f'http://coord-service/exec/{conn_id}', json=payload)
#         if response.status_code != 200:
#             abort(response.status_code, description=response.json))
@app.post('/subtract/<item_id>/<amount>')
def remove_stock(item_id: str, amount: int):
    # Check if the item exists
    if not db.exists(item_id):
        abort(404, description=f"Item with id {item_id} not found")

    # Start a transaction with the coordination service
    coord_response = requests.post('http://coord-service/start_tx')
    if coord_response.status_code != 200:
        abort(coord_response.status_code, description=coord_response.json().get('error'))
    conn_id = coord_response.json().get('conn_id')

    try:
        # Retrieve the current stock from the database
        current_stock = db.get(f"{item_id}:stock")
        if current_stock is None:
            abort(404, description=f"Item with id {item_id} has no stock")
        current_stock = int(current_stock)

        # Check if there is enough stock
        if current_stock < amount:
            abort(400, description=f"Not enough stock for item with id {item_id}")

        # Prepare the command payload for execution
        payload = {
            'command': f'DECRBY {item_id}:stock {amount}'
        }

        # Execute the command within the transaction
        exec_response = requests.post(f'http://coord-service/exec/{conn_id}', json=payload)
        if exec_response.status_code != 200:
            abort(exec_response.status_code, description=exec_response.json().get('error'))

        # Commit the transaction
        commit_response = requests.post(f'http://coord-service/commit_tx/{conn_id}')
        if commit_response.status_code != 200:
            abort(commit_response.status_code, description=commit_response.json().get('error'))

        # Return the success response
        return jsonify({
            "CODE": 200,
            "message": "Stock removed successfully",
        })
    except Exception as e:
        # Handle errors and cancel the transaction
        requests.post(f'http://coord-service/cancel_tx/{conn_id}')
        abort(500, description=str(e))
