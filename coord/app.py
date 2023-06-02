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
        "completed": False
    }

    db.set(conn["conn_id"], json.dumps(conn))

    return jsonify(conn), 200

# def start_transaction():
#     # conn_id = str(db.incr("transaction_id"))
#     conn_id = str(uuid.uuid4())
#     db.set(conn_id, "PREPARE")
#     return jsonify({'conn_id': conn_id}), 200

@app.get('/status/<conn_id>')
def get_transaction_status(conn_id):
    if db.exists(conn_id):
        status = db.get(conn_id).decode('utf-8')
        status = db.get(conn_id)
        return jsonify({'status': status})
    else:
        return jsonify({'error': 'Invalid connection ID'}), 400
    
@app.post('/add/<conn_id>/<item_id>/<count>')
def add_items(conn_id, item_id, count):
    conn_found = json.loads(db.get(conn_id))
    conn_found["pending_items"].append((item_id, count))
    db.set(conn_found["conn_id"], json.dumps(conn_found))
    return jsonify(conn_found), 200

@app.post('/add/<conn_id>/<user_id>/<amount>')
def add_payment(conn_id, user_id, amount):
    conn_found = json.loads(db.get(conn_id))
    conn_found["pending_payments"].append((user_id, amount))
    db.set(conn_found["conn_id"], json.dumps(conn_found))
    return jsonify(conn_found), 200

# @app.post('/prepare/<conn_id>')
# def prepare_transaction(conn_id):
#     if db.exists(conn_id):
#         status = db.get(conn_id).decode('utf-8')
#         if status == "PREPARE":
#             db.set(conn_id, "READY")
#             return jsonify({'message': 'Prepare vote recorded'})
#         else:
#             return jsonify({'error': 'Invalid transaction status'}), 400
#     else:
#         return jsonify({'error': 'Invalid connection ID'}), 400

# @app.post('/acknowledge/<conn_id>')
# def acknowledge_transaction(conn_id):
#     if db.exists(conn_id):
#         status = db.get(conn_id).decode('utf-8')
#         if status == "COMMIT":
#             db.set(conn_id, "ACKNOWLEDGED")
#             return jsonify({'message': 'Acknowledgment recorded'})
#         else:
#             return jsonify({'error': 'Invalid transaction status'}), 400
#     else:
#         return jsonify({'error': 'Invalid connection ID'}), 400
    

@app.post('/commit_tx/<conn_id>')
def commit_transaction(conn_id):
    conn_found = json.loads(db.get(conn_id))
    if conn_found["pending_payments"] != [] and conn_found["pending_items"] != []:
        conn_found["completed"] = True
        return jsonify(conn_found), 200
    else:
        return jsonify(conn_found), 400

# @app.post('/commit_tx/<conn_id>')
# def commit_transaction(conn_id):
#     if db.exists(conn_id):
#         status = db.get(conn_id).decode('utf-8')
#         if status == "READY" or status == "ACKNOWLEDGED":
#             db.set(conn_id, "COMMIT")
#             # Send commit message to participating services
#             response = requests.post(f"{gateway_url}/order/commit/{conn_id}")
#             if response.status_code == 200:
#                 return jsonify({'message': 'Transaction committed successfully'})
#             else:
#                 # Handle failure or error case
#                 db.set(conn_id, "ABORT")
#                 return jsonify({'error': 'Failed to commit transaction'}), 500
#         else:
#             return jsonify({'error': 'Invalid transaction status'}), 400
#     else:
#         return jsonify({'error': 'Invalid connection ID'}), 400
        
## RETURN ALL THE HOLDINGS
@app.post('/cancel_tx/<conn_id>')
def cancel_transaction(conn_id):
    conn_found = json.loads(db.get(conn_id))

    # Add back stock level
    if conn_found["pending_items"] != []:
        for item_id, amount in conn_found["pending_items"]:
            response = requests.post(f"{gateway_url}/order/add/{item_id}/{amount}")
        
        if response.status_code != 200:
            return jsonify(conn_found), response.status_code
    
    if conn_found["pending_payments"] != []:
        for user_id, amount in conn_found["pending_payments"]:
            response = requests.post(f"{gateway_url}/payment/add_funds/{user_id}/{amount}")
        
        if response.status_code != 200:
            return jsonify(conn_found), response.status_code
    
    return jsonify(conn_found), 200
                           
# @app.post('/exec/<conn_id>')
# # @app.route('/exec/<conn_id>', methods=['POST'])
# def execute_command(conn_id):
#     if db.exists(conn_id):
#         command = requests.json.get('command')
#         db.rpush(f"{conn_id}:commands", command)
#         return jsonify({'message': 'Command executed successfully'})
#     else:
#         return jsonify({'error': 'Invalid connection ID'}), 400

# # @app.route('/commit_tx/<conn_id>', methods=['POST'])
# @app.post('/commit_tx/<conn_id>')
# def commit_transaction(conn_id):
#     if db.exists(conn_id):
#         db.rpush(f"{conn_id}:commands", "COMMIT")
#         db.delete(conn_id)
#         return jsonify({'message': 'Transaction committed successfully'})
#     else:
#         return jsonify({'error': 'Invalid connection ID'}), 400
# @app.post('/cancel_tx/<conn_id>')
# # @app.route('/cancel_tx/<conn_id>', methods=['POST'])
# def cancel_transaction(conn_id):
#     if db.exists(conn_id):
#         db.rpush(f"{conn_id}:commands", "ROLLBACK")
#         db.delete(conn_id)
#         return jsonify({'message': 'Transaction cancelled successfully'})
#     else:
#         return jsonify({'error': 'Invalid connection ID'}), 400

# @app.route('/find/<item_id>', methods=['GET'])
# def find_item(item_id):
#     if not db.exists(item_id):
#         abort(404, description=f"Item with id {item_id} not found")

#     item_found = db.get(item_id).decode('utf-8')
#     item_found = json.loads(item_found)
#     item_found["price"] = float(item_found["price"])
#     item_found["stock"] = int(item_found["stock"])

#     return jsonify({'CODE': 200, **item_found})

