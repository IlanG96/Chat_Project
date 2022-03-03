def checksum(buffer):
    nleft = len(buffer)
    sum = 0
    pos = 0
    while nleft > 1:
        sum = ord(buffer[pos]) * 256 + (ord(buffer[pos + 1]) + sum)
        pos = pos + 2
        nleft = nleft - 2
    if nleft == 1:
        sum = sum + ord(buffer[pos]) * 256

    sum = (sum >> 16) + (sum & 0xFFFF)
    sum += (sum >> 16)
    sum = (~sum & 0xFFFF)

    return sum

