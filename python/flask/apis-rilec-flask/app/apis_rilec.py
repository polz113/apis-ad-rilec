#!/bin/env python3

from flask import Flask, request, abort, jsonify

app = Flask(__name__)

@app.route('/hr/HRMaster/replicate', methods=['POST', 'PUT'])
def rilec_post():
    try:
        assert request.headers['X-Api-Key'] == 'ToleJeSkrivnost'
    except:
        return jsonify(''), 401
    data = request.get_json()
    return jsonify(data)

@app.route('/hr/HRMaster/replicate', methods=['GET'])
def rilec_get():
    pass

@app.route('/')
def hello_world():
    return 'Hello, World!'
