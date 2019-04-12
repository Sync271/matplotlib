"""
A module providing some utility functions regarding bezier path manipulation.
"""

import numpy as np

import matplotlib.cbook as cbook
from matplotlib.path import Path


class NonIntersectingPathException(ValueError):
    pass

# some functions


def get_intersection(cx1, cy1, cos_t1, sin_t1,
                     cx2, cy2, cos_t2, sin_t2):
    """
    Return the intersection between the line through (*cx1*, *cy1*) at angle
    *t1* and the line through (*cx2, cy2) at angle *t2*.
    """

    # line1 => sin_t1 * (x - cx1) - cos_t1 * (y - cy1) = 0.
    # line1 => sin_t1 * x + cos_t1 * y = sin_t1*cx1 - cos_t1*cy1

    line1_rhs = sin_t1 * cx1 - cos_t1 * cy1
    line2_rhs = sin_t2 * cx2 - cos_t2 * cy2

    # rhs matrix
    a, b = sin_t1, -cos_t1
    c, d = sin_t2, -cos_t2

    ad_bc = a * d - b * c
    if np.abs(ad_bc) < 1.0e-12:
        raise ValueError("Given lines do not intersect. Please verify that "
                         "the angles are not equal or differ by 180 degrees.")

    # rhs_inverse
    a_, b_ = d, -b
    c_, d_ = -c, a
    a_, b_, c_, d_ = [k / ad_bc for k in [a_, b_, c_, d_]]

    x = a_ * line1_rhs + b_ * line2_rhs
    y = c_ * line1_rhs + d_ * line2_rhs

    return x, y


def get_normal_points(cx, cy, cos_t, sin_t, length):
    """
    For a line passing through (*cx*, *cy*) and having a angle *t*, return
    locations of the two points located along its perpendicular line at the
    distance of *length*.
    """

    if length == 0.:
        return cx, cy, cx, cy

    cos_t1, sin_t1 = sin_t, -cos_t
    cos_t2, sin_t2 = -sin_t, cos_t

    x1, y1 = length * cos_t1 + cx, length * sin_t1 + cy
    x2, y2 = length * cos_t2 + cx, length * sin_t2 + cy

    return x1, y1, x2, y2


# BEZIER routines

# subdividing bezier curve
# http://www.cs.mtu.edu/~shene/COURSES/cs3621/NOTES/spline/Bezier/bezier-sub.html


def _de_casteljau1(beta, t):
    next_beta = beta[:-1] * (1 - t) + beta[1:] * t
    return next_beta


def split_de_casteljau(beta, t):
    """
    Split a bezier segment defined by its control points *beta* into two
    separate segments divided at *t* and return their control points.
    """
    beta = np.asarray(beta)
    beta_list = [beta]
    while True:
        beta = _de_casteljau1(beta, t)
        beta_list.append(beta)
        if len(beta) == 1:
            break
    left_beta = [beta[0] for beta in beta_list]
    right_beta = [beta[-1] for beta in reversed(beta_list)]

    return left_beta, right_beta


@cbook._rename_parameter("3.1", "tolerence", "tolerance")
def find_bezier_t_intersecting_with_closedpath(
        bezier_point_at_t, inside_closedpath, t0=0., t1=1., tolerance=0.01):
    """ Find a parameter t0 and t1 of the given bezier path which
    bounds the intersecting points with a provided closed
    path(*inside_closedpath*). Search starts from *t0* and *t1* and it
    uses a simple bisecting algorithm therefore one of the end point
    must be inside the path while the other doesn't. The search stop
    when |t0-t1| gets smaller than the given tolerance.
    value for

    - bezier_point_at_t : a function which returns x, y coordinates at *t*

    - inside_closedpath : return True if the point is inside the path

    """
    # inside_closedpath : function

    start = bezier_point_at_t(t0)
    end = bezier_point_at_t(t1)

    start_inside = inside_closedpath(start)
    end_inside = inside_closedpath(end)

    if start_inside == end_inside and start != end:
        raise NonIntersectingPathException(
            "Both points are on the same side of the closed path")

    while True:

        # return if the distance is smaller than the tolerance
        if np.hypot(start[0] - end[0], start[1] - end[1]) < tolerance:
            return t0, t1

        # calculate the middle point
        middle_t = 0.5 * (t0 + t1)
        middle = bezier_point_at_t(middle_t)
        middle_inside = inside_closedpath(middle)

        if start_inside ^ middle_inside:
            t1 = middle_t
            end = middle
            end_inside = middle_inside
        else:
            t0 = middle_t
            start = middle
            start_inside = middle_inside


