import os
import requests
from jose import jwt, JWTError
from fastapi import status, Header, HTTPException
from dotenv import load_dotenv
load_dotenv()

JWKS_URL = os.getenv("JWKS_URL")
ALGORITHM = os.getenv("ALGORITHM")
jwks_cache = None

def get_jwks():
  global jwks_cache
  if jwks_cache is None:
    resp = requests.get(JWKS_URL)
    resp.raise_for_status()
    jwks_cache = resp.json()
  return jwks_cache

def get_current(authorization: str = Header(None)):
  if not authorization or not authorization.startswith(f"{os.getenv("TOKEN_TYPE")} "):
    raise HTTPException(status_code=401, detail="Missing token")
  
  token = authorization.split(" ")[1]
  jwks = get_jwks()
  kid = os.getenv("KID")
  key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
  if not key:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Public key not found")
  
  try:
    payload = jwt.decode(token, key, algorithms=[ALGORITHM])
    return payload
  except JWTError:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
