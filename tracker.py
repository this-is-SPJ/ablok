
#tracker.py
"""This script is an addon for mitmproxy. Its sole job is to passively observe all web requests, extract relevant data, and log it to a persistent database for later analysis. """

import sqlite3
import time
import logging
from contextlib import closing
import types
from mitmproxy import http

DB_PATH = 'activity.db'



logging.basicConfig(level=logging.INFO, format='%(asctime)s - [tracker.py] - %(message)s')

DB_CONNECTION = None
logged_domains = set()  # Tracks domains already logged this session


def setup_database(conn):
    with closing(conn.cursor()) as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY,
                timestamp REAL NOT NULL,
                domain TEXT NOT NULL
            )
        """)
    conn.commit()


def load(loader):
    global DB_CONNECTION
    DB_CONNECTION = sqlite3.connect(DB_PATH, check_same_thread=False)
    DB_CONNECTION.execute("PRAGMA journal_mode=WAL;")  # Enable read/write concurrency
    setup_database(DB_CONNECTION)
    logging.info("Database ready.")


def request(flow: http.HTTPFlow):
    global DB_CONNECTION, logged_domains

    if not DB_CONNECTION:
        return

    domain = flow.request.host

    # Only log domain once per session
    if domain in logged_domains:
        return

    flow.request.timestamp_start = time.time()  # Save for later


def response(flow: http.HTTPFlow):
    global DB_CONNECTION, logged_domains

    if not DB_CONNECTION:
        return

    domain = flow.request.host
    if domain in logged_domains:
        return

    # Allow only successful responses
    if flow.response.status_code != 200:
        return

    timestamp = flow.request.timestamp_start

    try:
        with closing(DB_CONNECTION.cursor()) as cursor:
            cursor.execute("INSERT INTO visits (timestamp, domain) VALUES (?, ?)", (timestamp, domain))
        DB_CONNECTION.commit()
        logged_domains.add(domain)
        logging.info(f"Logged: {domain}")
    except Exception as e:
        logging.warning(f"DB write failed for {domain}: {e}")


def done():
    global DB_CONNECTION
    if DB_CONNECTION:
        DB_CONNECTION.close()
        DB_CONNECTION = None
        logging.info("Database connection closed.")


tracker_object = types.SimpleNamespace()
tracker_object.load = load
tracker_object.request = request
tracker_object.response = response
tracker_object.done = done
addons = [tracker_object]