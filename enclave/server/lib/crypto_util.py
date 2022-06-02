import os
import logging
import traceback

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import padding as primitives_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding as asymmetric_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def gen_rsa_key(bits):
    try:
        prv_key_obj = rsa.generate_private_key(
            public_exponent=65537, key_size=bits)
        prv_key_pem = prv_key_obj.private_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()).decode("utf-8")

        return prv_key_pem
    except BaseException as e:
        logging.error(traceback.format_exc())

    return None


def derive_pub_key(prv_key_pem, is_pem):
    try:
        prv_key_obj = serialization.load_pem_private_key(
            prv_key_pem.encode("utf-8"), password=None)
        pub_key_obj = prv_key_obj.public_key()

        if is_pem:
            return pub_key_obj.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
        else:
            return pub_key_obj.public_bytes(encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo)
    except BaseException as e:
        logging.error(traceback.format_exc())

    return None


def rsa_decrypt_data(prv_key_pem, encrypted_data_bytes):
    try:
        prv_key_obj = serialization.load_pem_private_key(
            prv_key_pem.encode("utf-8"), password=None)
        decrypted_data_bytes = prv_key_obj.decrypt(encrypted_data_bytes, asymmetric_padding.OAEP(
            mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))

        return decrypted_data_bytes
    except BaseException as e:
        logging.error(traceback.format_exc())

    return None


def aes_cbc_encrypt_data(aes_key_bytes, iv_bytes, origin_data_bytes):
    try:
        cipher = Cipher(algorithms.AES(aes_key_bytes), modes.CBC(iv_bytes))
        padder = primitives_padding.PKCS7(128).padder()
        padded_data = padder.update(origin_data_bytes) + padder.finalize()
        encryptor = cipher.encryptor()
        encrypted_data_bytes = encryptor.update(
            padded_data) + encryptor.finalize()

        return encrypted_data_bytes
    except BaseException as e:
        logging.error(traceback.format_exc())

    return None


def aes_cbc_decrypt_data(aes_key_bytes, iv_bytes, encrypted_data_bytes):
    try:
        cipher = Cipher(algorithms.AES(aes_key_bytes), modes.CBC(iv_bytes))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(
            encrypted_data_bytes) + decryptor.finalize()
        unpadder = primitives_padding.PKCS7(128).unpadder()
        decrypted_data_bytes = unpadder.update(
            padded_data) + unpadder.finalize()

        return decrypted_data_bytes
    except BaseException as e:
        logging.error(traceback.format_exc())

    return None


def gen_random_bytes(size):
    return os.urandom(size)
