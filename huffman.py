import marshal
import os
import pickle
import sys
import operator
from array import array
from typing import Dict
from typing import Tuple

#####################################################################################
# INVARIANTS:
#
# In a proper Huffman tree, the least frequent characters will always be at 
#    the greatest depths of said tree
#
# Initialization: The Huffman tree has no values stored in it on intialization
#     so the invariant is trivially true.
#
# Maintenance: The tree is built by adding the two lowest values at a time, starting
#     from the leaf nodes, any nodes that appear more frequently will be pushed up a 
#     level. Because the tree is built using the lowest frequencies, and building
#     up from the leaves, the invariant holds.
#
# Termination: Once the tree has been fully built, due to our maintenance of the tree, 
#     the highest frequency characters have the shortest codes as they were inserted 
#     into the tree last, and the lowest frequency characters remain deeper in
#     the tree which is the invarient stated above.
#####################################################################################



#####################################################################################
# This function will take in a stream of bytes and store unique ones and their 
# frequencies, it will create a list of tuples formated as (byte, frequency)
# makeFreqList(data) returns the list of tuples in sorted (backwards) order
#####################################################################################
def makeFreqList(data):
    #manage the input data
    byte_arr = array('B', data)
    #create a dictionary to store characters with frequncies
    freq_dict = {}
    #this will be the final list of tuples that we are returning
    final = []

    #populate the dictionary and pair with the frequencies of each byte
    for c in byte_arr:
        if c in freq_dict:
            freq_dict[c] = freq_dict[c] + 1
        else:
            freq_dict[c] = 1

    #insert each byte/frequency tuple into the final list
    for b, f in freq_dict.items():
        temp = (b, f)
        final.append(temp)
    
    #sort the list and return it
    final.sort(key=operator.itemgetter(0))

    return final


#####################################################################################
# Takes a digit, left shifts it, and adds that digit to the buffer
#####################################################################################
def leftShift(buffer, digit):
    if digit == '1':
        buffer = (buffer << 1) | 1
    else:
        buffer = (buffer << 1)
    return buffer

#####################################################################################
# This function performs an inorder traversal of the tree
# We use it to generate the binary representation of each char
#####################################################################################
def makeString(tree, val, result):
    #check if we've reached the end
    if isinstance(tree[0], tuple):
        #recurse right and left
        r = makeString(tree[0][1], val, result + '1')
        l = makeString(tree[0][0], val, result + '0')

        #choose whether we return right or left
        if r[len(r) - 1] == 'g':
            return r
        elif l[len(l) - 1] == 'g':
            return l
        else:
            return l
    #we reached the end
    else:
        if tree[0] == val:
            return result + 'g'
        else:
            return result + 'b'

#####################################################################################
# Generate codes will create the unique x-bit code for each char, and store it in a 
# dictionary with the byte as the key, and the code as the value.
# genCodes(t_list) returns said dictionary.
#####################################################################################
def genCodes(t_list):
    #create the tree
    #make a copy to build up the tree
    tree = t_list.copy()

    #Build the tree
    while len(tree) > 1:
        #grab the smallest 2 elements from the sorted list
        sub = ((tree[0], tree[1]), tree[0][1] + tree[1][1])
        del tree[:2]

        #insert the nodes into the tree
        i = 0
        while i < len(tree) and tree[i][1] < sub[1]:
                i += 1
        tree.insert(i, sub)
    #make dictionary for bytes and codes
    final = {}
    for t in t_list:
        temp = makeString(tree[0], t[0], "")
        #this next line is apparently very important
        temp = temp[:-1]
        final[t[0]] = temp

    return final

def encode(message: bytes) -> Tuple[str, Dict]:
    """ Given the bytes read from a file, encodes the contents using the Huffman encoding algorithm.

    :param message: raw sequence of bytes from a file
    :returns: string of 1s and 0s representing the encoded message
              dict containing the decoder ring as explained in lecture and handout.
    """
    freq_list = makeFreqList(message)
    ring = genCodes(freq_list)
    encode_str = ""
    #manage input, put into string
    for c in message:
        encode_str += ring[c]
    
    decode_dict = {}
    #reverse the ring for decoding
    for key, val in ring.items():
        decode_dict[val] = key

    return (encode_str, decode_dict)


