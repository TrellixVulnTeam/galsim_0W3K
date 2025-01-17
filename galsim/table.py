# Copyright (c) 2012-2018 by the GalSim developers team on GitHub
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
# https://github.com/GalSim-developers/GalSim
#
# GalSim is free software: redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions, and the disclaimer given in the accompanying LICENSE
#    file.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions, and the disclaimer given in the documentation
#    and/or other materials provided with the distribution.
#
""""@file table.py
A few adjustments to galsim.LookupTable at the Python layer, including the
addition of the docstring and few extra features.

Also, a simple 2D table for gridded input data: LookupTable2D.
"""
import numpy as np
import numbers

from . import _galsim
from .utilities import lazy_property
from .position import PositionD
from .bounds import BoundsD
from .errors import GalSimRangeError, GalSimBoundsError, GalSimValueError
from .errors import GalSimIncompatibleValuesError, convert_cpp_errors

class LookupTable(object):
    """
    LookupTable represents a lookup table to store function values that may be slow to calculate,
    for which interpolating from a lookup table is sufficiently accurate.

    A LookupTable may be constructed from two arrays (lists, tuples, or NumPy arrays of
    floats/doubles).

        >>> args = [...]
        >>> vals = []
        >>> for arg in args:
        ...     val = calculateVal(arg)
        ...     vals.append(val)
        >>> table = galsim.LookupTable(x=args,f=vals)

    Then you can use this table as a replacement for the slow calculation:

        >>> other_args = [...]
        >>> for arg in other_args:
        ...     val = table(arg)
        ...     [... use val ...]


    The default interpolation method is cubic spline interpolation.  This is usually the
    best choice, but we also provide three other options, which can be specified by
    the `interpolant` kwarg.  The choices are 'floor', 'ceil', 'linear' and 'spline':

    - 'floor' takes the value from the previous argument in the table.
    - 'ceil' takes the value from the next argument in the table.
    - 'nearest' takes the value from the nearest argument in the table.
    - 'linear' does linear interpolation between these two values.
    - 'spline' uses a cubic spline interpolation, so the interpolated values are smooth at
      each argument in the table.

    There are also two factory functions which can be used to build a LookupTable:

        LookupTable.from_func   makes a LookupTable from a callable function
        LookupTable.from_file   reads in a file of x and f values.

    The user can also opt to interpolate in log(x) and/or log(f), though this is not the default.
    It may be a wise choice depending on the particular function, e.g., for a nearly power-law
    f(x) (or at least one that is locally power-law-ish for much of the x range) then it might
    be a good idea to interpolate in log(x) and log(f) rather than x and f.

    @param x             The list, tuple, or NumPy array of `x` values (floats, doubles, or ints,
                         which get silently converted to floats for the purpose of interpolation).
    @param f             The list, tuple, or NumPy array of `f(x)` values (floats, doubles, or ints,
                         which get silently converted to floats for the purpose of interpolation).
    @param interpolant   The interpolant to use, with the options being 'floor', 'ceil', 'nearest',
                         'linear' and 'spline'. [default: 'spline']
    @param x_log         Set to True if you wish to interpolate using log(x) rather than x.  Note
                         that all inputs / outputs will still be x, it's just a question of how the
                         interpolation is done. [default: False]
    @param f_log         Set to True if you wish to interpolate using log(f) rather than f.  Note
                         that all inputs / outputs will still be f, it's just a question of how the
                         interpolation is done. [default: False]
    """
    def __init__(self, x, f, interpolant=None, x_log=False, f_log=False):
        self.x_log = x_log
        self.f_log = f_log

        # check for proper interpolant
        if interpolant is None:
            interpolant = 'spline'
        else:
            if interpolant not in ('spline', 'linear', 'ceil', 'floor', 'nearest'):
                raise GalSimValueError("Unknown interpolant", interpolant,
                                       ('spline', 'linear', 'ceil', 'floor', 'nearest'))
        self.interpolant = interpolant

        # Sanity checks
        if len(x) != len(f):
            raise GalSimIncompatibleValuesError("Input array lengths don't match", x=x, f=f)
        if interpolant == 'spline' and len(x) < 3:
            raise GalSimValueError("Input arrays too small to spline interpolate", x)
        if interpolant in ('linear', 'ceil', 'floor', 'nearest') and len(x) < 2:
            raise GalSimValueError("Input arrays too small to interpolate", x)

        # turn x and f into numpy arrays so that all subsequent math is possible (unlike for
        # lists, tuples).  Also make sure the dtype is float
        x = np.asarray(x, dtype=float)
        f = np.asarray(f, dtype=float)
        s = np.argsort(x)
        self.x = np.ascontiguousarray(x[s])
        self.f = np.ascontiguousarray(f[s])

        self._x_min = self.x[0]
        self._x_max = self.x[-1]
        if self._x_min == self._x_max:
            raise GalSimValueError("All x values are equal", x)
        if self.x_log and self.x[0] <= 0.:
            raise GalSimValueError("Cannot interpolate in log(x) when table contains x<=0.", x)
        if self.f_log and np.any(self.f <= 0.):
            raise GalSimValueError("Cannot interpolate in log(f) when table contains f<=0.", f)

    @lazy_property
    def _tab(self):
        # Store these as attributes, so don't need to worry about C++ layer persisting them.
        self._x = self.x
        self._f = self.f
        if self.x_log: self._x = np.log(self._x)
        if self.f_log: self._f = np.log(self._f)

        with convert_cpp_errors():
            return _galsim._LookupTable(self._x.ctypes.data, self._f.ctypes.data,
                                        len(self._x), self.interpolant)

    @property
    def x_min(self): return self._x_min
    @property
    def x_max(self): return self._x_max

    def __len__(self): return len(self.x)

    def __call__(self, x):
        """Interpolate the LookupTable to get `f(x)` at some `x` value(s).

        When the LookupTable object is called with a single argument, it returns the value at that
        argument.  An exception will be thrown automatically by the _LookupTable class if the `x`
        value is outside the range of the original tabulated values.  The value that is returned is
        the same type as that provided as an argument, e.g., if a single value `x` is provided then
        a single value of `f` is returned; if a tuple of `x` values is provided then a tuple of `f`
        values is returned; and so on.  Even if interpolation was done using the `x_log` option,
        the user should still provide `x` rather than `log(x)`.

        @param x        The `x` value(s) for which `f(x)` should be calculated via interpolation on
                        the original `(x,f)` lookup table.  `x` can be a single float/double, or a
                        tuple, list, or arbitrarily shaped 1- or 2-dimensional NumPy array.

        @returns the interpolated `f(x)` value(s).
        """
        # Check that all x values are in the allowed range
        self._check_range(x)

        # Handle the log(x) if necessary
        if self.x_log:
            x = np.log(x)

        x = np.asarray(x)
        if x.shape == ():
            f = self._tab.interp(float(x))
        else:
            dimen = len(x.shape)
            if dimen > 1:
                f = np.empty_like(x.ravel(), dtype=float)
                xx = x.astype(float,copy=False).ravel()
                self._tab.interpMany(xx.ctypes.data, f.ctypes.data, len(xx))
                f = f.reshape(x.shape)
            else:
                f = np.empty_like(x, dtype=float)
                xx = x.astype(float,copy=False)
                self._tab.interpMany(xx.ctypes.data, f.ctypes.data, len(xx))

        # Handle the log(f) if necessary
        if self.f_log:
            f = np.exp(f)
        return f

    def _check_range(self, x):
        slop = (self.x_max - self.x_min) * 1.e-6
        if np.min(x) < self.x_min - slop:
            raise GalSimRangeError("x value(s) below the range of the LookupTable.",
                                   x, self.x_min, self.x_max)
        if np.max(x) > self.x_max + slop:
            raise GalSimRangeError("x value(s) above the range of the LookupTable.",
                                   x, self.x_min, self.x_max)

    def getArgs(self):
        return self.x

    def getVals(self):
        return self.f

    def getInterp(self):
        return self.interpolant

    def isLogX(self):
        return self.x_log

    def isLogF(self):
        return self.f_log

    def __eq__(self, other):
        return (isinstance(other, LookupTable) and
                np.array_equal(self.x,other.x) and
                np.array_equal(self.f,other.f) and
                self.x_log == other.x_log and
                self.f_log == other.f_log and
                self.interpolant == other.interpolant)
    def __ne__(self, other): return not self.__eq__(other)

    def __hash__(self):
        # Cache this in case self.x, self.f are long.
        if not hasattr(self, '_hash'):
            self._hash = hash(("galsim.LookupTable", tuple(self.x), tuple(self.f), self.x_log,
                               self.f_log, self.interpolant))
        return self._hash


    def __repr__(self):
        return 'galsim.LookupTable(x=array(%r), f=array(%r), interpolant=%r, x_log=%r, f_log=%r)'%(
            self.x.tolist(), self.f.tolist(), self.interpolant, self.x_log, self.f_log)

    def __str__(self):
        s = 'galsim.LookupTable(x=[%s,...,%s], f=[%s,...,%s]'%(
            self.x[0], self.x[-1], self.f[0], self.f[-1])
        if self.interpolant != 'spline':
            s += ', interpolant=%r'%(self.interpolant)
        if self.x_log:
            s += ', x_log=True'
        if self.f_log:
            s += ', f_log=True'
        s += ')'
        return s

    @classmethod
    def from_file(cls, file_name, interpolant='spline', x_log=False, f_log=False, amplitude=1.0):
        """Create a LookupTable from a file of x, f values.

        This reads in a file, which should contain two columns with the x and f values.

        @param file_name    A file from which to read the `(x,f)` pairs.
        @param interpolant  Type of interpolation to use. [default: 'spline']
        @param x_log        Whether the x values should be uniform in log rather than lienar.
                            [default: False]
        @param f_log        Whether the f values should be interpolated using their logarithms
                            rather than their raw values. [default: False]
        @param amplitude    An optional scaling of the f values relative to the values in the file
                            [default: 1.0]
        """
        # We don't require pandas as a dependency, but if it's available, this is much faster.
        # cf. http://stackoverflow.com/questions/15096269/the-fastest-way-to-read-input-in-python
        CParserError = AttributeError # In case we don't get to the line below where we import
                                      # it from pandas.parser
        try:
            import pandas
            try:
                # version >= 0.20
                from pandas.io.common import CParserError
            except ImportError:
                # version < 0.20
                from pandas.parser import CParserError
            data = pandas.read_csv(file_name, comment='#', delim_whitespace=True, header=None)
            data = data.values.transpose()
        except (ImportError, AttributeError, CParserError): # pragma: no cover
            data = np.loadtxt(file_name).transpose()
        if data.shape[0] != 2:  # pragma: no cover
            raise GalSimValueError("File provided for LookupTable does not have 2 columns",
                                   file_name)
        x=data[0]
        f=data[1]
        if amplitude != 1.0:
            f[:] *= amplitude
        return LookupTable(x, f, interpolant=interpolant, x_log=x_log, f_log=f_log)

    @classmethod
    def from_func(cls, func, x_min, x_max, npoints=2000, interpolant='spline',
                  x_log=False, f_log=False):
        """Create a LookupTable from a callable function

        This constructs a LookupTable over the given range from x_min and x_max, calculating the
        corresponding f values from the given function (technically any callable object).

        @param func         A callable function.
        @param x_min        The minimum x value at which to evalue the function and store in the
                            lookup table.
        @param x_max        The maximum x value at which to evalue the function and store in the
                            lookup table.
        @param npoints      Number of x values at which to evaluate the function. [default: 2000]
        @param interpolant  Type of interpolation to use. [default: 'spline']
        @param x_log        Whether the x values should be uniform in log rather than lienar.
                            [default: False]
        @param f_log        Whether the f values should be interpolated using their logarithms
                            rather than their raw values. [default: False]
        """
        if x_log:
            x = np.exp(np.linspace(np.log(x_min), np.log(x_max), npoints))
        else:
            x = np.linspace(x_min, x_max, npoints)
        f = np.array([func(xx) for xx in x])
        return cls(x, f, interpolant=interpolant, x_log=x_log, f_log=f_log)

    def __getstate__(self):
        d = self.__dict__.copy()
        d.pop('_tab',None)
        return d

    def __setstate__(self, d):
        self.__dict__ = d

