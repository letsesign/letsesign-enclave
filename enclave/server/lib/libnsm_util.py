from ctypes import *

nsm_lib = cdll.LoadLibrary("/usr/lib64/libnsm.so")


def nsm_lib_get_attestation_doc(user_data_bytes, pub_key_bytes):
    # initiate nsm libaray
    nsm_fd = nsm_lib.nsm_lib_init()
    user_data_len = 0 if user_data_bytes == None else len(user_data_bytes)
    pub_key_len = 0 if pub_key_bytes == None else len(pub_key_bytes)

    if user_data_len > 512:
        raise Exception("user data buffer too big")

    if pub_key_len > 1024:
        raise Exception("public key buffer too big")

    # allocate buffer for attestation document
    init_len = 16 * 1024 + user_data_len + pub_key_len
    attestation_doc_len = c_int(init_len)
    attestation_doc_buf = create_string_buffer(init_len)

    # call nsm library function to retrieve attestation document
    ret_val = nsm_lib.nsm_get_attestation_doc(nsm_fd, user_data_bytes, len(user_data_bytes) if user_data_bytes is not None else 0, None, 0, pub_key_bytes, len(
        pub_key_bytes) if pub_key_bytes is not None else 0, attestation_doc_buf, byref(attestation_doc_len))

    # release nsm library resource
    nsm_lib.nsm_lib_exit(nsm_fd)

    if ret_val != 0:
        raise Exception(
            f"nsm_get_attestation_doc return error code: {ret_val}")

    return attestation_doc_buf[:attestation_doc_len.value]
