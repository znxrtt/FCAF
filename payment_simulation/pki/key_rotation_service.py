from cryptography.hazmat.primitives.asymmetric import rsa


def generate_rotated_certificate_key():
    """
    Generates a replacement RSA key during a controlled
    certificate-key rotation in the synthetic PKI environment.
    """
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
