import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from mysql.connector import Error
import logging
from datetime import datetime, timedelta
import time
import threading
import contextlib
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def with_connection(func):
    """Decorator that ensures a valid connection for database operations."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                if not self.connection or not self.cursor or not self.connection.is_connected():
                    self.reconnect()
                
                # If we still don't have a connection after reconnect attempt, retry
                if not self.connection or not self.cursor:
                    retry_count += 1
                    time.sleep(1)
                    continue
                    
                return func(self, *args, **kwargs)
                
            except mysql.connector.Error as e:
                # Handle MySQL specific errors
                logging.error(f"❌ MySQL Error in {func.__name__}: {e}")
                if self.connection and hasattr(self.connection, 'is_connected') and self.connection.is_connected():
                    if self.connection.in_transaction:
                        self.connection.rollback()
                
                # Connection errors should trigger reconnection attempt
                if e.errno in (2006, 2013, 2003):
                    self.reconnect()
                
                retry_count += 1
                if retry_count >= max_retries:
                    logging.error(f"❌ Max retries reached in {func.__name__}")
                    return None  # Or appropriate default value
                
                time.sleep(1)  # Wait before retry
                
            except Exception as e:
                logging.error(f"❌ General error in {func.__name__}: {e}", exc_info=True)
                if self.connection and hasattr(self.connection, 'is_connected') and self.connection.is_connected():
                    if self.connection.in_transaction:
                        self.connection.rollback()
                
                retry_count += 1
                if retry_count >= max_retries:
                    logging.error(f"❌ Max retries reached in {func.__name__} after general error")
                    return None
                time.sleep(5)
        return None
    
    return wrapper

class DatabaseCommunication:
    _thread_local = threading.local()
    _pool_lock = threading.Lock()
    
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
        self.cnxpool = None
        self.last_used = time.time()
        self.max_idle_time = 60
        
        # Try to create a connection pool but have fallback mechanism
        try:
            with self._pool_lock:
                self.cnxpool = mysql.connector.pooling.MySQLConnectionPool(
                    pool_name="leak_detection_pool",
                    pool_size=32,  # Maintain pool size of 32
                    pool_reset_session=True,
                    **self.db_config
                )
            logging.info("✅ Database connection pool created successfully!")
        except Error as e:
            logging.error(f"❌ Failed to create connection pool: {e}")
            self.cnxpool = None
            
        # Connect to database (either using pool or direct connection)
        self.connect_db()

    def connect_db(self):
        """Connects to the database and initializes the cursor."""
        
        try:
            if hasattr(self, 'cnxpool') and self.cnxpool:
                with self._pool_lock:
                    self.connection = self.cnxpool.get_connection()
                logging.info("✅ Got connection from pool")
            else:
                self.connection = mysql.connector.connect(**self.db_config)
                logging.info("✅ Created new connection")
            
            self.connection.autocommit = False  # Explicit transaction management
            self.cursor = self.connection.cursor(buffered=True)  # Use buffered cursor for efficiency
            logging.info("✅ Database connection established successfully!")
        except Error as e:
            logging.error(f"❌ Database connection failed: {e}")
            self.connection = None
            self.cursor = None

    def reconnect(self):
        """Reconnects to the database if disconnected."""
        logging.info("🔄 Attempting to reconnect to the database...")
        try:
            self.close_connection()
            time.sleep(0.1)  # Brief pause before reconnection attempt
            self.connect_db()
        except Exception as e:
            logging.error(f"❌ Error during reconnection: {e}", exc_info=True)
            # Make sure connection and cursor are nullified
            self.connection = None
            self.cursor = None
    
    @contextlib.contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        if not self.connection or not self.cursor:
            self.reconnect()
            if not self.connection:
                raise Exception("Failed to establish database connection for transaction")
                
        try:
            # Make sure we're not in a transaction already
            if self.connection.in_transaction:
                self.connection.rollback()
                logging.warning("⚠️ Rolling back previous transaction before starting a new one")
                
            # Start transaction
            logging.debug("Starting database transaction")
            yield self
            # Commit if no exceptions
            self.connection.commit()
            logging.debug("Transaction committed")
        except Exception as e:
            # Rollback on exception
            if self.connection and hasattr(self.connection, 'is_connected') and self.connection.is_connected():
                if self.connection.in_transaction:
                    self.connection.rollback()
                    logging.warning("Transaction rolled back due to error")
            raise e

    def ping_connection(self):
        """Ping the database to keep the connection alive."""
        try:
            self.ensure_connection()
            logging.debug("✅ Database connection ping successful")
        except Exception as e:
            logging.error(f"❌ Database ping failed: {e}")
    
    def close_connection(self):
        """Close the database connection."""
        if self.connection:
            try:
                self.connection.close()
                logging.info("✅ Database connection closed")
            except Exception as e:
                logging.error(f"❌ Error closing database connection: {e}")

    @with_connection
    def update_server_connection(self, device_id, status):
        """Updates the server connection status for a device."""
        try:
            # Fix the typo in column name
            column_name = f'server_connection_{device_id}'
            query = f"UPDATE myplclog SET {column_name} = %s"
            
            # Log before executing
            logging.info(f"🔄 Updating {column_name} to {status} using query: {query}")
            
            # Execute the update
            self.cursor.execute(query, (status,))
            
            # Get number of affected rows to verify update worked
            affected_rows = self.cursor.rowcount
            logging.info(f"✅ Query affected {affected_rows} rows")
            
            # Commit explicitly
            self.connection.commit()
            logging.info(f"✅ Successfully updated connection status: {column_name} = {status}")
            
            return True
        except Exception as e:
            logging.error(f"❌ Error updating {column_name}: {e}", exc_info=True)
            if self.connection and self.connection.is_connected():
                self.connection.rollback()
            return False
    def ensure_connection(self):
        """Ensure the database connection is valid before operations."""
        try:
            # Check if connection is too old (idle for too long)
            if time.time() - self.last_used > self.max_idle_time:
                logging.info("🔄 Connection idle for too long, refreshing...")
                self.connect_db()
                return
            
            # Check if connection is still valid with a simple query
            self.cursor.execute("SELECT 1")
            self.connection.commit()
            self.last_used = time.time()
        except Exception as e:
            logging.warning(f"⚠️ Database connection check failed: {e}")
            self.connect_db()

    @with_connection
    def insert_data_batch(self, json_data):
        """Inserts sensor data into the appropriate table based on prodstatus."""
        self.ensure_connection()
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
            with self.transaction():
                self.cursor.executemany(insert_query, batch_data)
            logging.info(f"✅ Inserted {len(batch_data)} values into {table_name}")
        else:
            logging.warning("⚠️ No valid data to insert")

    @with_connection
    def get_prodstatus_and_part_number_id(self):
        """Fetches the prodstatus and part_number_id from myplclog table."""
        query = "SELECT prodstatus, part_number_id FROM myplclog LIMIT 1"
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        return (result[0], result[1]) if result else (None, None)

    @with_connection
    def get_calibration_values(self):
        """Fetches calibration values (m, c) for each filter_no from y_cal_values table."""
        query = "SELECT filter_no, m_value, c_value FROM y_cal_values"
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        
        # Create a dictionary mapping filter_no to (m, c) values
        calibration_map = {row[0]: (row[1], row[2]) for row in results}
        return calibration_map

    @with_connection
    def get_highest_ai(self, start_time, end_time, ai_key):
        """Fetches the highest AI value from leakapp_result_tbl in the given timeframe."""
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

    @with_connection
    def get_setpoints(self):
        """Fetches timer and setpoint values from leakapp_masterdata."""
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

    @with_connection
    def fetch_shift_id(self):
        """Fetches the active shift ID based on the current time, handling overnight shifts."""
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

    @with_connection
    def save_report(self, date, status, all_max_values):
        """Stores the result for all AI filters in leakapp_show_report."""
        logging.info("Inside save_report with status: %s", status)
        
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
        
        # Use transaction for batch insert
        with self.transaction():
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
        
        logging.info(f"✅ Report saved for all AI filters: Date={date}, Status={status}, Batch={batch_counter}")

    @with_connection
    def save_single_filter_report(self, date, filter_no, max_value, status):
        """
        Stores the result for a single AI filter in leakapp_show_report and updates leakapp_test.
        Returns True if successful, False otherwise.
        """
        logging.info(f"🔍 Starting save_single_filter_report for {filter_no} with value {max_value}, status: {status}")
        
        with self.transaction():
            # Get the current part_number_id
            self.cursor.execute("SELECT part_number_id FROM myplclog LIMIT 1")
            result = self.cursor.fetchone()
            if not result:
                logging.error("❌ Could not fetch part_number_id from myplclog")
                return False
            
            part_number_id = result[0]
            logging.info(f"📊 Using part_number_id: {part_number_id}")

            # Get the active shift ID
            shift_id = self.fetch_shift_id()
            logging.info(f"📊 Current shift_id: {shift_id}")
            if shift_id is None:
                logging.warning("⚠️ No active shift found, using NULL for shift_id")
            
            # Get the latest batch counter and increment
            self.cursor.execute("SELECT MAX(batch_counter) FROM leakapp_show_report")
            batch_result = self.cursor.fetchone()
            batch_counter = 1
            if batch_result and batch_result[0]:
                batch_counter = batch_result[0] + 1
            logging.info(f"📊 Using batch_counter: {batch_counter}")

            # Insert into leakapp_show_report table
            logging.info(f"🔍 Inserting into leakapp_show_report: {filter_no}, value: {max_value}")
            show_report_query = """
            INSERT INTO leakapp_show_report 
            (date, part_number_id, filter_no, filter_values, highest_value, status, batch_counter, shift_id) 
            VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(
                show_report_query, 
                (date, part_number_id, filter_no, max_value, max_value, status, batch_counter, shift_id)
            )
            show_report_id = self.cursor.lastrowid
            logging.info(f"✅ Inserted into leakapp_show_report with ID: {show_report_id}")

            # Update or insert into the leakapp_test table
            logging.info(f"🔍 Checking if {filter_no} exists in leakapp_test")
            check_query = """
            SELECT id FROM leakapp_test 
            WHERE part_number_id = %s AND filter_no = %s
            """
            self.cursor.execute(check_query, (part_number_id, filter_no))
            existing_filter = self.cursor.fetchone()
            
            if existing_filter:
                # Filter exists, update it
                logging.info(f"🔍 Updating existing record in leakapp_test for {filter_no} with ID {existing_filter[0]}")
                update_query = """
                UPDATE leakapp_test 
                SET filter_values = %s, 
                    highest_value = %s, 
                    status = %s, 
                    batch_counter = %s, 
                    shift_id = %s,
                    date = FROM_UNIXTIME(%s)
                WHERE id = %s
                """
                self.cursor.execute(
                    update_query, 
                    (max_value, max_value, status, batch_counter, shift_id, date, existing_filter[0])
                )
                logging.info(f"✅ Updated existing filter in leakapp_test: {filter_no}, ID={existing_filter[0]}")
            else:
                # Filter doesn't exist, create it
                logging.info(f"🔍 Creating new record in leakapp_test for {filter_no}")
                insert_query = """
                INSERT INTO leakapp_test 
                (date, part_number_id, filter_no, filter_values, highest_value, status, batch_counter, shift_id) 
                VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s, %s, %s)
                """
                self.cursor.execute(
                    insert_query, 
                    (date, part_number_id, filter_no, max_value, max_value, status, batch_counter, shift_id)
                )
                test_id = self.cursor.lastrowid
                logging.info(f"✅ Created new filter in leakapp_test: {filter_no} with ID {test_id}")
        
        return True
            
    def __del__(self):
        """Destructor to ensure connections are closed."""
        self.close_connection()