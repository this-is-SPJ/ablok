
#rules.py
"""This is the "brain" of the application. It is stateless and has one core function: to analyze the activity log against the user's rules and decide which domains *should* be blocked right now."""

import yaml
import sqlite3
import time
import logging
from contextlib import closing


DB_PATH = 'activity.db'
CONFIG_PATH = 'config.yaml'



logging.basicConfig(level=logging.INFO, format='%(asctime)s - [rules.py] - %(message)s')

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("config.yaml not found! Exiting.")
        exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing config.yaml: {e}. Exiting.")
        exit(1)

def get_domains_to_block(config):
    domains = set(config.get('static_blocklist', []))
    
    dynamic_rule = config.get('dynamic_rule', {})
    if dynamic_rule.get('enabled', False):
        try:
            with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as cursor:
                time_limit = time.time() - (dynamic_rule.get('time_period_minutes', 60) * 60) # defaults to 60 minutes converted to seconds
                visit_count_threshold = dynamic_rule.get('visit_count', 100) #defalts to 100 visits
                
                cursor.execute("""
                    SELECT domain FROM visits 
                    WHERE timestamp > ? 
                    GROUP BY domain 
                    HAVING COUNT(id) > ?
                """, (time_limit, visit_count_threshold))
                
                dynamic_domains = {row[0] for row in cursor.fetchall()}
                if dynamic_domains:
                    logging.info(f"Dynamic rule triggered for: {', '.join(dynamic_domains)}")
                    domains.update(dynamic_domains)

        except Exception as e:
            logging.error(f"Failed to query database for dynamic rules: {e}")

    return domains