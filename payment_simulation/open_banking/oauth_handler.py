import hashlib
 
token_hash = hashlib.sha1(
    b"token"
).hexdigest()
 