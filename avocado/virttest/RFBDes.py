from virttest import utils_misc


class Des(object):

    """
    Base Data Encryption Standard class.
    For details, please refer to:
    http://en.wikipedia.org/wiki/Data_Encryption_Standard
    """
    # Permutation and translation tables for DES
    PC1 = [
        56, 48, 40, 32, 24, 16, 8,
        0, 57, 49, 41, 33, 25, 17,
        9, 1, 58, 50, 42, 34, 26,
        18, 10, 2, 59, 51, 43, 35,
        62, 54, 46, 38, 30, 22, 14,
        6, 61, 53, 45, 37, 29, 21,
        13, 5, 60, 52, 44, 36, 28,
        20, 12, 4, 27, 19, 11, 3
    ]

    # Number left rotations of pc1
    left_rotations = [
        1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1
    ]

    # get_sub_listd choice key (table 2)
    PC2 = [
        13, 16, 10, 23, 0, 4,
        2, 27, 14, 5, 20, 9,
        22, 18, 11, 3, 25, 7,
        15, 6, 26, 19, 12, 1,
        40, 51, 30, 36, 46, 54,
        29, 39, 50, 44, 32, 47,
        43, 48, 38, 55, 33, 52,
        45, 41, 49, 35, 28, 31
    ]

    # Initial permutation IP
    IP = [
        57, 49, 41, 33, 25, 17, 9, 1,
        59, 51, 43, 35, 27, 19, 11, 3,
        61, 53, 45, 37, 29, 21, 13, 5,
        63, 55, 47, 39, 31, 23, 15, 7,
        56, 48, 40, 32, 24, 16, 8, 0,
        58, 50, 42, 34, 26, 18, 10, 2,
        60, 52, 44, 36, 28, 20, 12, 4,
        62, 54, 46, 38, 30, 22, 14, 6
    ]

    # Expansion table for turning 32 bit blocks into 48 bits
    E = [
        31, 0, 1, 2, 3, 4,
        3, 4, 5, 6, 7, 8,
        7, 8, 9, 10, 11, 12,
        11, 12, 13, 14, 15, 16,
        15, 16, 17, 18, 19, 20,
        19, 20, 21, 22, 23, 24,
        23, 24, 25, 26, 27, 28,
        27, 28, 29, 30, 31, 0
    ]

    # The (in)famous S-boxes
    sbox = [
        # S1
        [14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7,
         0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8,
         4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0,
         15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13],

        # S2
        [15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10,
         3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5,
         0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15,
         13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9],

        # S3
        [10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8,
         13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1,
         13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7,
         1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12],

        # S4
        [7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15,
         13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9,
         10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4,
         3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14],

        # S5
        [2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9,
         14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6,
         4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14,
         11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3],

        # S6
        [12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11,
         10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8,
         9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6,
         4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13],

        # S7
        [4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1,
         13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6,
         1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2,
         6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12],

        # S8
        [13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7,
         1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2,
         7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8,
         2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11],
    ]

    # 32-bit permutation function P used on the output of the S-boxes
    P = [
        15, 6, 19, 20, 28, 11,
        27, 16, 0, 14, 22, 25,
        4, 17, 30, 9, 1, 7,
        23, 13, 31, 26, 2, 8,
        18, 12, 29, 5, 21, 10,
        3, 24
    ]

    # Final permutation IP^-1
    FP = [
        39, 7, 47, 15, 55, 23, 63, 31,
        38, 6, 46, 14, 54, 22, 62, 30,
        37, 5, 45, 13, 53, 21, 61, 29,
        36, 4, 44, 12, 52, 20, 60, 28,
        35, 3, 43, 11, 51, 19, 59, 27,
        34, 2, 42, 10, 50, 18, 58, 26,
        33, 1, 41, 9, 49, 17, 57, 25,
        32, 0, 40, 8, 48, 16, 56, 24
    ]

    # Initialisation
    def __init__(self, key):
        """
        Initialize the instance.

        :param key: Original used in DES.
        """
        if len(key) != 8:
            key = (key + '\0' * 8)[:8]

        self.L = []
        self.R = []
        self.Kn = [[0] * 48] * 16    # 16 48-bit keys (K1 - K16)

        self.setKey(key)

    def getKey(self):
        """
        Just get the crypting key.
        """
        return self.key

    def setKey(self, key):
        """
        Will set the crypting key for this object.
        RFB protocol for authentication requires client to encrypt
        challenge sent by server with password using DES method. However,
        bits in each byte of the password are put in reverse order before
        using it as encryption key.

        :param key: Original used in DES.
        """
        newkey = []
        for ki in range(len(key)):
            bsrc = ord(key[ki])
            btgt = 0
            for i in range(8):
                if bsrc & (1 << i):
                    btgt = btgt | (1 << 7 - i)

            newkey.append(chr(btgt))
        self.key = newkey
        self.create_Kn()

    def get_sub_list(self, table, block):
        """
        Return sub list of block according to index in table.

        :param table: Index list.
        :param block: bit list used to get sub list.
        """
        block_list = []
        for x in table:
            block_list.append(block[x])
        return block_list

    def create_Kn(self):
        """
        Create the 16 subkeys,from K[0] to K[15], from the given key
        """
        key = self.get_sub_list(
            self.PC1, utils_misc.string_to_bitlist(self.getKey()))
        self.L = key[:28]
        self.R = key[28:]
        for i in range(16):
            # Perform circular left shifts
            for j in range(self.left_rotations[i]):
                self.L.append(self.L[0])
                del self.L[0]
                self.R.append(self.R[0])
                del self.R[0]
            # Create one of the 16 subkeys through pc2 permutation
            self.Kn[i] = self.get_sub_list(self.PC2, self.L + self.R)

    def f(self, K):
        """
        The Feistel function (F-function) of DES, operates on half a block
        (32 bits) at a time and consists of four stages:
        1. Expansion
        2. Key mixing
        3. Substitution
        4. Permutation

        :param K: One of sixteen 48-bit subkeys are derived from the main key.
        """
        # Expansion:
        # The 32-bit half-block is expanded to 48 bits using E.
        self.R = self.get_sub_list(self.E, self.R)

        # Key mixing: The result is combined with a subkey using an XOR
        # operation. Sixteen 48-bit subkeys are derived from the main key.
        self.R = list(map(lambda x, y: x ^ y, self.R, K))

        # The block is divided into eight 6-bit pieces
        B = [self.R[:6], self.R[6:12], self.R[12:18], self.R[18:24],
             self.R[24:30], self.R[30:36], self.R[36:42], self.R[42:]]

        # Substitution:
        Bn = [0] * 32
        pos = 0
        for j in range(8):
            # Work out the offsets
            m = (B[j][0] << 1) + B[j][5]
            n = (B[j][1] << 3) + (B[j][2] << 2) + (B[j][3] << 1) + B[j][4]

            # Find the permutation value
            v = self.sbox[j][(m << 4) + n]

            # Turn value into bits, add it to result: Bn
            Bn[pos] = (v & 8) >> 3
            Bn[pos + 1] = (v & 4) >> 2
            Bn[pos + 2] = (v & 2) >> 1
            Bn[pos + 3] = v & 1

            pos += 4

        # Permutation:
        # Bn are rearranged according to a fixed permutation, the P-box.
        self.R = self.get_sub_list(self.P, Bn)

    def des_crypt(self, data, crypt_type=0):
        """
        Crypt the block of data through DES bit-manipulation

        :param data: data need to crypt.
        :param crypt_type: crypt type. 0 means encrypt, and 1 means decrypt.
        """
        # Get new block by using Ip.
        block = self.get_sub_list(self.IP, data)
        self.L = block[:32]
        self.R = block[32:]

        if crypt_type == 0:
            des_i = 0
            des_adj = 1
        else:
            des_i = 15
            des_adj = -1

        i = 0
        while i < 16:
            tempR = self.R
            self.f(self.Kn[des_i])

            # Xor with L[i - 1]
            self.R = list(map(lambda x, y: x ^ y, self.R, self.L))
            # Optimization: This now replaces the below commented code
            self.L = tempR

            i += 1
            des_i += des_adj

        # Final permutation of R[16]L[16]
        final = self.get_sub_list(self.FP, self.R + self.L)
        return final

    def crypt(self, data, crypt_type=0):
        """
        Crypt the data in blocks, running it through des_crypt()

        :param data: Data to be encrypted/decrypted.
        :param crypt_type: crypt type. 0 means encrypt, and 1 means decrypt.
        """

        # Split the data into list, crypting each one separately
        i = 0
        result = []
        while i < len(data):
            # Test code for caching encryption results
            block = utils_misc.string_to_bitlist(data[i:i + 8])
            pro_block = self.des_crypt(block, crypt_type)

            # Add the resulting block to our list
            result.append(utils_misc.bitlist_to_string(pro_block))
            i += 8

        # Return the full encrypted/decrypted string
        return ''.join(result)
