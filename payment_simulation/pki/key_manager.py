from cryptography.hazmat.primitives.asymmetric import rsa


def generate_pki_service_key():
    """
    Generates an RSA key for the synthetic PKI key-management service.
    """
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
