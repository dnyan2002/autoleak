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

    def fetch_filtered_values(self, filter_no, timer_duration):
        """
        Fetch values from leakapp_result_tbl within the given timer duration.
        """
        try:
            self.check_connection()
            time_threshold = datetime.now() - timedelta(seconds=timer_duration)
            
            query = """
                SELECT filter_values 
                FROM leakapp_result_tbl 
                WHERE filter_no = %s AND date >= %s
            """
            self.cursor.execute(query, (filter_no, time_threshold))
            results = self.cursor.fetchall()
            
            # Extract values
            all_values = []
            for row in results:
                try:
                    values = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    if isinstance(values, (int, float)):  
                        values = [values]  
                    if isinstance(values, list):
                        all_values.extend(values)
                except json.JSONDecodeError:
                    logging.error(f"❌ Error parsing filter values for {filter_no}: {row[0]}")

            return all_values
        except Error as e:
            logging.error(f"❌ Error fetching filtered values for {filter_no}: {e}")
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

    def insert_into_leakapp_showreport(self, filter_no, highest_value, status, shift_id, part_number_id):
        """
        Insert the highest value found into leakapp_showreport with a foreign key.
        """
        try:
            self.check_connection()
            query = """
                INSERT INTO leakapp_show_report (filter_no, highest_value, status, shift_id, part_number_id, date)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            self.cursor.execute(query, (filter_no, highest_value, status, shift_id, part_number_id))
            logging.info(f"✅ Inserted into leakapp_showreport: Filter {filter_no}, Max: {highest_value}, Status: {status}, Part No: {part_number_id}")
        except Error as e:
            logging.error(f"❌ Error inserting into leakapp_showreport: {e}")
                                                                       
    def process_filters(self):
        filters = [f"AI{i}" for i in range(1, 17)]

        while True:
            for filter_no in filters:
                shift_id = self.fetch_shift_id()
                if shift_id is None:
                    logging.error("❌ Could not determine shift. Skipping processing.")
                    continue

                # Fetch master data for timer and setpoints
                part_number_id = 10
                master_data = self.fetch_master_data(part_number_id)
                if not master_data:
                    logging.warning(f"❌ No master data found for part_number_id: {part_number_id}")
                    continue

                timer1, timer2, setpoint1, setpoint2 = master_data
                timer1 = timer1 / 1000000 if timer1 > 10000 else timer1
                timer2 = timer2 / 1000000 if timer2 > 10000 else timer2

                # Fetch values within the timer intervals
                values_timer1 = self.fetch_filtered_values(filter_no, timer1)
                values_timer2 = self.fetch_filtered_values(filter_no, timer2)

                if not values_timer1 and not values_timer2:
                    logging.info(f"✅ No values found for filter {filter_no} in last {timer2} seconds")
                    continue

                # Get highest value in timer1 & timer2 intervals
                max_value_timer1 = max(values_timer1) if values_timer1 else 0
                max_value_timer2 = max(values_timer2) if values_timer2 else 0

                status_timer1 = "OK" if max_value_timer1 <= setpoint1 else "NOK"
                status_timer2 = "OK" if max_value_timer2 <= setpoint2 else "NOK"
                
                query = "SELECT id FROM leakapp_result_tbl WHERE filter_no = %s ORDER BY date DESC LIMIT 1"
                self.cursor.execute(query, (filter_no,))
                result = self.cursor.fetchone()
                result_id = result[0] if result else None
                print(result_id)

                if result_id:
                    self.insert_into_leakapp_test(part_number_id, filter_no, max_value_timer1, status_timer1, shift_id)
                    self.insert_into_leakapp_showreport(filter_no, max_value_timer2, status_timer2, shift_id, part_number_id)

            time.sleep(5)

if __name__ == "__main__":
    db = DatabaseCommunication()
    db.process_filters()
