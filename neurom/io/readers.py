''' Module for morphology data loading and access'''
import os
from collections import defaultdict
from collections import namedtuple
from itertools import imap
import numpy as np

# SWC n, T, x, y, z, R, P
(ID, TYPE, X, Y, Z, R, P) = xrange(7)

ROOT_ID = -1

def read_swc(filename):
    '''Read an SWC file and return a tuple of data, offset, format.'''
    data = np.loadtxt(filename)
    offset = data[0][ID]
    return data, offset, 'SWC'

_READERS = {'swc': read_swc}


def unpack_data(filename):
    '''Read an SWC file and return a tuple of data, offset, format.
    Forwards filename to appropriate reader depending on extension'''
    extension = os.path.splitext(filename)[1][1:]
    return _READERS[extension.lower()](filename)


def load_data(filename):
    '''Unpack filename and return a RawDataWrapper object containing the data

    Determines format from extension. Currently supported:

        * SWC (case-insensitive extension ".swc")
    '''
    return RawDataWrapper(unpack_data(filename))


Point = namedtuple('Point', ('t', 'x', 'y', 'z', 'r'))


def point_from_row(row):
    '''Create a point from a data block row'''
    return Point(*row[TYPE:P])


class RawDataWrapper(object):
    '''Class holding an array of data and an offset to the first element
    and giving basic access to its elements

    The array contains rows with
        [ID, TYPE, X, Y, Z, R, P]

    where the elements are

    * ID: Identifier for a point. Non-negative, increases by one for each row.
    * TYPE: Type of neuronal segment.
    * X, Y, Z: X, Y, Z coorsinates of point
    * R: Radius of node at that point
    * P: ID of parent point
    '''
    def __init__(self, raw_data):
        self.data_block, self._offset, self.fmt = raw_data
        self.adj_list = defaultdict(list)
        for row in self.data_block:
            self.adj_list[int(row[P])].append(int(row[ID]))

    def get_children(self, idx):
        ''' get list of ids of children of parent with id idx'''
        if idx != ROOT_ID and idx not in self.get_ids():
            raise LookupError('Invalid id: {}'.format(idx))
        return self.adj_list[idx]

    def _apply_offset(self, idx):
        ''' Apply global offset to an id'''
        return idx - self._offset

    def get_parent(self, idx):
        '''get the parent of element with id idx'''
        if idx not in self.get_ids():
            raise LookupError('Invalid id: {}'.format(idx))
        return int(self.data_block[self._apply_offset(idx)][P])

    def get_point(self, idx):
        '''Get point data for element idx'''
        idx = self._apply_offset(idx)
        p = point_from_row(self.data_block[idx]) if idx > ROOT_ID else None
        return p

    def get_end_points(self):
        ''' get the end points of the tree

        End points have no children so are not in the
        adjacency list.
        '''
        return [int(i) for i in
                set(self.data_block[:, ID]) - set(self.adj_list.keys())]

    def get_ids(self):
        '''Get the list of ids'''
        return list(self.data_block[:, ID])

    def get_fork_points(self):
        '''Get list of point ids for points with more than one child'''
        return [i for i, l in self.adj_list.iteritems() if len(l) > 1]

    def iter_points(self, start_id=None):
        '''Get an iterator starting at start_id

        Iterator de-references to a Point object.
        '''
        if start_id is None:
            start_id = self._offset

        start_id = self._apply_offset(start_id)
        if start_id < 0 or start_id >= self.data_block.shape[0]:
            raise LookupError('Invalid id: {}'.format(start_id))

        return imap(point_from_row,
                    iter(self.data_block[start_id:]))