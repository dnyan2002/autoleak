import mysql.connector
from mysql.connector import Error
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseCommunication:
    def __init__(self):
        """Establishes a connection to the MySQL database."""
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
        """Connects to the database and initializes the cursor."""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            self.cursor = self.connection.cursor()
            logging.info("✅ Database connection established successfully!")
        except Error as e:
            logging.error(f"❌ Database connection failed: {e}")
            self.connection = None
            self.cursor = None

    def reconnect(self):
        """Reconnects to the database if disconnected."""
        logging.info("🔄 Attempting to reconnect to the database...")
        self.close_connection()
        self.connect_db()

    def get_prodstatus_and_part_number_id(self):
        """Fetches the prodstatus and part_number_id from myplclog table."""
        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection:
                logging.error("❌ Unable to reconnect to the database.")
                return None, None

        try:
            query = "SELECT prodstatus, part_number FROM myplclog LIMIT 1"
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            return (result[0], result[1]) if result else (None, None)

        except Error as e:
            logging.error(f"❌ Error retrieving prodstatus and part_number: {e}")
            self.reconnect()
            return None, None

    def get_calibration_values(self):
        """Fetches calibration values (m, c) for each filter_no from y_cal_values table."""
        query = "SELECT filter_no, m_value, c_value FROM y_cal_values"
        
        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection:
                logging.error("❌ Unable to reconnect to the database.")
                return {}

        try:
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            
            # Create a dictionary mapping filter_no to (m, c) values
            calibration_map = {row[0]: (row[1], row[2]) for row in results}
            return calibration_map

        except Error as e:
            logging.error(f"❌ Error retrieving calibration values: {e}")
            self.reconnect()
            return {}

    def insert_data_batch(self, json_data):
        """Inserts multiple sensor data records with calibrated values."""
        prodstatus, part_number_id = self.get_prodstatus_and_part_number_id()

        if prodstatus is None or part_number_id is None:
            logging.error("❌ Failed to retrieve prodstatus or part_number_id, batch data will not be inserted.")
            return

        calibration_values = self.get_calibration_values()  # Get (m, c) values for each filter_no

        if not calibration_values:
            logging.error("❌ No calibration values found. Batch data will not be inserted.")
            return

        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection or not self.cursor:
                logging.error("❌ Unable to reconnect to the database. Data will be lost.")
                return

        try:
            if prodstatus == 1:
                insert_query = """
                INSERT INTO foi_tbl (part_number_id, filter_no, filter_values, date) 
                VALUES (%s, %s, %s, NOW())
                """
            else:
                insert_query = """
                INSERT INTO leakapp_result_tbl (part_number_id, filter_no, filter_values, date) 
                VALUES (%s, %s, %s, NOW())
                """

            # Apply formula using correct m, c values from DB
            batch_data = [
                (part_number_id, filter_no, (calibration_values.get(filter_no, (1, 0))[0] * raw_value) + calibration_values.get(filter_no, (1, 0))[1])
                for filter_no, raw_value in json_data.items()
            ]

            self.cursor.executemany(insert_query, batch_data)
            self.connection.commit()
            logging.info(f"✅ Batch data inserted successfully: {len(batch_data)} records.")

        except Error as e:
            logging.error(f"❌ Database error: {e}")
            self.reconnect()

    def close_connection(self):
        """Closes the database connection properly."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logging.info("✅ Database connection closed.")

if __name__ == "__main__":
    db = DatabaseCommunication()
