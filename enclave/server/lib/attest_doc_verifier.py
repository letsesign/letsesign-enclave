import cbor2
import datetime

from OpenSSL import crypto
from cose.keys import EC2Key
from cose.keys.curves import P384
from cose.messages.sign1message import Sign1Message

ROOT_CERT_PEM = '-----BEGIN CERTIFICATE-----\n\
MIICETCCAZagAwIBAgIRAPkxdWgbkK/hHUbMtOTn+FYwCgYIKoZIzj0EAwMwSTEL\n\
MAkGA1UEBhMCVVMxDzANBgNVBAoMBkFtYXpvbjEMMAoGA1UECwwDQVdTMRswGQYD\n\
VQQDDBJhd3Mubml0cm8tZW5jbGF2ZXMwHhcNMTkxMDI4MTMyODA1WhcNNDkxMDI4\n\
MTQyODA1WjBJMQswCQYDVQQGEwJVUzEPMA0GA1UECgwGQW1hem9uMQwwCgYDVQQL\n\
DANBV1MxGzAZBgNVBAMMEmF3cy5uaXRyby1lbmNsYXZlczB2MBAGByqGSM49AgEG\n\
BSuBBAAiA2IABPwCVOumCMHzaHDimtqQvkY4MpJzbolL//Zy2YlES1BR5TSksfbb\n\
48C8WBoyt7F2Bw7eEtaaP+ohG2bnUs990d0JX28TcPQXCEPZ3BABIeTPYwEoCWZE\n\
h8l5YoQwTcU/9KNCMEAwDwYDVR0TAQH/BAUwAwEB/zAdBgNVHQ4EFgQUkCW1DdkF\n\
R+eWw5b6cp3PmanfS5YwDgYDVR0PAQH/BAQDAgGGMAoGCCqGSM49BAMDA2kAMGYC\n\
MQCjfy+Rocm9Xue4YnwWmNJVA44fA0P5W2OpYow9OYCVRaEevL8uO1XYru5xtMPW\n\
rfMCMQCi85sWBbJwKKXdS6BptQFuZbT73o/gBh1qUxl/nNr12UO8Yfwr6wPLb+6N\n\
IwLz3/Y=\n\
-----END CERTIFICATE-----'

# following verificaiton process is based on
# https://github.com/aws/aws-nitro-enclaves-nsm-api/blob/bf5c9f2edb04ede2f5bbe1cb930d8d7c795bea8b/docs/attestation_process.md


def verify_attestation_doc(attestation_doc, verify_cert_in_signing_time=False):
    """
    Verify the attestation document
    If invalid, raise an exception
    """
    ################################
    # 3.2.1. COSE decode and validate signature operations
    ################################
    # Decode CBOR attestation document
    data = cbor2.loads(attestation_doc)

    # Load and decode document payload
    doc = data[2]
    doc_obj = cbor2.loads(doc)
    ################################
    # 3.2.2 Syntactical validation - Check if the required fields are present and check content
    ################################
    # module_id - Module ID must be non-empty
    if 'module_id' not in doc_obj or isinstance(doc_obj['module_id'], str) == False:
        raise Exception("invalid module_id")
    # digest -  Digest can be exactly one of these values, $value ∈ {"SHA384"}
    if 'digest' not in doc_obj or isinstance(doc_obj['digest'], str) == False or doc_obj['digest'] != 'SHA384':
        raise Exception("invalid digest")
    # timestamp - Timestamp must be greater than 0
    if 'timestamp' not in doc_obj or isinstance(doc_obj['timestamp'], int) == False or doc_obj['timestamp'] <= 0:
        raise Exception("invalid timestamp")
    # pcrs - verify with input pcrs
    if 'pcrs' not in doc_obj or isinstance(doc_obj['pcrs'], dict) == False or len(doc_obj['pcrs']) == 0:
        raise Exception("invalid pcrs")
    # cabundle - CA Bundle is not allowed to have 0 elements
    if 'cabundle' not in doc_obj or isinstance(doc_obj['cabundle'], list) == False or len(doc_obj['cabundle']) == 0:
        raise Exception("invalid cabundle")
    # public_key
    if 'public_key' not in doc_obj:
        raise Exception("invalid public_key")
    # user_data
    if 'user_data' not in doc_obj:
        raise Exception("invalid user_data")

    ################################
    # 3.2.3 Semantical validation - Certificates validity, Certificates critical extensions
    ################################
    cert = crypto.load_certificate(
        crypto.FILETYPE_ASN1, doc_obj['certificate'])
    # Certificates critical extensions: basic constraints
    # Certificates critical extensions: key usage
    if cert.get_extension_count() != 2:
        raise Exception("invalid certificate extension")
    hasBasicConstraints = False
    hasKeyUsage = False
    for idx in range(cert.get_extension_count()):
        if cert.get_extension(idx).get_short_name().decode() == 'basicConstraints':
            hasBasicConstraints = True
        if cert.get_extension(idx).get_short_name().decode() == 'keyUsage':
            hasKeyUsage = True
    if hasBasicConstraints == False or hasKeyUsage == False:
        raise Exception("invalid certificate extension")
    ################################
    # 3.2.4 Certificates chain
    ################################
    # Create an X509Store object for the CA bundles
    chain = []
    store = crypto.X509Store()
    if verify_cert_in_signing_time == True:
        # set signing time as check time
        store.set_time(datetime.datetime.fromtimestamp(
            doc_obj['timestamp'] / 1000))
    # Create the CA cert object from PEM string, and store into X509Store
    store.add_cert(crypto.load_certificate(crypto.FILETYPE_PEM, ROOT_CERT_PEM))

    # Get the CA bundle from attestation document and store into chain
    for _cert_asn1 in doc_obj['cabundle']:
        chain.append(crypto.load_certificate(
            crypto.FILETYPE_ASN1, _cert_asn1))
    # Get the X509Store context
    store_ctx = crypto.X509StoreContext(store, cert, chain=chain)

    # Validate the certificate
    # If the cert is invalid, it will raise exception
    store_ctx.verify_certificate()
    ################################
    # Validate signature
    ################################
    # Get the key parameters from the cert public key
    cert_public_numbers = cert.get_pubkey().to_cryptography_key().public_numbers()
    x = cert_public_numbers.x
    y = cert_public_numbers.y

    x = x.to_bytes((x.bit_length() + 7) // 8, 'big')
    y = y.to_bytes((y.bit_length() + 7) // 8, 'big')

    # Create the EC2 key from public key parameters
    key = EC2Key(crv=P384, x=x, y=y)

    # Get the protected header from attestation document
    phdr = cbor2.loads(data[0])

    # Construct the Sign1 message
    msg = Sign1Message(phdr=phdr, uhdr=data[1], payload=doc, key=key)
    msg._signature = data[3]

    # Verify the signature using the EC2 key
    if not msg.verify_signature():
        raise Exception("Wrong signature")

    # print("verify_attestation_doc success")
    return {
        'pcrs': doc_obj['pcrs'],
        'timestamp': doc_obj['timestamp'],
        'public_key': doc_obj['public_key'],
        'user_data': doc_obj['user_data']
    }
