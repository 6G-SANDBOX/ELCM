import socket
import ssl
import json
from Helper import Level, influx
import time
import threading
from .to_influx import ToInfluxBase

class TelegrafToInflux(ToInfluxBase):
    
    def __init__(self, logMethod, parent, params):
        # Initialize the Task superclass and define the expected parameters
        super().__init__("TELEGRAF", parent, params, logMethod, None)
        
        # Define the rules for expected parameters
        self.paramRules = {
            'Measurement': (None, True),    # Measurement name for InfluxDB, required
            'Stop': (None, True),           # Stop signal, required
            'Encryption': (False, True),    # Flag for SSL usage, required
            'Certificates': (None, False),  # Path to SSL certificates, optional
            'Port': (None,False)            # Port, optional 
        }

        self.executionId = self.params['ExecutionId']
        self.use_ssl = self.params.get('Encryption', False)  # Check if SSL is to be used
        base_path = self.params.get('Certificates', "")
        self.port=int(self.params.get('Port',8094))

        # Paths to SSL certificate files
        self.certfile = base_path + "server-cert.pem"
        self.keyfile = base_path + "server-key.pem"
        self.ca = base_path + "ca.pem"
    
    # Method to process incoming data and send it to InfluxDB
    def save_to_influx(self, data):
        
        measurement = self.params['Measurement']
        flattened_data = self._flatten_telegraf_json(data)  
        timestamp = data['timestamp']

        for key in list(flattened_data.keys()):
            value = flattened_data[key]
            if isinstance(value, int):
                flattened_data[key] = float(value)
            
        # Send the flattened data to InfluxDB
        try:
            self._send_to_influx(measurement, flattened_data, timestamp, self.executionId)
        except Exception as e:
            if isinstance(e, influx.InfluxDBError) and e.response.status==442:
                self.Log(Level.WARNING, f"Warning (TELEGRAF): Unprocessable entity (422). Invalid data: {data}")
            else:
                self.Log(Level.ERROR, f"Failed to send data to InfluxDB (TELEGRAF). Exception: {e}")
                raise RuntimeError(f"Exiting due to unexpected error: {e}")
        
    # Method to handle incoming TCP connections
    def tcp_handler(self, stop_event):
        TCP_IP = '0.0.0.0'  # Listen on all available IP addresses
        TCP_PORT = self.port     # Port for incoming TCP connections
        BUFFER_SIZE = 4096  # Size of the buffer to receive data
        MAX_RETRY = 6       # Maximum number of retries for reconnections
        SOCKET_TIMEOUT = 10  # Timeout for socket operations in seconds
        
        try:
            # Set up a TCP socket
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind((TCP_IP, TCP_PORT))
            server_socket.listen(1)
            server_socket.settimeout(SOCKET_TIMEOUT)  # Set socket timeout
            self.Log(Level.INFO, "Socket successfully set up and listening with timeout")
        except Exception as e:
            self.Log(Level.ERROR, f"Error setting up socket: {e}")
            self.SetVerdictOnError()
            return

        if self.use_ssl:
            try:
                # Set up SSL context if encryption is enabled
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
                context.load_verify_locations(cafile=self.ca)
                tls_server_socket = context.wrap_socket(server_socket, server_side=True)
                tls_server_socket.settimeout(SOCKET_TIMEOUT)  # Set timeout for the SSL socket
                self.Log(Level.INFO, "SSL context successfully created and socket wrapped with timeout")
                server_socket.close()  # Close original socket as it's now wrapped with SSL
                server_socket = tls_server_socket
            except Exception as e:
                self.Log(Level.ERROR, f"Error setting up SSL context: {e}")
                self.SetVerdictOnError()
                return

        retry = 0
        connected = False
        while retry <= MAX_RETRY and not connected:
            try:
                # Accept incoming connection
                conn, addr = server_socket.accept()
                conn.settimeout(SOCKET_TIMEOUT)  # Set timeout for the accepted connection
                self.Log(Level.INFO, f"Connection accepted from {addr}")
                connected = True
            except socket.timeout:
                self.Log(Level.WARNING, "Socket accept timed out")
                retry += 1
                time.sleep(5)
                continue
            except Exception as e:
                retry += 1
                self.Log(Level.ERROR, f"Error accepting connection Telegraf: {e}")
                time.sleep(5)  # Wait before retrying
                if retry == MAX_RETRY:
                    self.Log(Level.ERROR, f"Error accepting connection Telegraf: {e}, BYE")
                    server_socket.close()
                    self.SetVerdictOnError()
                    return

        buffer = ""
        while not stop_event.is_set():
            try:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    # Close connection if no data is received
                    conn.close()
                    self.Log(Level.WARNING, "No data received, closing connection")
                    break
                else:
                    try:
                        buffer += data.decode('utf-8', errors='surrogateescape')
                    except UnicodeDecodeError as e:
                        self.Log(Level.ERROR, f"Error decoding data: {e}")
                        break

                    # Process all complete JSON objects in the buffer
                    while True:
                        try:
                            json_data, index = json.JSONDecoder().raw_decode(buffer)
                            self.save_to_influx(json_data)
                            buffer = buffer[index:].lstrip()  # Remove processed JSON object
                        except json.JSONDecodeError:
                            # Wait for more data if JSON is incomplete
                            break

            except socket.timeout:
                self.Log(Level.WARNING, "Socket recv timed out")
                continue
            except json.JSONDecodeError as e:
                self.Log(Level.ERROR, f"Error decoding JSON data: {e}")
                break
            except ConnectionError as e:
                self.Log(Level.WARNING, f"Connection error: {e}")
                retry = 0
                connected = False

                while retry < MAX_RETRY and not connected:
                    try:
                        time.sleep(5)
                        conn, addr = server_socket.accept()
                        conn.settimeout(SOCKET_TIMEOUT)  # Set timeout for the re-accepted connection
                        if conn:
                            connected = True
                    except socket.timeout:
                        self.Log(Level.WARNING, "Socket re-accept timed out")
                    except Exception as e:
                        retry += 1
                        self.Log(Level.ERROR, f"Error re-accepting connection: {e}")

                if retry == MAX_RETRY and not connected:
                    break

            except Exception as e:
                self.Log(Level.ERROR, f"Unexpected error during data handling: {e}")
                break

        try:
            if server_socket:
                server_socket.close()
                self.Log(Level.INFO, "Server socket closed")
        except Exception as e:
            self.Log(Level.ERROR, f"Error closing server socket: {e}")

    # Main method to start the task
    def Run(self):
        stop_event = threading.Event()
        stop = self.params['Stop']

        if not isinstance(self.use_ssl, bool):
            self.Log(Level.ERROR, f"Exception telegraf bool")
            return
        
        # Start the TCP handler in a separate thread
        tcp_thread = threading.Thread(target=self.tcp_handler, args=(stop_event,))
        tcp_thread.start()

        while not self.parent.ReadMilestone(stop) and not self.parent.stopRequested:
            time.sleep(1)

        stop_event.set()
        tcp_thread.join()  # Wait for the TCP handler thread to finish
        self.Log(Level.INFO, "Telegraf task finished")