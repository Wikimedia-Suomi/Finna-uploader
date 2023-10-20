def unsigned_to_signed(unsigned_num):
    """Convert an unsigned 64-bit integer to a signed 64-bit integer."""
    if unsigned_num >= 2**63:
        return unsigned_num - 2**64
    return unsigned_num


def signed_to_unsigned(signed_num):
    """Convert a signed 64-bit integer to an unsigned 64-bit integer."""
    if signed_num < 0:
        return signed_num + 2**64
    return signed_num
        

