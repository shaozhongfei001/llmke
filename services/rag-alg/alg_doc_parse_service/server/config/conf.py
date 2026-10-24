#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: conf.py  
Time: 2025/10/31 13:28  
"""
import os


API_WORKER_COUNT = int(os.getenv("API_WORKER_COUNT", 6))

API_TIME_OUT = int(os.getenv("API_TIME_OUT", 600))

