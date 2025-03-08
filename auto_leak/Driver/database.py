import mysql.connector
from mysql.connector import Error
import logging
import time
import requests
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_communication.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

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
        self.previous_prodstatus = None
        self.connect_db()

    def connect_db(self):
        """Connects to the database and initializes the cursor."""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            self.cursor = self.connection.cursor()
            self.connection.autocommit = True  # Enable autocommit to reflect changes immediately
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

    def close_connection(self):
        """Closes the database connection properly."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logging.info("✅ Database connection closed.")

    def check_connection(self):
        """Checks if the cursor and connection are valid."""
        if self.connection is None or self.cursor is None:
            logging.warning("❌ No database connection or cursor. Attempting to reconnect...")
            self.reconnect()

    def fetch_prodstatus(self):
        """Fetches the prodstatus value from myplclog table."""
        try:
            self.check_connection()  # Ensure the connection is valid
            query = "SELECT prodstatus FROM myplclog LIMIT 1"
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            if result:
                current_prodstatus = result[0]
                logging.info(f"✅ Fetched current prodstatus: {current_prodstatus}")
                return current_prodstatus
            else:
                logging.error("❌ Failed to fetch prodstatus.")
                return None
        except Error as e:
            logging.error(f"❌ Error fetching prodstatus: {e}")
            return None

    def fetch_part_number_id(self):
        """Fetches the part_number_id from the myplclog table."""
        try:
            self.check_connection()  # Ensure the connection is valid
            query = "SELECT part_number_id FROM myplclog LIMIT 1"
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            if result:
                part_number_id = result[0]
                logging.info(f"✅ Fetched part_number_id: {part_number_id}")
                return part_number_id
            else:
                logging.error("❌ Failed to fetch part_number_id.")
                return None
        except Error as e:
            logging.error(f"❌ Error fetching part_number_id: {e}")
            return None

    def insert_foihighest(self, filter_no, filter_values, highest_value, batch_counter):
        """Inserts data into the foihighest_tbl."""
        try:
            # Fetch part_number_id from myplclog
            part_number_id = self.fetch_part_number_id()
            if part_number_id is None:
                logging.error("❌ Failed to retrieve part_number_id. Data will not be inserted.")
                return

            # Prepare the query to insert into foihighest_tbl
            query = """
                INSERT INTO foihighest (part_number_id, batch_counter, filter_no, filter_values, highest_value, status, date)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """

            # Prepare the data to insert
            data = (part_number_id, batch_counter, filter_no, filter_values, highest_value, "Not Ok")
            self.cursor.execute(query, data)
            self.connection.commit()
            logging.info(f"✅ Data inserted into foihighest_tbl: {data}")

        except Error as e:
            logging.error(f"❌ Error inserting data into foihighest_tbl: {e}")
            self.reconnect()

    def fetch_max_filter_values(self):
        """Fetches the max value for each FilterNo (AI1 to AI16) from foi_table."""
        filter_values = {}
        try:
            self.check_connection()  # Ensure the connection is valid
            for i in range(1, 17):
                filter_no = f"AI{i}"
                query = f"SELECT MAX(filter_values) FROM foi_tbl WHERE filter_no = %s"
                self.cursor.execute(query, (filter_no,))
                result = self.cursor.fetchone()
                if result:
                    filter_values[filter_no] = result[0]
                    logging.info(f"✅ Max value for {filter_no}: {result[0]}")
                else:
                    logging.warning(f"❌ No values found for {filter_no}.")
            return filter_values
        except Error as e:
            logging.error(f"❌ Error fetching filter values: {e}")
            return {}

    def delete_from_foi_tbl(self):
        """Deletes all data from the foi_tbl after POST request success."""
        try:
            query = "DELETE FROM foi_tbl WHERE 1"
            self.cursor.execute(query)
            self.connection.commit()
            logging.info("✅ Data successfully deleted from foi_tbl.")
        except Error as e:
            logging.error(f"❌ Error deleting data from foi_tbl: {e}")

    def send_post_request(self, data):
        """Sends a POST request with the collected data."""
        try:
            # Restructure the data into the required format
            post_data = {
                'apikey': "",
                'field1': "",
                'field2': "",
                'field3': "",
                'test': data
            }

            # url = "https://irouteinspapi.fleetguard-forum.com:4443/ThirdPartyAPI/Update"
            url = "https://httpbin.org/post"
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, data=json.dumps(post_data), headers=headers)

            if response.status_code == 200:
                logging.info("✅ Data successfully posted to the external service.")
                print("Response from httpbin:", response.json())  # Print the response data
                return True
            else:
                logging.error(f"❌ Failed to post data. HTTP Status Code: {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"❌ Error while sending POST request: {e}")
            return False

if __name__ == "__main__":
    db = DatabaseCommunication()

    while True:
        try:
            # Fetch the current prodstatus
            current_prodstatus = db.fetch_prodstatus()

            if current_prodstatus is not None:
                # If this is the first iteration, set the previous_prodstatus to current_prodstatus
                if db.previous_prodstatus is None:
                    db.previous_prodstatus = current_prodstatus
                    logging.info(f"First iteration: Set previous_prodstatus to {current_prodstatus}")

                # Now compare current_prodstatus with previous_prodstatus
                # Case: Transition from prodstatus 0 to 1, send data
                if db.previous_prodstatus ==1  and current_prodstatus == 0:
                    logging.info("✅ Transition from prodstatus 0 to 1 detected. Sending data...")

                    # Fetch filter values and insert into foihighest_tbl
                    filter_values = db.fetch_max_filter_values()
                    if filter_values:
                        for filter_no, filter_value in filter_values.items():
                            highest_value = filter_value  # You can customize this logic if needed
                            db.insert_foihighest(filter_no, filter_value, highest_value, batch_counter=1)

                        # Attempt to send the POST request
                        if db.send_post_request(filter_values):
                            # If the POST request is successful, delete data from foi_tbl
                            db.delete_from_foi_tbl()
                        else:
                            logging.warning("❌ POST request failed. Not deleting data from foi_tbl.")

                    else:
                        logging.warning("❌ No valid filter values found.")

                # Update the previous_prodstatus only if current_prodstatus has changed
                if current_prodstatus != db.previous_prodstatus:
                    db.previous_prodstatus = current_prodstatus
                    logging.info(f"Updated previous_prodstatus to {db.previous_prodstatus}")

            else:
                logging.warning("❌ Could not fetch prodstatus. Skipping this cycle.")

            time.sleep(0.3)

        except Exception as e:
            logging.error(f"❌ An error occurred during the main loop: {e}")
            time.sleep(0.3)
