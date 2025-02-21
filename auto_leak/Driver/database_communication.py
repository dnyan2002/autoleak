import mysql.connector
from mysql.connector import Error
import logging
import socket
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
        logging.info("🔄 Reconnecting to the database...")
        self.connect_db()

    def insert_data(self, part_number, filter_no, filter_values, status):
        """Check if data exists and insert sensor data into the database."""
        if not self.connection:
            self.reconnect()
        
        try:
            insert_query = """
            INSERT INTO leakapp_result_tbl 
            (part_number_id, filter_no, filter_values, status) 
            VALUES (%s, %s, %s, %s)
            """
            self.cursor.execute(insert_query, (part_number, filter_no, filter_values, status))
            self.connection.commit()
            logging.info("✅ Data inserted successfully.")
        
        except Error as e:
            logging.error(f"❌ Database error: {e}")

    
    def fetch_data_from_device(self, host, port, retries=3):
        """Connects to an IoT device and retrieves data with retry logic."""
        for attempt in range(retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)
                    s.connect((host, port))
                    s.sendall(b'GET_DATA')
                    data = s.recv(1024).decode('utf-8')
                    logging.info(f"Received data: {data}")
                    return data
            except (socket.timeout, ConnectionRefusedError) as e:
                logging.warning(f"Attempt {attempt+1}: Connection failed - {e}")
                time.sleep(2)
        logging.error("Failed to retrieve data after multiple attempts.")
        return None

    def main(self):
        """Main function to fetch data and insert into the database."""
        while True:
            sensor_data = self.fetch_data_from_device('192.168.1.12', 5050)
            if sensor_data is not None:
                self.insert_data(sensor_data)
            time.sleep(10)

    def close_connection(self):
        """Closes the database connection properly."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logging.info("✅ Database connection closed.")

if __name__ == "__main__":
    db = DatabaseCommunication()
    db.main()
