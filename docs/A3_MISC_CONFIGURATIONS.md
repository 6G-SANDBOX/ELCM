**Notes**: It is necessary to have keytool and openssl installed to generate the certificates in ELCM/Certificates.
This guide is a generic example and may require specific adaptations depending on the project context or particular needs.
# KAFKA Configuration Guide
**KAFKA configuration, user and password without SSL - server.properties**:
```html
security.inter.broker.protocol=SASL_PLAINTEXT
sasl.mechanism.inter.broker.protocol=PLAIN

listeners=SASL_PLAINTEXT://:9092
advertised.listeners=SASL_PLAINTEXT://localhost:9092
listener.security.protocol.map=SASL_PLAINTEXT:SASL_PLAINTEXT

sasl.enabled.mechanisms=PLAIN
```
**KAFKA configuration, only SSL - server.properties**:
```html
listeners=PLAINTEXT://0.0.0.0:9092,SSL://0.0.0.0:9093
advertised.listeners=PLAINTEXT://localhost:9092,SSL://localhost:9093
ssl.keystore.location=C:/ELCM/Certificates/kafka/kafka.broker.keystore.jks
ssl.keystore.password=12345678
ssl.key.password=12345678
ssl.truststore.location=C:/ELCM/Certificates/kafka/kafka.broker.truststore.jks
ssl.truststore.password=12345678
```
**KAFKA configuration, user and password with SSL - server.properties**:
```html
ssl.keystore.location=C:/ELCM/Certificates/kafka/kafka.broker.keystore.jks
ssl.keystore.password=12345678
ssl.key.password=12345678
ssl.truststore.location=C:/ELCM/Certificates/kafka/kafka.broker.truststore.jks
ssl.truststore.password=12345678

security.inter.broker.protocol=SASL_SSL
sasl.mechanism.inter.broker.protocol=PLAIN
listener.name.internal.sasl.enabled.mechanisms=PLAIN
listeners=SASL_SSL://0.0.0.0:9093
advertised.listeners=SASL_SSL://localhost:9093
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,SASL_SSL:SASL_SSL
sasl.enabled.mechanisms=PLAIN
sasl.mechanism.controller=PLAIN
```
**KAFKA configuration, for user and password - kafka_server_jaas.conf**:

```html
KafkaServer {
   org.apache.kafka.common.security.plain.PlainLoginModule required
   username="broker_user"
   password="broker_password"
   user_broker_user="broker_password"
   user_user1="password1"
   user_user2="password2";
};
```
# Mosquitto Configuration Guide

## Introduction

Mosquitto is an open-source MQTT broker that supports various configurations for encryption and authentication.

## Prerequisites

- Mosquitto broker installed on your Windows machine.
- Certificates for TLS/SSL if using encryption.
- Credentials for authentication if required.

## Configuration Cases

### Case 1: Encryption Enabled, Authentication Required

**Generate SSL Certificates**:
   Ensure you have the following certificates:
   - `ca.pem` (CA certificate)
   - `client-cert.pem` (Client certificate)
   - `client-key.pem` (Client key)

**Edit the Mosquitto Configuration File**:
   Open the Mosquitto configuration file (`mosquitto.conf`). This file is typically located in the installation directory, for example, `C:\Program Files\mosquitto\`.

   Add or update the following configuration:

   ```conf
   listener 8883
   cafile C:\path\to\ca.pem
   certfile C:\path\to\client-cert.pem
   keyfile C:\path\to\client-key.pem
   require_certificate true
   allow_anonymous false
   password_file C:\path\to\passwordfile
   ```
### Case 2: Encryption Enabled, No Authentication

**Generate SSL Certificates**:
   Ensure you have the following certificates:
   - `ca.pem` (CA certificate)
   - `server-cert.pem` (Server certificate)
   - `server-key.pem` (Server key)

**Edit the Mosquitto Configuration File**:
   Open the Mosquitto configuration file (`mosquitto.conf`). This file is typically located in the installation directory, for example, `C:\Program Files\mosquitto\`.

   Add or update the following configuration:

   ```conf
   listener 8883
   cafile C:\path\to\ca.pem
   certfile C:\path\to\server-cert.pem
   keyfile C:\path\to\server-key.pem
   require_certificate true
   allow_anonymous true
  ```
### Case 3: No Encryption, Authentication Required
**Create a Password File**:
   Use the `mosquitto_passwd` utility to create a password file. Open Command Prompt as Administrator and run:

  
   mosquitto_passwd -c C:\path\to\passwordfile username
  
  ```conf
  listener 1885
  allow_anonymous false
  password_file C:\path\to\passwordfile
  ```

### Case 4: No Encryption, No Authentication

**Edit the Mosquitto Configuration File**:
   Open the Mosquitto configuration file (`mosquitto.conf`). This file is typically located in the installation directory, for example, `C:\Program Files\mosquitto\`.

   Add or update the following configuration:

   ```conf
   listener 1885
   allow_anonymous true
   ```

# PROMETHEUS Configuration Guide

**PROMETHEUS configuration, user and password without SSL - web.config.yml**:
```html
basic_auth_users:
    admin: $2a$12$N5gdOu3klRE.bEngaiI59.LHu4aFj2G3PVt5m9D9nMrY3.2nWrOoi
```
The administrator password is stored in hash format, and in plain text corresponds to 'admin'

[Link to generate hashes](https://bcrypt-generator.com/)

**PROMETHEUS configuration, only SSL - web.config.yml**:
```html
tls_server_config:
  cert_file: C:/ELCM/Certificates/prometheus/server-cert.pem
  key_file: C:/ELCM/Certificates/prometheus/server-key.pem
  client_ca_file: C:/ELCM/Certificates/prometheus/ca.pem
  client_auth_type: RequireAndVerifyClientCert
```

**PROMETHEUS configuration, user and password with SSL - web.config.yml**:
```html
basic_auth_users:
    admin: $2a$12$N5gdOu3klRE.bEngaiI59.LHu4aFj2G3PVt5m9D9nMrY3.2nWrOoi
tls_server_config:
  cert_file: C:/ELCM/Certificates/prometheus/server-cert.pem
  key_file: C:/ELCM/Certificates/prometheus/server-key.pem
  client_ca_file: C:/ELCM/Certificates/prometheus/ca.pem
  client_auth_type: RequireAndVerifyClientCert
```

# TELEGRAF Configuration Guide

**TELEGRAF configuration, without SSL - telegraf.conf**:
```html
[[outputs.socket_writer]]
  ## Address and port to listen on for incoming messages
  address = "tcp://127.0.0.1:8094"
  data_format = "json" 
```

**TELEGRAF configuration, SSL - telegraf.conf**:
```html
[[outputs.socket_writer]]
  ## Address and port to listen on for incoming messages
  address = "tcp://127.0.0.1:8094"
  ## Optional TLS configuration
  tls_enable= true
  insecure_skip_verify = false
  tls_cert = "C:/ELCM/Certificates/telegraf/client-cert.pem"
  tls_key = "C:/ELCM/Certificates/telegraf/client-key.pem"
  tls_ca = "C:/ELCM/Certificates/telegraf/ca.pem"
  ## Optional settings
  data_format = "json" 
  ```