class LookupTable2D(object):
    """
    LookupTable2D represents a 2-dimensional lookup table to store function values that may be slow
    to calculate, for which interpolating from a lookup table is sufficiently accurate.  A
    LookupTable2D is also useful for evaluating periodic 2-d functions given samples from a single
    period.

    A LookupTable2D representing the function f(x, y) may be constructed from a list or array of `x`
    values, a list or array of `y` values, and a 2D array of function evaluations at all
    combinations of x and y values.  For instance:

        >>> x = np.arange(5)
        >>> y = np.arange(8)
        >>> z = x[:, np.newaxis] + y  # function is x + y, dimensions of z are (5, 8)
        >>> tab2d = galsim.LookupTable2D(x, y, z)

    To evaluate new function values with the lookup table, use the () operator:

        >>> print tab2d(2.2, 3.3)
        5.5

    The () operator can also accept sequences (lists, tuples, numpy arrays, ...) for the x and y
    arguments at which to evaluate the LookupTable2D.  The x and y sequences should have the same
    length in this case, which will also be the length of the output sequence.

        >>> print tab2d([1, 2], [3, 4])
        [ 4.  6.]

    The default interpolation method is linear.  Other choices for the interpolant are:
      - 'floor'
      - 'ceil'
      - 'nearest'

        >>> tab2d = galsim.LookupTable2D(x, y, z, interpolant='floor')
        >>> tab2d(2.2, 3.7)
        5.0
        >>> tab2d = galsim.LookupTable2D(x, y, z, interpolant='ceil')
        >>> tab2d(2.2, 3.7)
        7.0
        >>> tab2d = galsim.LookupTable2D(x, y, z, interpolant='nearest')
        >>> tab2d(2.2, 3.7)
        6.0

    The `edge_mode` keyword describes how to handle extrapolation beyond the initial input range.
    Possibilities include:
      - 'raise': raise an exception.  (This is the default.)
      - 'constant': Return a constant specified by the `constant` keyword.
      - 'wrap': infinitely wrap the initial range in both directions.
    In order for LookupTable2D to determine the wrapping period when edge_mode='wrap', either the
    x and y grid points need to be equally spaced (in which case the x-period is inferred as
    len(x)*(x[1]-x[0]) and similarly for y), or the first/last row/column of f must be identical,
    in which case the x-period is inferred as x[-1] - x[0].  (If both conditions are satisfied
    (equally-spaced x and y and identical first/last row/column of f, then the x-period is inferred
    as len(x)*(x[1]-x[0])).

        >>> x = np.arange(5)
        >>> y = np.arange(8)
        >>> z = x[:, np.newaxis] + y  # function is x + y, dimensions of z is (5, 8)
        >>> tab2d = galsim.LookupTable2D(x, y, z, edge_mode='raise')
        >>> tab2d(7, 7)
        ValueError: Extrapolating beyond input range.

        >>> tab2d = galsim.LookupTable2D(x, y, z, edge_mode='constant', constant=1.0)
        1.0

        >>> tab2d = galsim.LookupTable2D(x, y, z, edge_mode='wrap')
        ValueError: Cannot wrap `f` array with unequal first/last column/row.

    We extend the x and y arrays with a uniform spacing, though any monotonic spacing would work.
    Note that the [(0,1), (0,1)] argument in np.pad below extends the z array by 0 rows/columns in
    the leading direction, and 1 row/column in the trailing direction.

        >>> x = np.append(x, x[-1] + (x[-1]-x[-2]))
        >>> y = np.append(y, y[-1] + (y[-1]-y[-2]))
        >>> z = np.pad(z, [(0,1), (0,1)], mode='wrap')
        >>> tab2d = galsim.LookupTable2D(x, y, z, edge_mode='wrap')
        >>> tab2d(2., 2.)
        4.0
        >>> tab2d(2.+5, 2.)  # The period is 5 in the x direction
        4.0
        >>> tab2d(2.+3*5, 2.+4*8)  # The period is 8 in the y direction
        4.0

    @param x              Strictly increasing array of `x` positions at which to create table.
    @param y              Strictly increasing array of `y` positions at which to create table.
    @param f              Nx by Ny input array of function values.
    @param interpolant    Interpolant to use.  One of 'floor', 'ceil', 'nearest', or 'linear'.
                          [default: 'linear']
    @param edge_mode      Keyword controlling how extrapolation beyond the input range is handled.
                          See above for details.  [default: 'raise']
    @param constant       A constant to return when extrapolating beyond the input range and
                          `edge_mode='constant'`.  [default: 0]
    """
    def __init__(self, x, y, f, interpolant='linear', edge_mode='raise', constant=0):
        if edge_mode not in ('raise', 'wrap', 'constant'):
            raise GalSimValueError("Unknown edge_mode.", edge_mode, ('raise', 'wrap', 'constant'))

        self.x = np.ascontiguousarray(x, dtype=float)
        self.y = np.ascontiguousarray(y, dtype=float)
        self.f = np.ascontiguousarray(f, dtype=float)

        dx = np.diff(self.x)
        dy = np.diff(self.y)

        if not all(dx > 0):
            raise GalSimValueError("x input grids is not strictly increasing.", x)
        if not all(dy > 0):
            raise GalSimValueError("y input grids is not strictly increasing.", y)

        fshape = self.f.shape
        if fshape != (len(x), len(y)):
            raise GalSimIncompatibleValuesError(
                "Shape of f incompatible with lengths of x,y", f=f, x=x, y=y)

        if interpolant not in ('linear', 'ceil', 'floor', 'nearest'):
            raise GalSimValueError("Unknown interpolant.", interpolant,
                                   ('linear', 'ceil', 'floor', 'nearest'))
        self.interpolant = interpolant


        self.interpolant = interpolant
        self.edge_mode = edge_mode
        self.constant = float(constant)

        if self.edge_mode == 'wrap':
            # Can wrap if x and y arrays are equally spaced ...
            if np.allclose(dx, dx[0]) and np.allclose(dy, dy[0]):
                # Underlying Table2D requires us to extend x, y, and f.
                self.x = np.append(self.x, self.x[-1]+dx[0])
                self.y = np.append(self.y, self.y[-1]+dy[0])
                self.f = np.pad(self.f, [(0,1), (0,1)], mode='wrap')
            if (all(self.f[0] == self.f[-1]) and all(self.f[:,0] == self.f[:,-1])):
                self.xperiod = self.x[-1] - self.x[0]
                self.yperiod = self.y[-1] - self.y[0]
            else:
                raise GalSimIncompatibleValuesError(
                    "Cannot use edge_mode='wrap' unless either x and y are equally "
                    "spaced or first/last row/column of f are identical.",
                    edge_mode=edge_mode, x=x, y=y, f=f)

    @lazy_property
    def _tab(self):
        with convert_cpp_errors():
            return _galsim._LookupTable2D(self.x.ctypes.data, self.y.ctypes.data,
                                          self.f.ctypes.data, len(self.x), len(self.y),
                                          self.interpolant)
    def getXArgs(self):
        return self.x

    def getYArgs(self):
        return self.y

    def getVals(self):
        return self.f

    def _inbounds(self, x, y):
        """Return whether or not *all* coords specified by x and y are in bounds of the original
        interpolated array."""
        return (np.min(x) >= self.x[0] and np.max(x) <= self.x[-1] and
                np.min(y) >= self.y[0] and np.max(y) <= self.y[-1])

    def _wrap_args(self, x, y):
        """Wrap points back into the fundamental period."""
        return ((x-self.x[0]) % self.xperiod + self.x[0],
                (y-self.y[0]) % self.yperiod + self.y[0])

    @property
    def _bounds(self):
        return BoundsD(self.x[0], self.x[-1], self.y[0], self.y[-1])

    def _call_raise(self, x, y):
        if not self._inbounds(x, y):
            raise GalSimBoundsError("Extrapolating beyond input range.",
                                    PositionD(x,y), self._bounds)

        if isinstance(x, numbers.Real):
            return self._tab.interp(x, y)
        else:
            xx = np.ascontiguousarray(x.ravel(), dtype=float)
            yy = np.ascontiguousarray(y.ravel(), dtype=float)
            f = np.empty_like(xx, dtype=float)
            self._tab.interpMany(xx.ctypes.data, yy.ctypes.data, f.ctypes.data, len(xx))
            f = f.reshape(x.shape)
            return f

    def _call_wrap(self, x, y):
        x, y = self._wrap_args(x, y)
        return self._call_raise(x, y)

    def _call_constant(self, x, y):
        if isinstance(x, numbers.Real):
            if self._inbounds(x, y):
                return self._tab.interp(x, y)
            else:
                return self.constant
        else:
            x = np.array(x, dtype=float, copy=False)
            y = np.array(y, dtype=float, copy=False)
            f = np.empty_like(x, dtype=float)
            f.fill(self.constant)
            good = ((x >= self.x[0]) & (x <= self.x[-1]) &
                    (y >= self.y[0]) & (y <= self.y[-1]))
            xx = np.ascontiguousarray(x[good].ravel(), dtype=float)
            yy = np.ascontiguousarray(y[good].ravel(), dtype=float)
            tmp = np.empty_like(xx, dtype=float)
            self._tab.interpMany(xx.ctypes.data, yy.ctypes.data, tmp.ctypes.data, len(xx))
            f[good] = tmp
            return f

    def __call__(self, x, y):
        if self.edge_mode == 'raise':
            return self._call_raise(x, y)
        elif self.edge_mode == 'wrap':
            return self._call_wrap(x, y)
        else: # constant
            return self._call_constant(x, y)

    def _gradient_raise(self, x, y):
        if not self._inbounds(x, y):
            raise GalSimBoundsError("Extrapolating beyond input range.",
                                    PositionD(x,y), self._bounds)

        if isinstance(x, numbers.Real):
            grad = np.empty(2, dtype=float)
            self._tab.gradient(x, y, grad.ctypes.data)
            return grad[0], grad[1]
        else:
            xx = np.ascontiguousarray(x.ravel(), dtype=float)
            yy = np.ascontiguousarray(y.ravel(), dtype=float)
            dfdx = np.empty_like(xx)
            dfdy = np.empty_like(xx)
            self._tab.gradientMany(xx.ctypes.data, yy.ctypes.data,
                                   dfdx.ctypes.data, dfdy.ctypes.data, len(xx))
            dfdx = dfdx.reshape(x.shape)
            dfdy = dfdy.reshape(x.shape)
            return dfdx, dfdy

    def _gradient_wrap(self, x, y):
        x, y = self._wrap_args(x, y)
        return self._gradient_raise(x, y)

    def _gradient_constant(self, x, y):
        if isinstance(x, numbers.Real):
            if self._inbounds(x, y):
                grad = np.empty(2, dtype=float)
                self._tab.gradient(float(x), float(y), grad.ctypes.data)
                return tuple(grad)
            else:
                return 0.0, 0.0
        else:
            x = np.array(x, dtype=float, copy=False)
            y = np.array(y, dtype=float, copy=False)
            dfdx = np.empty_like(x, dtype=float)
            dfdy = np.empty_like(x, dtype=float)
            dfdx.fill(0.0)
            dfdy.fill(0.0)
            good = ((x >= self.x[0]) & (x <= self.x[-1]) &
                    (y >= self.y[0]) & (y <= self.y[-1]))
            xx = np.ascontiguousarray(x[good].ravel(), dtype=float)
            yy = np.ascontiguousarray(y[good].ravel(), dtype=float)
            tmp1 = np.empty_like(xx, dtype=float)
            tmp2 = np.empty_like(xx, dtype=float)
            self._tab.gradientMany(xx.ctypes.data, yy.ctypes.data,
                                   tmp1.ctypes.data, tmp2.ctypes.data, len(xx))
            dfdx[good] = tmp1
            dfdy[good] = tmp2
            return dfdx, dfdy

    def gradient(self, x, y):
        """Calculate the gradient of the function at an arbitrary point or points.

        @param x        Either a single x value or an array of x values at which to compute
                        the gradient.
        @param y        Either a single y value or an array of y values at which to compute
                        the gradient.

        @returns A tuple of (dfdx, dfdy) where dfdx, dfdy are single values (if x,y were single
        values) or numpy arrays.
        """
        if self.edge_mode == 'raise':
            return self._gradient_raise(x, y)
        elif self.edge_mode == 'wrap':
            return self._gradient_wrap(x, y)
        else: # constant
            return self._gradient_constant(x, y)

    def __str__(self):
        return ("galsim.LookupTable2D(x=[%s,...,%s], y=[%s,...,%s], "
                "f=[[%s,...,%s],...,[%s,...,%s]], interpolant=%r, edge_mode=%r)"%(
            self.x[0], self.x[-1], self.y[0], self.y[-1],
            self.f[0,0], self.f[0,-1], self.f[-1,0], self.f[-1,-1],
            self.interpolant, self.edge_mode))

    def __repr__(self):
        return ("galsim.LookupTable2D(x=array(%r), y=array(%r), "
                "f=array(%r), interpolant=%r, edge_mode=%r, constant=%r)"%(
            self.x.tolist(), self.y.tolist(), self.f.tolist(), self.interpolant, self.edge_mode,
            self.constant))

    def __eq__(self, other):
        return (isinstance(other, LookupTable2D) and
                np.array_equal(self.x,other.x) and
                np.array_equal(self.y,other.y) and
                np.array_equal(self.f,other.f) and
                self.interpolant == other.interpolant and
                self.edge_mode == other.edge_mode and
                self.constant == other.constant)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(("galsim.LookupTable2D", tuple(self.x.ravel()), tuple(self.y.ravel()),
                    tuple(self.f.ravel()), self.interpolant, self.edge_mode, self.constant))

    def __getstate__(self):
        d = self.__dict__.copy()
        d.pop('_tab',None)
        return d

    def __setstate__(self, d):
        self.__dict__ = d
