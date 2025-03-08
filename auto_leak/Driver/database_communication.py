import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime, timedelta

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

    def check_connection(self):
        if self.connection is None or self.cursor is None:
            logging.warning("❌ No database connection. Attempting to reconnect...")
            self.connect_db()

    def update_server_connection(self, device_id, status):
        """Updates the connection status for a given device in the database."""
        try:
            if not self.connection or not self.cursor:
                self.reconnect()
                if not self.connection:
                    logging.error("❌ Unable to reconnect to the database.")
                    return
                
            query = f"UPDATE myplclog SET server_connection_{device_id} = {status}"
            self.cursor.execute(query)
            self.connection.commit()
            logging.info(f"✅ Updated connection status: server_connection_{device_id} = {status}")
        except Exception as e:
            logging.error(f"❌ Error updating connection status in the database: {e}", exc_info=True)
            self.reconnect()

    def insert_data_batch(self, json_data):
        """Inserts sensor data into the appropriate table based on prodstatus."""
        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection:
                logging.error("❌ Unable to reconnect to the database.")
                return

        try:
            # Get current prodstatus and part_number_id
            prodstatus, part_number_id = self.get_prodstatus_and_part_number_id()
            if prodstatus is None or part_number_id is None:
                logging.error("❌ Failed to retrieve prodstatus or part_number_id, data will not be inserted.")
                return
            
            # Get calibration values for all filters
            calibration_values = self.get_calibration_values()
            if not calibration_values:
                logging.warning("⚠️ No calibration values found. Using default values (m=1, c=0).")
                
            # Determine which table to insert into based on prodstatus
            table_name = "foi_tbl" if prodstatus == 1 else "leakapp_result_tbl"
            
            # Prepare and execute batch insert
            insert_query = f"""
            INSERT INTO {table_name} (part_number_id, filter_no, filter_values, date) 
            VALUES (%s, %s, %s, NOW())
            """
            
            batch_data = []
            for filter_no, raw_value in json_data.items():
                if filter_no.startswith("AI") or filter_no.startswith("DI"):
                    # Apply calibration formula if it's an AI value
                    if filter_no.startswith("AI"):
                        # Get m and c values for this filter
                        m, c = calibration_values.get(filter_no, (1, 0))
                        calibrated_value = (m * raw_value) + c
                    else:
                        # For DI values, use as-is
                        calibrated_value = raw_value
                        
                    batch_data.append((part_number_id, filter_no, calibrated_value))
            
            if batch_data:
                self.cursor.executemany(insert_query, batch_data)
                self.connection.commit()
                logging.info(f"✅ Inserted {len(batch_data)} values into {table_name}")
            else:
                logging.warning("⚠️ No valid data to insert")
                
        except Exception as e:
            logging.error(f"❌ Error inserting data batch: {e}", exc_info=True)
            self.reconnect()

    def get_prodstatus_and_part_number_id(self):
        """Fetches the prodstatus and part_number_id from myplclog table."""
        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection:
                logging.error("❌ Unable to reconnect to the database.")
                return None, None

        try:
            query = "SELECT prodstatus, part_number_id FROM myplclog LIMIT 1"
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            return (result[0], result[1]) if result else (None, None)

        except Error as e:
            logging.error(f"❌ Error retrieving prodstatus and part_number: {e}")
            self.reconnect()
            return None, None

    def get_calibration_values(self):
        """Fetches calibration values (m, c) for each filter_no from y_cal_values table."""
        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection:
                logging.error("❌ Unable to reconnect to the database.")
                return {}

        try:
            query = "SELECT filter_no, m_value, c_value FROM y_cal_values"
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            
            # Create a dictionary mapping filter_no to (m, c) values
            calibration_map = {row[0]: (row[1], row[2]) for row in results}
            return calibration_map

        except Error as e:
            logging.error(f"❌ Error retrieving calibration values: {e}")
            self.reconnect()
            return {}

    def get_highest_ai(self, start_time, end_time, ai_key):
        """Fetches the highest AI value from leakapp_result_tbl in the given timeframe."""
        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection:
                logging.error("❌ Unable to reconnect to the database.")
                return 0

        try:
            # Convert timestamp to MySQL timestamp format if needed
            query = """
            SELECT MAX(filter_values) FROM leakapp_result_tbl
            WHERE date BETWEEN FROM_UNIXTIME(%s) AND FROM_UNIXTIME(%s) AND filter_no = %s
            """
            
            # Log query parameters for debugging
            logging.info(f"Querying for highest {ai_key} between {start_time} and {end_time}")
            
            self.cursor.execute(query, (start_time, end_time, ai_key))
            result = self.cursor.fetchone()
            
            highest_value = result[0] if result and result[0] is not None else 0
            
            # Add debug logging
            if highest_value == 0:
                # Check if any records exist for this timeframe
                self.cursor.execute(
                    "SELECT COUNT(*) FROM leakapp_result_tbl WHERE date BETWEEN FROM_UNIXTIME(%s) AND FROM_UNIXTIME(%s)",
                    (start_time, end_time)
                )
                count = self.cursor.fetchone()[0]
                logging.warning(f"Found {count} total records in timeframe, but no values for {ai_key}")
                
            logging.info(f"📊 Highest {ai_key} value from database between {start_time} and {end_time}: {highest_value}")
            return highest_value
        except mysql.connector.Error as e:
            logging.error(f"❌ Database error in get_highest_ai: {e}")
            self.reconnect()
            return 0

    def get_setpoints(self):
        """Fetches timer and setpoint values from leakapp_masterdata."""
        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection:
                logging.error("❌ Unable to reconnect to the database.")
                return {"timer1": 0, "setpoint1": 0, "timer2": 0, "setpoint2": 0}

        try:
            # Get part_number_id from active part
            self.cursor.execute("SELECT part_number_id FROM myplclog LIMIT 1")
            part_number_id = self.cursor.fetchone()[0]
            
            # Get setpoints for this part
            query = """
            SELECT timer1, setpoint1, timer2, setpoint2 
            FROM leakapp_masterdata 
            WHERE id = %s
            """
            self.cursor.execute(query, (part_number_id,))
            result = self.cursor.fetchone()
            
            if result:
                # Convert DurationField to seconds
                timer1_seconds = result[0].total_seconds() if hasattr(result[0], 'total_seconds') else float(result[0])
                timer2_seconds = result[2].total_seconds() if hasattr(result[2], 'total_seconds') else float(result[2])
                
                setpoints = {
                    "timer1": timer1_seconds,
                    "setpoint1": float(result[1]),
                    "timer2": timer2_seconds,
                    "setpoint2": float(result[3]),
                }
                logging.info(f"📊 Fetched setpoints: {setpoints}")
                return setpoints
            else:
                logging.warning(f"⚠️ No setpoint data found for part_number_id {part_number_id}")
                return {"timer1": 0, "setpoint1": 0, "timer2": 0, "setpoint2": 0}
                
        except Exception as e:
            logging.error(f"❌ Error fetching setpoints: {e}", exc_info=True)
            self.reconnect()
            return {"timer1": 0, "setpoint1": 0, "timer2": 0, "setpoint2": 0}

    def fetch_shift_id(self):
        """Fetches the active shift ID based on the current time, handling overnight shifts."""
        try:
            self.check_connection()
            query = "SELECT id, start_time, end_time FROM shift_tbl"
            self.cursor.execute(query)
            shifts = self.cursor.fetchall()
            logging.info(f"📊 Fetched shifts: {shifts}")
            
            current_time = datetime.now().time()
            logging.info(f"🕒 Checking shift for current time: {current_time}")

            for shift_id, start_time, end_time in shifts:
                # Convert timedelta to time if needed
                if isinstance(start_time, timedelta):
                    start_time = (datetime.min + start_time).time()
                if isinstance(end_time, timedelta):
                    end_time = (datetime.min + end_time).time()

                logging.info(f"⏳ Checking shift {shift_id}: {start_time} - {end_time}")

                # Handle normal shifts (same day)
                if start_time <= end_time:
                    if start_time <= current_time <= end_time:
                        logging.info(f"✅ Active shift found: {shift_id}")
                        return shift_id
                else:
                    # Handle overnight shifts (crosses midnight)
                    if current_time >= start_time or current_time <= end_time:
                        logging.info(f"✅ Active overnight shift found: {shift_id}")
                        return shift_id

            logging.warning("⚠️ No matching shift found for the current time.")
            return None

        except Error as e:
            logging.error(f"❌ Error fetching shift data: {e}", exc_info=True)
            return None

    def save_report(self, date, status, all_max_values):
        """Stores the result for all AI filters in leakapp_show_report."""
        logging.info("Inside save_report with status: %s", status)
        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection:
                logging.error("❌ Unable to reconnect to the database.")
                return

        try:
            # Get the current part_number_id
            self.cursor.execute("SELECT part_number_id FROM myplclog LIMIT 1")
            part_number_id = self.cursor.fetchone()[0]

            # Get the active shift ID
            shift_id = self.fetch_shift_id()
            logging.info(f"Current shift_id: {shift_id}")
            
            # Get the latest batch counter and increment
            self.cursor.execute("SELECT MAX(batch_counter) FROM leakapp_show_report")
            batch_result = self.cursor.fetchone()
            batch_counter = 1
            if batch_result and batch_result[0]:
                batch_counter = batch_result[0] + 1
            
            # Save data for all AI filters
            for i in range(1, 17):
                filter_no = f"AI{i}"
                # Get max value for this filter from the passed dictionary
                max_value = all_max_values.get(filter_no, 0)
                
                # Insert into show report
                query = """
                INSERT INTO leakapp_show_report 
                (date, part_number_id, filter_no, filter_values, highest_value, status, batch_counter, shift_id) 
                VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s, %s, %s)
                """
                self.cursor.execute(
                    query, 
                    (date, part_number_id, filter_no, max_value, max_value, status, batch_counter, shift_id)
                )
            
            self.connection.commit()
            logging.info(f"✅ Report saved for all AI filters: Date={date}, Status={status}, Batch={batch_counter}")
            
        except Exception as e:
            logging.error(f"❌ Error saving report: {e}", exc_info=True)
            self.reconnect()

    def save_single_filter_report(self, date, filter_no, max_value, status):
        """
        Stores the result for a single AI filter in leakapp_show_report and updates leakapp_test.
        """
        logging.info(f"Saving report for {filter_no} with value {max_value}, status: {status}")
        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection:
                logging.error("❌ Unable to reconnect to the database.")
                return

        try:
            # Get the current part_number_id
            self.cursor.execute("SELECT part_number_id FROM myplclog LIMIT 1")
            part_number_id = self.cursor.fetchone()[0]

            # Get the active shift ID
            shift_id = self.fetch_shift_id()
            logging.info(f"Current shift_id: {shift_id}")
            
            # Get the latest batch counter and increment
            self.cursor.execute("SELECT MAX(batch_counter) FROM leakapp_show_report")
            batch_result = self.cursor.fetchone()
            batch_counter = 1
            if batch_result and batch_result[0]:
                batch_counter = batch_result[0] + 1
            
            # Insert into leakapp_show_report
            show_report_query = """
            INSERT INTO leakapp_show_report 
            (date, part_number_id, filter_no, filter_values, highest_value, status, batch_counter, shift_id) 
            VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(
                show_report_query, 
                (date, part_number_id, filter_no, max_value, max_value, status, batch_counter, shift_id)
            )
            
            # Now update the leakapp_test table with the same information
            # First check if the filter already exists
            check_query = """
            SELECT id FROM leakapp_test 
            WHERE filter_no = %s
            """
            self.cursor.execute(check_query, (filter_no, ))
            existing_filter = self.cursor.fetchone()
            
            if existing_filter:
                # Filter exists, update it
                update_query = """
                UPDATE leakapp_test 
                SET part_number_id = %s,
                    filter_values = %s, 
                    highest_value = %s, 
                    status = %s, 
                    batch_counter = %s, 
                    shift_id = %s,
                    date = FROM_UNIXTIME(%s)
                WHERE id = %s
                """
                self.cursor.execute(
                    update_query, 
                    (part_number_id, max_value, max_value, status, batch_counter, shift_id, date, existing_filter[0])
                )
                logging.info(f"✅ Updated existing filter in leakapp_test: {filter_no}, ID={existing_filter[0]}")
            else:
                # Filter doesn't exist, create it
                insert_query = """
                INSERT INTO leakapp_test 
                (date, part_number_id, filter_no, filter_values, highest_value, status, batch_counter, shift_id) 
                VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s, %s, %s)
                """
                self.cursor.execute(
                    insert_query, 
                    (date, part_number_id, filter_no, max_value, max_value, status, batch_counter, shift_id)
                )
                logging.info(f"✅ Created new filter in leakapp_test: {filter_no}")
            
            self.connection.commit()
            logging.info(f"✅ Report saved for {filter_no}: Date={date}, Value={max_value}, Status={status}, Batch={batch_counter}")
            
        except Exception as e:
            logging.error(f"❌ Error saving single filter report: {e}", exc_info=True)
            self.reconnect()

    def close_connection(self):
        """Closes the database connection properly."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logging.info("✅ Database connection closed.")