from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
 
private_key = ec.generate_private_key(
    ec.SECP256R1()
)
 
signature = private_key.sign(
    b"payment-request",
    ec.ECDSA(hashes.SHA256())
)
 