def decode(message: str, decoder_ring: Dict) -> bytes:
    """ Given the encoded string and the decoder ring, decodes the message using the Huffman decoding algorithm.

    :param message: string of 1s and 0s representing the encoded message
    :param decoder_ring: dict containing the decoder ring
    return: raw sequence of bytes that represent a decoded file
    """
    final = temp = ""
    temp_set = set(decoder_ring.keys())
    #loop through the message
    for c in message:
        temp += c
        #check if temp is ready for the final string
        if temp in temp_set:
            final += chr(decoder_ring[temp])
            temp = ""

    return final.encode('utf-8')


def compress(message: bytes) -> Tuple[array, Dict]:
    """ Given the bytes read from a file, calls encode and turns the string into an array of bytes to be written to disk.

    :param message: raw sequence of bytes from a file
    :returns: array of bytes to be written to disk
              dict containing the decoder ring
    """
    #initializes an array to hold the compressed message.
    compressed_arr = array('B')
    #call encode and handle, comes in as (binary message ; code dictionary {code:character})
    encode_str, ring_dict = encode(message)

    #how much do we have to pad (if at all)
    pad = (len(encode_str) % 8)

    #check if we need padding
    if pad != 0:
        pad_size = 8 - pad
    else:
        pad_size = 0
    #add the padding to the dictionary with key "PAD"
    ring_dict["PAD"] = pad_size
    
    #initialize variables for bytes
    buff = 0
    temp = 0
    i = 0

    #handle the special cases (first byte and padding) and do the rest
    while i < len(encode_str):
        buff = leftShift(buff, encode_str[i])
        temp += 1
        i += 1
        if temp >= 8:
            compressed_arr.append(buff)
            buff = 0
            temp = 0
    if temp != 0:
        buff = (buff << pad_size)
    compressed_arr.append(buff)
    
    return (compressed_arr, ring_dict)


def decompress(message: array, decoder_ring: Dict) -> bytes:
    """ Given a decoder ring and an array of bytes read from a compressed file, turns the array into a string and calls decode.

    :param message: array of bytes read in from a compressed file
    :param decoder_ring: dict containing the decoder ring
    :return: raw sequence of bytes that represent a decompressed file
    """
    #handle input and create the final array
    byte_array = array('B',message)
    final = array('B')

    #make a string of all the bits and set up variables for the decompress
    byte_str = ""
    pad = 0
    count = 1
    for byte in byte_array:
        #if we're at the end, get padding ready
        if count == len(byte_array):
            pad = decoder_ring["PAD"]

        #loop and do work on byte
        for i in range(8 - pad):
            if (byte & 128):
                byte_str += '1'
            else:
                byte_str += '0'
            byte = (byte << 1)
            
            if byte_str in decoder_ring:
                final.append(decoder_ring[byte_str])
                byte_str = ""

        count += 1

    return final


if __name__ == '__main__':
    usage = f'Usage: {sys.argv[0]} [ -c | -d | -v | -w ] infile outfile'
    if len(sys.argv) != 4:
        raise Exception(usage)

    operation = sys.argv[1]
    if operation not in {'-c', '-d', '-v', 'w'}:
        raise Exception(usage)

    infile, outfile = sys.argv[2], sys.argv[3]
    if not os.path.exists(infile):
        raise FileExistsError(f'{infile} does not exist.')

    if operation in {'-c', '-v'}:
        with open(infile, 'rb') as fp:
            _message = fp.read()

        if operation == '-c':
            _message, _decoder_ring = compress(_message)
            with open(outfile, 'wb') as fp:
                marshal.dump((pickle.dumps(_decoder_ring), _message), fp)
        else:
            _message, _decoder_ring = encode(_message)
            print(_message)
            with open(outfile, 'wb') as fp:
                marshal.dump((pickle.dumps(_decoder_ring), _message), fp)

    else:
        with open(infile, 'rb') as fp:
            pickleRick, _message = marshal.load(fp)
            _decoder_ring = pickle.loads(pickleRick)

        if operation == '-d':
            bytes_message = decompress(array('B', _message), _decoder_ring)
        else:
            bytes_message = decode(_message, _decoder_ring)
        with open(outfile, 'wb') as fp:
            fp.write(bytes_message)
