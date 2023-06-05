import os
import atexit
import json
import requests
from collections import Counter
import uuid

from flask import Flask, jsonify
import redis


app = Flask("coord-service")
gateway_url = os.environ['GATEWAY_URL']

db: redis.Redis = redis.Redis(host=os.environ['REDIS_HOST'],
                              port=int(os.environ['REDIS_PORT']),
                              password=os.environ['REDIS_PASSWORD'],
                              db=int(os.environ['REDIS_DB']))

def close_db_connection():
    db.close()
atexit.register(close_db_connection)

@app.post('/start_tx')
def start_transaction():
    conn = {
        "conn_id": str(uuid.uuid4()),
        "pending_items": [],
        "pending_payments": [],
        "status": "Pending",
    }

    db.set(conn["conn_id"], json.dumps(conn))

    return jsonify(conn), 200

@app.get('/find/<conn_id>')
def get_transaction_status(conn_id):
    if db.exists(conn_id):
        conn_found = json.loads(db.get(conn_id))
        return jsonify(conn_found), 200
    else:
        return jsonify({'error': 'Invalid connection ID'}), 400
    
@app.post('/addItem/<conn_id>/<item_id>/<count>')
def add_items(conn_id, item_id, count):
    conn_found = json.loads(db.get(conn_id))
    conn_found["pending_items"].append((item_id, count))

    db.set(conn_found["conn_id"], json.dumps(conn_found))
    return jsonify(conn_found), 200

@app.post('/addPayment/<conn_id>/<user_id>/<amount>')
def add_payment(conn_id, user_id, amount):
    conn_found = json.loads(db.get(conn_id))
    conn_found["pending_payments"].append((user_id, amount))

    db.set(conn_found["conn_id"], json.dumps(conn_found))
    return jsonify(conn_found), 200

@app.post('/commit_tx/<conn_id>')
def commit_transaction(conn_id):
    conn_found = json.loads(db.get(conn_id))
    if conn_found["pending_payments"] != [] and conn_found["pending_items"] != []:
        conn_found["status"] = "Completed"
        return jsonify(conn_found), 200
    else:
        return jsonify(conn_found), 400


@app.post('/cancel_tx/<conn_id>')
def cancel_transaction(conn_id):
    conn_found = json.loads(db.get(conn_id))

    # Add back stock level
    if conn_found["pending_items"] != []:
        for item_id, amount in conn_found["pending_items"]:
            response = requests.post(f"{gateway_url}/stock/add/{item_id}/{amount}")

            if response.status_code != 200:
                return "pending item failed", response.status_code
    
    if conn_found["pending_payments"] != []:
        for user_id, amount in conn_found["pending_payments"]:
            response = requests.post(f"{gateway_url}/payment/add_funds/{user_id}/{amount}")
        
            if response.status_code != 200:
                return "pending payment failed", response.status_code
    
    conn_found["status"] = "Cancelled"
    db.set(conn_found["conn_id"], json.dumps(conn_found))

    return jsonify(conn_found), 200

