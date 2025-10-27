#!/usr/bin/env python3
"""
SDash Backend - Flask API Server
Main entry point for the SDash backend
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# Add python-scraper directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python-scraper'))

# Import API wrapper functions
from api_wrapper import (
    api_get_all_data,
    api_validate_credentials,
    api_get_calendar_data,
    api_get_timetable_data,
    api_get_attendance_data,
    api_get_marks_data
)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@app.route('/', methods=['GET'])
def index():
    """Root endpoint - returns API information"""
    return jsonify({
        "name": "SDash Backend API",
        "version": "1.0.0",
        "description": "SRM Academia Portal Scraper API",
        "endpoints": {
            "/health": "Health check",
            "/api/scrape": "Main scraping endpoint"
        }
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "SDash Backend is running"})


@app.route('/api/scrape', methods=['POST'])
def scrape():
    """
    Main API endpoint for scraping operations
    Handles all action types: validate_credentials, get_all_data, etc.
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Extract parameters
        action = data.get('action')
        email = data.get('email')
        password = data.get('password')
        force_refresh = data.get('force_refresh', False)
        
        if not action:
            return jsonify({
                "success": False,
                "error": "Action parameter required"
            }), 400
        
        # Handle different actions
        if action == 'validate_credentials':
            if not email or not password:
                return jsonify({
                    "success": False,
                    "error": "Email and password required"
                }), 400
            
            result = api_validate_credentials(email, password)
            return jsonify(result)
        
        elif action == 'get_all_data':
            if not email:
                return jsonify({
                    "success": False,
                    "error": "Email required"
                }), 400
            
            result = api_get_all_data(email, password, force_refresh)
            return jsonify(result)
        
        elif action == 'get_calendar_data':
            if not email or not password:
                return jsonify({
                    "success": False,
                    "error": "Email and password required"
                }), 400
            
            result = api_get_calendar_data(email, password, force_refresh)
            return jsonify(result)
        
        elif action == 'get_timetable_data':
            if not email or not password:
                return jsonify({
                    "success": False,
                    "error": "Email and password required"
                }), 400
            
            result = api_get_timetable_data(email, password)
            return jsonify(result)
        
        elif action == 'get_attendance_data':
            if not email or not password:
                return jsonify({
                    "success": False,
                    "error": "Email and password required"
                }), 400
            
            result = api_get_attendance_data(email, password)
            return jsonify(result)
        
        elif action == 'get_marks_data':
            if not email or not password:
                return jsonify({
                    "success": False,
                    "error": "Email and password required"
                }), 400
            
            result = api_get_marks_data(email, password)
            return jsonify(result)
        
        else:
            return jsonify({
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": [
                    "validate_credentials",
                    "get_all_data",
                    "get_calendar_data",
                    "get_timetable_data",
                    "get_attendance_data",
                    "get_marks_data"
                ]
            }), 400
    
    except Exception as e:
        print(f"[ERROR] Flask route error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500


if __name__ == '__main__':
    print("=" * 50, file=sys.stderr)
    print("SDash Backend API Server Starting...", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)