class BezierSegment(object):
    """
    A simple class of a 2-dimensional bezier segment
    """

    # Higher order bezier lines can be supported by simplying adding
    # corresponding values.
    _binom_coeff = {1: np.array([1., 1.]),
                    2: np.array([1., 2., 1.]),
                    3: np.array([1., 3., 3., 1.])}

    def __init__(self, control_points):
        """
        *control_points* : location of contol points. It needs have a
         shape of n * 2, where n is the order of the bezier line. 1<=
         n <= 3 is supported.
        """
        _o = len(control_points)
        self._orders = np.arange(_o)

        _coeff = BezierSegment._binom_coeff[_o - 1]
        xx, yy = np.asarray(control_points).T
        self._px = xx * _coeff
        self._py = yy * _coeff

    def point_at_t(self, t):
        "evaluate a point at t"
        tt = ((1 - t) ** self._orders)[::-1] * t ** self._orders
        _x = np.dot(tt, self._px)
        _y = np.dot(tt, self._py)
        return _x, _y


@cbook._rename_parameter("3.1", "tolerence", "tolerance")
def split_bezier_intersecting_with_closedpath(
        bezier, inside_closedpath, tolerance=0.01):

    """
    bezier : control points of the bezier segment
    inside_closedpath : a function which returns true if the point is inside
                        the path
    """

    bz = BezierSegment(bezier)
    bezier_point_at_t = bz.point_at_t

    t0, t1 = find_bezier_t_intersecting_with_closedpath(
        bezier_point_at_t, inside_closedpath, tolerance=tolerance)

    _left, _right = split_de_casteljau(bezier, (t0 + t1) / 2.)
    return _left, _right


@cbook.deprecated("3.1")
@cbook._rename_parameter("3.1", "tolerence", "tolerance")
def find_r_to_boundary_of_closedpath(
        inside_closedpath, xy, cos_t, sin_t, rmin=0., rmax=1., tolerance=0.01):
    """
    Find a radius r (centered at *xy*) between *rmin* and *rmax* at
    which it intersect with the path.

    inside_closedpath : function
    cx, cy : center
    cos_t, sin_t : cosine and sine for the angle
    rmin, rmax :
    """

    cx, cy = xy

    def _f(r):
        return cos_t * r + cx, sin_t * r + cy

    find_bezier_t_intersecting_with_closedpath(
        _f, inside_closedpath, t0=rmin, t1=rmax, tolerance=tolerance)

# matplotlib specific


@cbook._rename_parameter("3.1", "tolerence", "tolerance")
def split_path_inout(path, inside, tolerance=0.01, reorder_inout=False):
    """ divide a path into two segment at the point where inside(x, y)
    becomes False.
    """

    path_iter = path.iter_segments()

    ctl_points, command = next(path_iter)
    begin_inside = inside(ctl_points[-2:])  # true if begin point is inside

    ctl_points_old = ctl_points

    concat = np.concatenate

    iold = 0
    i = 1

    for ctl_points, command in path_iter:
        iold = i
        i += len(ctl_points) // 2
        if inside(ctl_points[-2:]) != begin_inside:
            bezier_path = concat([ctl_points_old[-2:], ctl_points])
            break
        ctl_points_old = ctl_points
    else:
        raise ValueError("The path does not intersect with the patch")

    bp = bezier_path.reshape((-1, 2))
    left, right = split_bezier_intersecting_with_closedpath(
        bp, inside, tolerance)
    if len(left) == 2:
        codes_left = [Path.LINETO]
        codes_right = [Path.MOVETO, Path.LINETO]
    elif len(left) == 3:
        codes_left = [Path.CURVE3, Path.CURVE3]
        codes_right = [Path.MOVETO, Path.CURVE3, Path.CURVE3]
    elif len(left) == 4:
        codes_left = [Path.CURVE4, Path.CURVE4, Path.CURVE4]
        codes_right = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]
    else:
        raise AssertionError("This should never be reached")

    verts_left = left[1:]
    verts_right = right[:]

    if path.codes is None:
        path_in = Path(concat([path.vertices[:i], verts_left]))
        path_out = Path(concat([verts_right, path.vertices[i:]]))

    else:
        path_in = Path(concat([path.vertices[:iold], verts_left]),
                       concat([path.codes[:iold], codes_left]))

        path_out = Path(concat([verts_right, path.vertices[i:]]),
                        concat([codes_right, path.codes[i:]]))

    if reorder_inout and not begin_inside:
        path_in, path_out = path_out, path_in

    return path_in, path_out


