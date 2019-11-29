import numpy as np
from scipy.spatial import distance as dist


def order_points(points):
    """
    Order points of a bounding box such that the order of points is always
    [topleft, topright, bottomright, bottomleft].

    :param points:
    :return:
    """
    # This should only accept values with exactly four points.
    assert (len(points) == 4)

    # Sort by x-values first
    x_sorted = points[np.argsort(points[:, 0]), :]

    # Retrieve leftmost  and rightmost x-values
    left_most = x_sorted[:2, :]
    right_most = x_sorted[2:, :]

    # Determine top-left and bottom-left points by sorting y-values
    left_most = left_most[np.argsort(left_most[:, 1]), :]
    tl, bl = left_most

    # Determine bottom-right point by sorting by euclidean distance from top-left.
    d = dist.cdist(tl[np.newaxis], right_most, "euclidean")[0]
    br, tr = right_most[np.argsort(d)[::-1], :]

    return np.array([tl, tr, br, bl], dtype="float32")


def is_between_scalar(a, b, val):
    """
    Check if val is between a and b.

    :param a:
    :param b:
    :param val:
    :return:
    """
    b = round(b, 4)
    a = round(a, 4)
    val = round(val, 4)

    if a < b:
        return a <= val <= b
    if a > b:
        return a >= val >= b
    if a == b:
        return a == val or b == val


def is_between(p, p1, p2):
    """
    Check if point p lies within the rect defined by p1 and p2.

    :param p:
    :param p1:
    :param p2:
    :return:
    """
    x, y = p
    x1, y1 = p1
    x2, y2 = p2

    return is_between_scalar(x1, x2, x) and is_between_scalar(y1, y2, y)


def lineq(p1, p2):
    """
    Calculate the slope and y-intercept of a line given two points.

    :param p1:
    :param p2:
    :return:
    """
    x1, y1 = p1
    x2, y2 = p2

    if x2 - x1 == 0:
        m = np.inf
        c = x1
        return m, c

    m = (y2 - y1) / (x2 - x1)
    c = y1 - m * x1

    return m, c


def line_intersect(p1, p2, m, c):
    """
    Return the point of intersection between the line between p1 and p2  and the linear
    equation defined by y=mx + c. If the lines do not intersect then return None.

    :param p1:
    :param p2:
    :param m:
    :param c:
    :return:
    """
    m1, c1 = lineq(p1, p2)

    # Explicitly handle case of vertical line
    if np.isinf(m1):
        x, y = p1
        return x, m * x + c

    if m - m1 == 0:
        return None

    x = (c1 - c) / (m - m1)
    y = m * ((c1 - c) / (m - m1)) + c

    if is_between([x, y], p1, p2):
        return np.array([x, y])
    return None


def intersections_with_bbox(boxpoints, m, c):
    """
    Return the points of intersection between the bounding box defined by boxpoints and the
    linear equation defined by y=mx+c.

    :param boxpoints:
    :param m:
    :param c:
    :return:
    """
    intersections = []

    p1, p2, p3, p4 = boxpoints

    intersections.append(line_intersect(p1, p2, m, c))
    intersections.append(line_intersect(p2, p3, m, c))
    intersections.append(line_intersect(p3, p4, m, c))
    intersections.append(line_intersect(p4, p1, m, c))

    intersections = np.array(list(filter(lambda p: p is not None, intersections)))

    # Choose points that maximize euclidean distance if there are more than 2 intersections
    if len(intersections) > 2:
        e_distance = dist.cdist(intersections, intersections, 'euclidean')
        i1, i2 = np.unravel_index(np.argmax(e_distance), e_distance.shape)
        intersections = [intersections[i1],
                         intersections[i2]]

    return intersections
