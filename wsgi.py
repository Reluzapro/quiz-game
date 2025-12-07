#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI entry point for deployment
"""
import sys
import os

# Add your project directory to the sys.path
project_home = os.path.dirname(__file__)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import the Flask app
from app import app as application

if __name__ == "__main__":
    application.run()
