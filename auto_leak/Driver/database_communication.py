import mysql.connector
from mysql.connector import Error
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseCommunication:
    def __init__(self):
        """Establishes a connection to the MySQL database and checks connectivity."""
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
        """Reconnects to the database in case of failure."""
        logging.info("🔄 Attempting to reconnect to the database...")
        self.close_connection()
        self.connect_db()

    def insert_data(self, part_number, filter_no, filter_values, status):
        """Inserts sensor data into the database."""
        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection:
                logging.error("❌ Unable to reconnect to the database. Data will be lost.")
                return

        try:
            insert_query = """
            INSERT INTO leak_app_result 
            (part_number_id, filter_no, filter_values, status, date, iot_value) 
            VALUES (%s, %s, %s, %s, NOW(), %s)
            """
            self.cursor.execute(insert_query, (part_number, filter_no, filter_values, status, filter_values))
            self.connection.commit()
            logging.info(f"✅ Data inserted: {filter_no} = {filter_values}, Status: {status}")

        except Error as e:
            logging.error(f"❌ Database error: {e}")
            self.reconnect()  # Try reconnecting if insertion fails

    def close_connection(self):
        """Closes the database connection properly."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logging.info("✅ Database connection closed.")

if __name__ == "__main__":
    db = DatabaseCommunication()
