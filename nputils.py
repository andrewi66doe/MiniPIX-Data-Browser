import numpy as np
from scipy.sparse import coo_matrix


def sparse_to_dense(data):
    data = np.array(data)

    if data.size == 0:
        return np.zeros((256, 256))

    x = data[:, 0]
    y = data[:, 1]
    values = data[:, 2]

    return coo_matrix((values, (x, y)), shape=(256, 256)).todense()