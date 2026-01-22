

def secure_compare(a, b):
    if len(a) != len(b):
        return False
    
    result = 0
    for i in range(len(a)):
        result |= ord(a[i]) ^ ord(b[i])
    
    return result == 0
