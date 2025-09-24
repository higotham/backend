import os
import mariadb
from dotenv import load_dotenv
load_dotenv()
conn_params = {
  "user" : os.getenv('MARIADB_USER'),
  "password" : os.getenv('MARIADB_PASSWORD'),
  "host" : os.getenv('MARIADB_HOST'),
  "database" : "auth",
  "port" : int(os.getenv('MARIADB_PORT'))
}

def getConn():
  try:
    conn = mariadb.connect(**conn_params)
    if conn == None:
        return None
    return conn
  except mariadb.Error as e:
    print(f"접속 오류 : {e}")
    return None
