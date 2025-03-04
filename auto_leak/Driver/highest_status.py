import mysql.connector
from mysql.connector import Error
import logging
import time
import json
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('highest_values.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class DatabaseCommunication:
    def __init__(self):
        self.db_config = {
            "host": "localhost",
            "user": "root",
            "password": "",
            "database": "leak_app"
        }
        self.connection = None
        self.cursor = None
        self.connect_db()

    def connect_db(self):
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            self.cursor = self.connection.cursor()
            self.connection.autocommit = True
            logging.info("✅ Database connection established successfully!")
        except Error as e:
            logging.error(f"❌ Database connection failed: {e}")
            self.connection = None
            self.cursor = None

    def check_connection(self):
        if self.connection is None or self.cursor is None:
            logging.warning("❌ No database connection. Attempting to reconnect...")
            self.connect_db()

    def fetch_unprocessed_values(self, filter_no):
        try:
            self.check_connection()
            query = """
                SELECT id, part_number_id, batch_counter, filter_no, filter_values, shift_id, date 
                FROM leakapp_result_tbl
                WHERE filter_no = %s AND processed = 0
                ORDER BY date DESC 
                LIMIT 150
            """
            self.cursor.execute(query, (filter_no,))
            return self.cursor.fetchall()
        except Error as e:
            logging.error(f"❌ Error fetching unprocessed values for {filter_no}: {e}")
            return []

    def fetch_shift_id(self):
        try:
            self.check_connection()
            query = "SELECT id, start_time, end_time FROM shift_tbl"
            self.cursor.execute(query)
            shifts = self.cursor.fetchall()
            
            current_time = datetime.now().time()
            for shift_id, start_time, end_time in shifts:
                print(shift_id)
                if isinstance(start_time, timedelta):
                    start_time = (datetime.min + start_time).time()
                if isinstance(end_time, timedelta):
                    end_time = (datetime.min + end_time).time()
                
                if start_time <= current_time <= end_time:
                    return shift_id

            logging.warning("❌ No matching shift found for the current time.")
            return None
        except Error as e:
            logging.error(f"❌ Error fetching shift data: {e}")
            return None

    def fetch_master_data(self, part_number_id):
        try:
            self.check_connection()
            query = "SELECT timer1, timer2, setpoint1, setpoint2 FROM leakapp_masterdata WHERE id = %s"
            self.cursor.execute(query, (part_number_id,))
            return self.cursor.fetchone()
        except Error as e:
            logging.error(f"❌ Error fetching master data: {e}")
            return None

    def update_result_status(self, result_id):
        try:
            self.check_connection()
            query = "UPDATE leakapp_result_tbl SET processed = 1 WHERE id = %s"
            self.cursor.execute(query, (result_id,))
            logging.info(f"✅ Updated result ID {result_id} marked as processed.")
        except Error as e:
            logging.error(f"❌ Error updating result status: {e}")

    def insert_into_leakapp_test(self, part_number_id, filter_no, highest_value, status, shift_id):
        try:
            self.check_connection()
            query = """
                INSERT INTO leakapp_test (part_number_id, filter_no, highest_value, status, shift_id, date)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE highest_value = VALUES(highest_value), status = VALUES(status), shift_id = VALUES(shift_id), date = NOW();
            """
            self.cursor.execute(query, (part_number_id, filter_no, highest_value, status, shift_id))
            logging.info(f"✅ Inserted into leakapp_test: Part No {part_number_id}, Filter {filter_no}, Status: {status}, Shift: {shift_id}")
        except Error as e:
            logging.error(f"❌ Error inserting into leakapp_test: {e}")

    def process_filters(self):
        filters = [f"AI{i}" for i in range(1, 17)]

        while True:
            for filter_no in filters:
                results = self.fetch_unprocessed_values(filter_no)
                if not results:
                    logging.info(f"✅ No unprocessed results found for filter {filter_no}")
                    continue

                shift_id = self.fetch_shift_id()
                if shift_id is None:
                    logging.error("❌ Could not determine shift. Skipping processing.")
                    continue

                # Ensure shift_id exists in shift_tbl
                self.cursor.execute("SELECT COUNT(*) FROM shift_tbl WHERE id = %s", (shift_id,))
                if self.cursor.fetchone()[0] == 0:
                    logging.error(f"❌ Invalid shift_id {shift_id}: It does not exist in shift_tbl.")
                    continue


                for result in results:
                    result_id, part_number_id, batch_counter, filter_no, filter_values, shift, date = result

                    try:
                        if isinstance(filter_values, (int, float)):  # If it's a single number, convert to a list
                            filter_values = [filter_values]
                        else:
                            filter_values = json.loads(filter_values)  # Parse JSON if it's a string

                        if not isinstance(filter_values, list):  # Ensure it's a list
                            raise ValueError("filter_values should be a list")
                    except Exception as e:
                        logging.error(f"❌ Invalid filter_values format for result ID {result_id}: {e} (Value: {filter_values})")
                        continue

                    master_data = self.fetch_master_data(part_number_id)
                    if not master_data:
                        logging.warning(f"❌ No master data found for part_number_id: {part_number_id}")
                        continue

                    timer1, timer2, setpoint1, setpoint2 = master_data
                    highest_value = max(max(filter_values), setpoint1, setpoint2)
                    status = "OK" if highest_value <= setpoint1 else "NOK"

                    self.update_result_status(result_id)
                    self.insert_into_leakapp_test(part_number_id, filter_no, highest_value, status, shift_id)

            time.sleep(5)


if __name__ == "__main__":
    db = DatabaseCommunication()
    db.process_filters()
