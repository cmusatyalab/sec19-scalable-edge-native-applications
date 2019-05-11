# (junjuew) ImageHash related functions are adapted from
# https://github.com/JohannesBuchner/imagehash
from __future__ import absolute_import, division, print_function
import numpy as np


def _binary_array_to_hex(arr):
    """
    internal function to make a hex string out of a binary array.
    """
    bit_string = ''.join(str(b) for b in 1 * arr.flatten())
    width = int(np.ceil(len(bit_string) / 4))
    return '{:0>{width}x}'.format(int(bit_string, 2), width=width)


class ImageHash(object):
    """
    Hash encapsulation. Can be used for dictionary keys and comparisons.
    """

    @classmethod
    def from_string(cls, hex_string):
        val = int(hex_string, base=16)
        binary_string = '{:b}'.format(val)
        binary_array = np.array([int(i) for i in binary_string])
        return ImageHash(binary_array)

    def __init__(self, binary_array):
        self.hash = binary_array

    def __str__(self):
        return _binary_array_to_hex(self.hash.flatten())

    def __repr__(self):
        return repr(self.hash)

    def __sub__(self, other):
        if other is None:
            raise TypeError('Other hash must not be None.')
        if self.hash.size != other.hash.size:
            raise TypeError('ImageHashes must be of the same shape.',
                            self.hash.shape, other.hash.shape)
        return np.count_nonzero(self.hash.flatten() != other.hash.flatten())

    def __eq__(self, other):
        if other is None:
            return False
        return np.array_equal(self.hash.flatten(), other.hash.flatten())

    def __ne__(self, other):
        if other is None:
            return False
        return not np.array_equal(self.hash.flatten(), other.hash.flatten())

    def __hash__(self):
        # this returns a 8 bit integer, intentionally shortening the information
        return sum([2**(i % 8) for i, v in enumerate(self.hash.flatten()) if v])


def phash(image, hash_size=8, highfreq_factor=4):
    """
    Perceptual Hash computation.

    Implementation follows http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html

    @image must be a opencv image
    """
    if hash_size < 2:
        raise ValueError("Hash size must be greater than or equal to 2")

    import cv2
    import scipy.fftpack
    img_size = hash_size * highfreq_factor
    # greyscale
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = cv2.resize(image, (img_size, img_size))
    dct = scipy.fftpack.dct(scipy.fftpack.dct(image, axis=0), axis=1)
    dctlowfreq = dct[:hash_size, :hash_size].flatten()
    # use average
    med = np.average(dctlowfreq[1:])
    # use median of DCT
    # med = np.median(dctlowfreq)
    diff = dctlowfreq > med
    return ImageHash(diff)


def resize_to_max_wh(img, max_wh):
    """Resize an image so that the max of width or height is less than max_wh."""
    import cv2
    if max(img.shape) > max_wh:
        resize_ratio = float(max_wh) / \
            max(img.shape[0], img.shape[1])
        img = cv2.resize(img, (0, 0), fx=resize_ratio,
                         fy=resize_ratio, interpolation=cv2.INTER_AREA)