def inside_circle(cx, cy, r):
    r2 = r ** 2

    def _f(xy):
        x, y = xy
        return (x - cx) ** 2 + (y - cy) ** 2 < r2
    return _f


# quadratic bezier lines

def get_cos_sin(x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    d = (dx * dx + dy * dy) ** .5
    # Account for divide by zero
    if d == 0:
        return 0.0, 0.0
    return dx / d, dy / d


@cbook._rename_parameter("3.1", "tolerence", "tolerance")
def check_if_parallel(dx1, dy1, dx2, dy2, tolerance=1.e-5):
    """ returns
       * 1 if two lines are parallel in same direction
       * -1 if two lines are parallel in opposite direction
       * 0 otherwise
    """
    theta1 = np.arctan2(dx1, dy1)
    theta2 = np.arctan2(dx2, dy2)
    dtheta = np.abs(theta1 - theta2)
    if dtheta < tolerance:
        return 1
    elif np.abs(dtheta - np.pi) < tolerance:
        return -1
    else:
        return False


def get_parallels(bezier2, width):
    """
    Given the quadratic bezier control points *bezier2*, returns
    control points of quadratic bezier lines roughly parallel to given
    one separated by *width*.
    """

    # The parallel bezier lines are constructed by following ways.
    #  c1 and c2 are control points representing the begin and end of the
    #  bezier line.
    #  cm is the middle point

    c1x, c1y = bezier2[0]
    cmx, cmy = bezier2[1]
    c2x, c2y = bezier2[2]

    parallel_test = check_if_parallel(c1x - cmx, c1y - cmy,
                                      cmx - c2x, cmy - c2y)

    if parallel_test == -1:
        cbook._warn_external(
            "Lines do not intersect. A straight line is used instead.")
        cos_t1, sin_t1 = get_cos_sin(c1x, c1y, c2x, c2y)
        cos_t2, sin_t2 = cos_t1, sin_t1
    else:
        # t1 and t2 is the angle between c1 and cm, cm, c2.  They are
        # also a angle of the tangential line of the path at c1 and c2
        cos_t1, sin_t1 = get_cos_sin(c1x, c1y, cmx, cmy)
        cos_t2, sin_t2 = get_cos_sin(cmx, cmy, c2x, c2y)

    # find c1_left, c1_right which are located along the lines
    # through c1 and perpendicular to the tangential lines of the
    # bezier path at a distance of width. Same thing for c2_left and
    # c2_right with respect to c2.
    c1x_left, c1y_left, c1x_right, c1y_right = (
        get_normal_points(c1x, c1y, cos_t1, sin_t1, width)
    )
    c2x_left, c2y_left, c2x_right, c2y_right = (
        get_normal_points(c2x, c2y, cos_t2, sin_t2, width)
    )

    # find cm_left which is the intersecting point of a line through
    # c1_left with angle t1 and a line through c2_left with angle
    # t2. Same with cm_right.
    if parallel_test != 0:
        # a special case for a straight line, i.e., angle between two
        # lines are smaller than some (arbitrary) value.
        cmx_left, cmy_left = (
            0.5 * (c1x_left + c2x_left), 0.5 * (c1y_left + c2y_left)
        )
        cmx_right, cmy_right = (
            0.5 * (c1x_right + c2x_right), 0.5 * (c1y_right + c2y_right)
        )
    else:
        cmx_left, cmy_left = get_intersection(c1x_left, c1y_left, cos_t1,
                                              sin_t1, c2x_left, c2y_left,
                                              cos_t2, sin_t2)

        cmx_right, cmy_right = get_intersection(c1x_right, c1y_right, cos_t1,
                                                sin_t1, c2x_right, c2y_right,
                                                cos_t2, sin_t2)

    # the parallel bezier lines are created with control points of
    # [c1_left, cm_left, c2_left] and [c1_right, cm_right, c2_right]
    path_left = [(c1x_left, c1y_left),
                 (cmx_left, cmy_left),
                 (c2x_left, c2y_left)]
    path_right = [(c1x_right, c1y_right),
                  (cmx_right, cmy_right),
                  (c2x_right, c2y_right)]

    return path_left, path_right


def find_control_points(c1x, c1y, mmx, mmy, c2x, c2y):
    """
    Find control points of the Bezier curve passing through (*c1x*, *c1y*),
    (*mmx*, *mmy*), and (*c2x*, *c2y*), at parametric values 0, 0.5, and 1.
    """
    cmx = .5 * (4 * mmx - (c1x + c2x))
    cmy = .5 * (4 * mmy - (c1y + c2y))
    return [(c1x, c1y), (cmx, cmy), (c2x, c2y)]


def make_wedged_bezier2(bezier2, width, w1=1., wm=0.5, w2=0.):
    """
    Being similar to get_parallels, returns control points of two quadratic
    bezier lines having a width roughly parallel to given one separated by
    *width*.
    """

    # c1, cm, c2
    c1x, c1y = bezier2[0]
    cmx, cmy = bezier2[1]
    c3x, c3y = bezier2[2]

    # t1 and t2 is the angle between c1 and cm, cm, c3.
    # They are also a angle of the tangential line of the path at c1 and c3
    cos_t1, sin_t1 = get_cos_sin(c1x, c1y, cmx, cmy)
    cos_t2, sin_t2 = get_cos_sin(cmx, cmy, c3x, c3y)

    # find c1_left, c1_right which are located along the lines
    # through c1 and perpendicular to the tangential lines of the
    # bezier path at a distance of width. Same thing for c3_left and
    # c3_right with respect to c3.
    c1x_left, c1y_left, c1x_right, c1y_right = (
        get_normal_points(c1x, c1y, cos_t1, sin_t1, width * w1)
    )
    c3x_left, c3y_left, c3x_right, c3y_right = (
        get_normal_points(c3x, c3y, cos_t2, sin_t2, width * w2)
    )

    # find c12, c23 and c123 which are middle points of c1-cm, cm-c3 and
    # c12-c23
    c12x, c12y = (c1x + cmx) * .5, (c1y + cmy) * .5
    c23x, c23y = (cmx + c3x) * .5, (cmy + c3y) * .5
    c123x, c123y = (c12x + c23x) * .5, (c12y + c23y) * .5

    # tangential angle of c123 (angle between c12 and c23)
    cos_t123, sin_t123 = get_cos_sin(c12x, c12y, c23x, c23y)

    c123x_left, c123y_left, c123x_right, c123y_right = (
        get_normal_points(c123x, c123y, cos_t123, sin_t123, width * wm)
    )

    path_left = find_control_points(c1x_left, c1y_left,
                                    c123x_left, c123y_left,
                                    c3x_left, c3y_left)
    path_right = find_control_points(c1x_right, c1y_right,
                                     c123x_right, c123y_right,
                                     c3x_right, c3y_right)

    return path_left, path_right


def make_path_regular(p):
    """
    If the :attr:`codes` attribute of `Path` *p* is None, return a copy of *p*
    with the :attr:`codes` set to (MOVETO, LINETO, LINETO, ..., LINETO);
    otherwise return *p* itself.
    """
    c = p.codes
    if c is None:
        c = np.full(len(p.vertices), Path.LINETO, dtype=Path.code_type)
        c[0] = Path.MOVETO
        return Path(p.vertices, c)
    else:
        return p


def concatenate_paths(paths):
    """Concatenate a list of paths into a single path."""
    vertices = np.concatenate([p.vertices for p in paths])
    codes = np.concatenate([make_path_regular(p).codes for p in paths])
    return Path(vertices, codes)
