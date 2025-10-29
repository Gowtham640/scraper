#!/usr/bin/env python3
"""
SDash Backend - Flask API Server
Main entry point for the SDash backend
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import threading
import requests
from apscheduler.schedulers.background import BackgroundScheduler

# Add python-scraper directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python-scraper'))

# Import API wrapper functions
from api_wrapper import (
    api_get_all_data,
    api_validate_credentials,
    api_get_calendar_data,
    api_get_timetable_data,
    api_get_attendance_data,
    api_get_marks_data,
    api_get_static_data,
    api_get_dynamic_data
)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure Flask app for better performance
app.config['TIMEOUT'] = 90  # 90 seconds timeout (workaround for free tier limits)

# Global lock for scraping operations to prevent concurrent scrapes
scrape_lock = threading.Lock()


def keep_warm():
    """Ping service to prevent spin-down on Render free tier"""
    try:
        url = os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:5000')
        requests.get(f"{url}/health", timeout=5)
        print('[KEEP-WARM] Service pinged successfully', file=sys.stderr)
    except Exception as e:
        print(f'[KEEP-WARM] Failed to ping: {e}', file=sys.stderr)


# Start keep-warm scheduler only on Render
if os.getenv('RENDER'):
    scheduler = BackgroundScheduler()
    scheduler.add_job(keep_warm, 'interval', minutes=14)
    scheduler.start()
    print('[KEEP-WARM] Scheduler started - pinging every 14 minutes', file=sys.stderr)
else:
    print('[KEEP-WARM] Not on Render, scheduler disabled', file=sys.stderr)


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
        
        # Use lock to ensure only ONE scrape operation at a time
        # This prevents concurrent scrapes from crashing the server
        with scrape_lock:
            print(f"[QUEUE] Processing {action} for {email}", file=sys.stderr)
            
            # Handle different actions
            result = handle_action(action, email, password, force_refresh)
            
            print(f"[QUEUE] Completed {action} for {email}", file=sys.stderr)
            return jsonify(result)
    
    except Exception as e:
        print(f"[ERROR] Flask route error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500


def handle_action(action, email, password, force_refresh):
    """Handle scraping action with proper queuing"""
    if action == 'validate_credentials':
        if not email or not password:
            return {
                "success": False,
                "error": "Email and password required"
            }
        return api_validate_credentials(email, password)
    
    elif action == 'get_all_data':
        if not email:
            return {
                "success": False,
                "error": "Email required"
            }
        return api_get_all_data(email, password, force_refresh)
    
    elif action == 'get_static_data':
        if not email:
            return {
                "success": False,
                "error": "Email required"
            }
        return api_get_static_data(email, password, force_refresh)
    
    elif action == 'get_dynamic_data':
        if not email:
            return {
                "success": False,
                "error": "Email required"
            }
        return api_get_dynamic_data(email, password)
    
    elif action == 'get_calendar_data':
        if not email or not password:
            return {
                "success": False,
                "error": "Email and password required"
            }
        return api_get_calendar_data(email, password, force_refresh)
    
    elif action == 'get_timetable_data':
        if not email or not password:
            return {
                "success": False,
                "error": "Email and password required"
            }
        return api_get_timetable_data(email, password)
    
    elif action == 'get_attendance_data':
        if not email or not password:
            return {
                "success": False,
                "error": "Email and password required"
            }
        return api_get_attendance_data(email, password)
    
    elif action == 'get_marks_data':
        if not email or not password:
            return {
                "success": False,
                "error": "Email and password required"
            }
        return api_get_marks_data(email, password)
    
    else:
        return {
            "success": False,
            "error": f"Unknown action: {action}",
            "available_actions": [
                "validate_credentials",
                "get_all_data",
                "get_static_data",
                "get_dynamic_data",
                "get_calendar_data",
                "get_timetable_data",
                "get_attendance_data",
                "get_marks_data"
            ]
        }


if __name__ == '__main__':
    print("=" * 50, file=sys.stderr)
    print("SDash Backend API Server Starting...", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)

