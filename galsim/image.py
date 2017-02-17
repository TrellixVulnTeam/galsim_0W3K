# Copyright (c) 2012-2016 by the GalSim developers team on GitHub
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
"""@file image.py
The Image class and some modifications to the docs for the C++ layer ImageAlloc and ImageView
classes.
"""

from future.utils import with_metaclass
from . import _galsim
import numpy as np
import galsim

# Sometimes (on 32-bit systems) there are two numpy.int32 types.  This can lead to some confusion
# when doing arithmetic with images.  So just make sure both of them point to ImageAllocI in the
# ImageAlloc dict.  One of them is what you get when you just write numpy.int32.  The other is
# what numpy decides an int16 + int32 is.  The first one is usually the one that's already in the
# ImageAlloc dict, but we assign both versions just to be sure.

_galsim.ImageAlloc[np.int32] = _galsim.ImageAllocI
_galsim.ImageView[np.int32] = _galsim.ImageViewI
_galsim.ConstImageView[np.int32] = _galsim.ConstImageViewI

alt_int32 = ( np.array([0]).astype(np.int32) + 1).dtype.type
_galsim.ImageAlloc[alt_int32] = _galsim.ImageAllocI
_galsim.ImageView[alt_int32] = _galsim.ImageViewI
_galsim.ConstImageView[alt_int32] = _galsim.ConstImageViewI

# On some systems, the above doesn't work, but this next one does.  I'll leave both active,
# just in case there are systems where this doesn't work but the above does.
alt_int32 = ( np.array([0]).astype(np.int16) +
              np.array([0]).astype(np.int32) ).dtype.type
_galsim.ImageAlloc[alt_int32] = _galsim.ImageAllocI
_galsim.ImageView[alt_int32] = _galsim.ImageViewI
_galsim.ConstImageView[alt_int32] = _galsim.ConstImageViewI

# For more information regarding this rather unexpected behaviour for numpy.int32 types, see
# the following (closed, marked "wontfix") ticket on the numpy issue tracker:
# http://projects.scipy.org/numpy/ticket/1246

# This meta class thing is to allow the obsolete syntax Image[float32](ncol,nrow).
# For that, we need to allow for the __getitem__ method to be a staticmethod.
# cf. http://stackoverflow.com/questions/6187932/how-to-write-a-static-python-getitem-method
class MetaImage(type):
    def __getitem__(cls,t):
        """A deprecated syntax that treats Image as a dict indexed by type"""
        from galsim.deprecated import depr
        depr('Image[type]', 1.1, 'Image(..., dtype=type)')
        Image_dict = {
            np.int16 : ImageS,
            np.int32 : ImageI,
            np.float32 : ImageF,
            np.float64 : ImageD
        }
        return Image_dict[t]

class Image(with_metaclass(MetaImage, object)):
    """A class for storing image data along with the pixel scale or WCS information

    The Image class encapsulates all the relevant information about an image including a NumPy array
    for the pixel values, a bounding box, and some kind of WCS that converts between pixel
    coordinates and world coordinates.  The NumPy array may be constructed by the Image class
    itself, or an existing array can be provided by the user.

    This class creates shallow copies unless a deep copy is explicitly requested using the `copy`
    method.  The main reason for this is that it allows users to work directly with and modify
    subimages of larger images (for example, to successively draw many galaxies into one large
    image).  For other implications of this convention, see the description of initialization
    instructions below.

    In most applications with images, we will use (x,y) to refer to the coordinates.  We adopt
    the same meaning for these coordinates as most astronomy applications do: ds9, SAOImage,
    SExtractor, etc. all treat x as the column number and y as the row number.  However, this
    is different from the default convention used by numpy.  In numpy, the access is by
    [row_num,col_num], which means this is really [y,x] in terms of the normal x,y values.
    Users are typically insulated from this concern by the Image API, but if you access the
    numpy array directly via the `array` attribute, you will need to be careful about this
    difference.

    There are 4 data types that the Image can use for the data values.  These are `numpy.int16`,
    `numpy.int32`, `numpy.float32`, and `numpy.float64`.  If you are constructing a new Image from
    scratch, the default is `numpy.float32`, but you can specify one of the other data types.

    Initialization
    --------------

    There are several ways to construct an Image:

        Image(ncol, nrow, dtype=numpy.float32, init_value=0, ...)

                This constructs a new image, allocating memory for the pixel values according to
                the number of columns and rows.  You can specify the data type as `dtype` if you
                want.  The default is `numpy.float32` if you don't specify it.  You can also
                optionally provide an initial value for the pixels, which defaults to 0.
                Reminder, with our convention for x,y coordinates described above, ncol is the
                number of pixels in the x direction, and nrow is the number of pixels in the y
                direction.

        Image(bounds, dtype=numpy.float32, init_value=0, ...)

                This constructs a new image, allocating memory for the pixel values according to a
                given bounds object.  The bounds should be a BoundsI instance.  You can specify the
                data type as `dtype` if you want.  The default is `numpy.float32` if you don't
                specify it.  You can also optionally provide an initial value for the pixels, which
                defaults to 0.

        Image(array, xmin=1, ymin=1, make_const=False, ...)

                This views an existing NumPy array as an Image, with updates to the array or Image
                being affecting the other object unless `Image(array.copy(), ...)` is used.  The
                dtype is taken from `array.dtype`, which must be one of the allowed types listed
                above.  You can also optionally set the origin `(xmin, ymin)` if you want it to be
                something other than (1,1).  You can also optionally force the Image to be read-only
                with `make_const=True`, though if the original NumPy array is modified then the
                contents of `Image.array` will change.

        Image(image, dtype=dtype)

                This creates a shallow copy of an Image, possibly changing the type.  e.g.

                    >>> image_float = galsim.Image(64, 64) # default dtype=numpy.float32
                    >>> image_double = galsim.Image(image_float, dtype=numpy.float64)

                To get a deep copy, use the `copy` method rather than the `Image` constructor.

    You can specify the `ncol`, `nrow`, `bounds`, `array`, or `image`  parameters by keyword
    argument if you want, or you can pass them as simple arg as shown aboves, and the constructor
    will figure out what they are.

    The other keyword arguments (shown as ... above) relate to the conversion between sky
    coordinates, which is how all the GalSim objects are defined, and the pixel coordinates.
    There are three options for this:

        scale       You can optionally specify a pixel scale to use.  This would normally have
                    units arcsec/pixel, but it doesn't have to be arcsec.  If you want to
                    use different units for the physical scale of your galsim objects, then
                    the same unit would be used here.
        wcs         A WCS object that provides a non-trivial mapping between sky units and
                    pixel units.  The `scale` parameter is equivalent to `wcs=PixelScale(scale)`.
                    But there are a number of more complicated options.  See the WCS class
                    for more details.
        None        If you do not provide either of the above, then the conversion is undefined.
                    When drawing onto such an image, a suitable pixel scale will be automatically
                    set according to the Nyquist scale of the object being drawn.


    Attributes
    ----------

    After construction, you can set or change the scale or wcs with

        >>> image.scale = new_scale
        >>> image.wcs = new_wcs

    Note that `image.scale` will only work if the WCS is a PixelScale.  Once you set the
    wcs to be something non-trivial, then you must interact with it via the `wcs` attribute.
    The `image.scale` syntax will raise an exception.

    There are also two read-only attributes:

        >>> image.bounds
        >>> image.array

    The `array` attribute is a NumPy array of the Image's pixels.  The individual elements in the
    array attribute are accessed as `image.array[y,x]`, matching the standard NumPy convention,
    while the Image class's own accessor uses `(x,y)`.  That is, the following are equivalent:

        >>> ixy = image(x,y)
        >>> ixy = image.array[y,x]


    Methods
    -------

        view        Return a view of the image, possibly giving it a new scale or wcs.
        subImage    Return a view of a portion of the full image.
        shift       Shift the origin of the image by (dx,dy).
        setCenter   Set a new position for the center of the image.
        setOrigin   Set a new position for the origin (x,y) = (0,0) of the image.
        im(x,y)     Get the value of a single pixel.
        setValue    Set the value of a single pixel.
        resize      Resize the image to have a new bounds.
        fill        Fill the image with the same value in all pixels.
        setZero     Fill the image with zeros.
        invertSelf  Convert each value x to 1/x.
        copy        Return a deep copy of the image.

    See their doc strings for more details.

    """

    cpp_valid_dtypes = list(_galsim.ImageView)
    alias_dtypes = {
        int : np.int32,          # So that user gets what they would expect
        float : np.float64,      # if using dtype=int or float
    }
    # Note: Numpy uses int64 for int on 64 bit machines.  We don't implement int64 at all,
    # so we cannot quite match up to the numpy convention for dtype=int.  e.g. via
    #     int : numpy.zeros(1,dtype=int).dtype.type
    # If this becomes too confusing, we might need to add an ImageL class that uses int64.
    # Hard to imagine a use case where this would be required though...
    valid_dtypes = cpp_valid_dtypes + list(alias_dtypes)

    unsigned_dtypes = {
        # We don't have unsigned image code, so just use signed int types.
        np.uint32 : np.int32,
        np.uint16 : np.int16,
    }
    valid_array_dtypes = cpp_valid_dtypes + list(unsigned_dtypes)

    def __init__(self, *args, **kwargs):
        # Parse the args, kwargs
        ncol = None
        nrow = None
        bounds = None
        array = None
        image = None
        if len(args) > 2:
            raise TypeError("Error, too many unnamed arguments to Image constructor")
        elif len(args) == 2:
            ncol = args[0]
            nrow = args[1]
        elif len(args) == 1:
            if isinstance(args[0], np.ndarray):
                array = args[0]
                xmin = kwargs.pop('xmin',1)
                ymin = kwargs.pop('ymin',1)
                make_const = kwargs.pop('make_const',False)
            elif isinstance(args[0], galsim.BoundsI):
                bounds = args[0]
            else:
                image = args[0]
        else:
            if 'array' in kwargs:
                array = kwargs.pop('array')
                xmin = kwargs.pop('xmin',1)
                ymin = kwargs.pop('ymin',1)
                make_const = kwargs.pop('make_const',False)
                if 'bounds' in kwargs:
                    b = kwargs.pop('bounds')
                    if b.xmax-b.xmin+1 != array.shape[1]:
                        raise ValueError("Shape of array is inconsistent with provided bounds")
                    if b.ymax-b.ymin+1 != array.shape[0]:
                        raise ValueError("Shape of array is inconsistent with provided bounds")
                    xmin = b.xmin
                    ymin = b.ymin
            elif 'bounds' in kwargs:
                bounds = kwargs.pop('bounds')
            elif 'image' in kwargs:
                image = kwargs.pop('image')
            else:
                ncol = kwargs.pop('ncol',None)
                nrow = kwargs.pop('nrow',None)

        # Pop off the other valid kwargs:
        dtype = kwargs.pop('dtype', None)
        init_value = kwargs.pop('init_value', None)
        scale = kwargs.pop('scale', None)
        wcs = kwargs.pop('wcs', None)

        # Check that we got them all
        if kwargs:
            raise TypeError("Image constructor got unexpected keyword arguments: %s",kwargs)

        # Figure out what dtype we want:
        if dtype in Image.alias_dtypes: dtype = Image.alias_dtypes[dtype]
        if dtype is not None and dtype not in Image.valid_dtypes:
            raise ValueError("dtype must be one of "+str(Image.valid_dtypes)+
                             ".  Instead got "+str(dtype))
        if array is not None:
            if array.dtype.type in Image.unsigned_dtypes and dtype is None:
                dtype = Image.unsigned_dtypes[array.dtype.type]
            if array.dtype.type not in Image.cpp_valid_dtypes and dtype is None:
                raise ValueError("array's dtype.type must be one of "+str(Image.cpp_valid_dtypes)+
                                 ".  Instead got "+str(array.dtype.type)+".  Or can set "+
                                 "dtype explicitly.")
            if dtype is not None and dtype != array.dtype.type:
                array = array.astype(dtype)
            # Be careful here: we have to watch out for little-endian / big-endian issues.
            # The path of least resistance is to check whether the array.dtype is equal to the
            # native one (using the dtype.isnative flag), and if not, make a new array that has a
            # type equal to the same one but with the appropriate endian-ness.
            if not array.dtype.isnative:
                array = array.astype(array.dtype.newbyteorder('='))
            self.dtype = array.dtype.type
        elif dtype is not None:
            self.dtype = dtype
        elif image is not None:
            self.dtype = image.array.dtype.type
        else:
            self.dtype = np.float32

        # Construct the image attribute
        if (ncol is not None or nrow is not None):
            if bounds is not None:
                raise TypeError("Cannot specify both ncol/nrow and bounds")
            if array is not None:
                raise TypeError("Cannot specify both ncol/nrow and array")
            if image is not None:
                raise TypeError("Cannot specify both ncol/nrow and image")
            if ncol is None or nrow is None:
                raise TypeError("Both nrow and ncol must be provided")
            try:
                ncol = int(ncol)
                nrow = int(nrow)
            except:
                raise TypeError("Cannot parse ncol, nrow as integers")
            self.image = _galsim.ImageAlloc[self.dtype](ncol, nrow)
            if init_value is not None:
                self.image.fill(init_value)
        elif bounds is not None:
            if array is not None:
                raise TypeError("Cannot specify both bounds and array")
            if image is not None:
                raise TypeError("Cannot specify both bounds and image")
            if not isinstance(bounds, galsim.BoundsI):
                raise TypeError("bounds must be a galsim.BoundsI instance")
            self.image = _galsim.ImageAlloc[self.dtype](bounds)
            if init_value is not None:
                self.image.fill(init_value)
        elif array is not None:
            if image is not None:
                raise TypeError("Cannot specify both array and image")
            if not isinstance(array, np.ndarray):
                raise TypeError("array must be a numpy.ndarray instance")
            # Easier than getting the memory management right in the C++ layer.
            # If we were provided a numpy array, keep a pointer to it here so it lives
            # as long as the self.image object.
            self._array = array
            if make_const:
                self.image = _galsim.ConstImageView[self.dtype](array, xmin, ymin)
            else:
                self.image = _galsim.ImageView[self.dtype](array, xmin, ymin)
            if init_value is not None:
                raise TypeError("Cannot specify init_value with array")
        elif image is not None:
            if isinstance(image, Image):
                if wcs is None and scale is None:
                    wcs = image.wcs
                image = image.image
            self.image = None
            for im_dtype in Image.cpp_valid_dtypes:
                if ( isinstance(image,_galsim.ImageAlloc[im_dtype]) or
                     isinstance(image,_galsim.ImageView[im_dtype]) or
                     isinstance(image,_galsim.ConstImageView[im_dtype]) ):
                    if dtype is not None and im_dtype != dtype:
                        # Allow dtype to force a retyping of the provided image
                        # e.g. im = ImageF(...)
                        #      im2 = ImageD(im)
                        self.image = _galsim.ImageAlloc[dtype](image)
                    else:
                        self.image = image
                    break
            if self.image is None:
                # Then never found the dtype above:
                raise TypeError("image must be an Image or BaseImage type")
            if init_value is not None:
                raise TypeError("Cannot specify init_value with image")
        else:
            self.image = _galsim.ImageAlloc[self.dtype]()
            if init_value is not None:
                raise TypeError("Cannot specify init_value without setting an initial size")
        if not hasattr(self,'_array'):
            self._array = self.image.array

        # Construct the wcs attribute
        if scale is not None:
            if wcs is not None:
                raise TypeError("Cannot provide both scale and wcs to Image constructor")
            self.wcs = galsim.PixelScale(scale)
        else:
            if wcs is not None and not isinstance(wcs,galsim.BaseWCS):
                raise TypeError("wcs parameters must be a galsim.BaseWCS instance")
            self.wcs = wcs

    def __repr__(self):
        return 'galsim.Image(bounds=%r, array=\n%r, wcs=%r)'%(
                self.bounds, self.array, self.wcs)

    def __str__(self):
        if self.wcs is not None and self.wcs.isPixelScale():
            return 'galsim.Image(bounds=%s, scale=%s)'%(self.bounds, self.scale)
        else:
            return 'galsim.Image(bounds=%s, wcs=%s)'%(self.bounds, self.wcs)

    # bounds and array are really properties which pass the request to the image
    @property
    def bounds(self): return self.image.bounds
    @property
    def array(self): return self._array

    # Allow scale to work as a PixelScale wcs.
    @property
    def scale(self):
        if self.wcs:
            if self.wcs.isPixelScale():
                return self.wcs.scale
            else:
                raise TypeError("image.wcs is not a simple PixelScale; scale is undefined.")
        else:
            return None

    @scale.setter
    def scale(self, value):
        if self.wcs is not None and not self.wcs.isPixelScale():
            raise TypeError("image.wcs is not a simple PixelScale; scale is undefined.")
        else:
            self.wcs = galsim.PixelScale(value)

    # Convenience functions
    @property
    def xmin(self): return self.image.bounds.xmin
    @property
    def xmax(self): return self.image.bounds.xmax
    @property
    def ymin(self): return self.image.bounds.ymin
    @property
    def ymax(self): return self.image.bounds.ymax
    def getXMin(self): return self.image.getXMin()
    def getXMax(self): return self.image.getXMax()
    def getYMin(self): return self.image.getYMin()
    def getYMax(self): return self.image.getYMax()
    def getBounds(self): return self.image.getBounds()

    def copy(self):
        return Image(image=self.image.copy(), wcs=self.wcs)

    def resize(self, bounds, wcs=None):
        """Resize the image to have a new bounds (must be a BoundsI instance)

        Note that the resized image will have uninitialized data.  If you want to preserve
        the existing data values, you should either use `subImage` (if you want a smaller
        portion of the current Image) or make a new Image and copy over the current values
        into a portion of the new image (if you are resizing to a larger Image).

        @param bounds   The new bounds to resize to.
        @param wcs      If provided, also update the wcs to the given value. [default: None,
                        which means keep the existing wcs]
        """
        if not isinstance(bounds, galsim.BoundsI):
            raise TypeError("bounds must be a galsim.BoundsI instance")
        try:
            self.image.resize(bounds)
        except:
            # if the image wasn't an ImageAlloc, then above won't work.  So just make it one.
            self.image = _galsim.ImageAlloc[self.dtype](bounds)
        self._array = self.image.array
        if wcs is not None:
            self.wcs = wcs

    def subImage(self, bounds):
        """Return a view of a portion of the full image

        This is equivalent to self[bounds]
        """
        if not isinstance(bounds, galsim.BoundsI):
            raise TypeError("bounds must be a galsim.BoundsI instance")
        subimage = self.image.subImage(bounds)
        # NB. The wcs is still accurate, since the sub-image uses the same (x,y) values
        # as the original image did for those pixels.  It's only once you recenter or
        # reorigin that you need to update the wcs.  So that's taken care of in im.shift.
        return Image(image=subimage, wcs=self.wcs)

    def setSubImage(self, bounds, rhs):
        """Set a portion of the full image to the values in another image

        This is equivalent to self[bounds] = rhs
        """
        self.subImage(bounds).image.copyFrom(rhs.image)

    def __getitem__(self, bounds):
        """Return a view of a portion of the full image
        """
        return self.subImage(bounds)

    def __setitem__(self, bounds, rhs):
        """Set a portion of the full image to the values in another image
        """
        self.setSubImage(bounds,rhs)

    def copyFrom(self, rhs):
        """Copy the contents of another image
        """
        self.image.copyFrom(rhs.image)

    def view(self, scale=None, wcs=None, origin=None, center=None, make_const=False):
        """Make a view of this image, which lets you change the scale, wcs, origin, etc.
        but view the same underlying data as the original image.

        If you do not provide either `scale` or `wcs`, the view will keep the same wcs
        as the current Image object.

        @param scale        If provided, use this as the pixel scale for the image. [default: None]
        @param wcs          If provided, use this as the wcs for the image. [default: None]
        @param origin       If profided, use this as the origin position of the view.
                            [default: None]
        @param center       If profided, use this as the center position of the view.
                            [default: None]
        @param make_const   Make the view's data array immutable. [default: False]
        """
        if origin is not None and center is not None:
            raise TypeError("Cannot provide both center and origin")

        if scale is not None:
            if wcs is not None:
                raise TypeError("Cannot provide both scale and wcs")
            wcs = galsim.PixelScale(scale)
        elif wcs is not None:
            if not isinstance(wcs,galsim.BaseWCS):
                raise TypeError("wcs parameters must be a galsim.BaseWCS instance")
        else:
            wcs = self.wcs

        if make_const:
            ret = Image(image=_galsim.ConstImageView[self.dtype](self.image.view()), wcs=wcs)
        else:
            ret = Image(image=self.image.view(), wcs=wcs)

        if origin is not None:
            ret.setOrigin(origin)
        elif center is not None:
            ret.setCenter(center)

        return ret

    def shift(self, *args, **kwargs):
        """Shift the pixel coordinates by some (integral) dx,dy.

        The arguments here may be either (dx, dy) or a PositionI instance.
        Or you can provide dx, dy as named kwargs.

        In terms of columns and rows, dx means a shift in the x value of each column in the
        array, and dy means a shift in the y value of each row.  In other words, the following
        will return the same value for ixy.  The shift function just changes the coordinates (x,y)
        used for that pixel:

            >>> ixy = im(x,y)
            >>> im.shift(3,9)
            >>> ixy = im(x+3, y+9)
        """
        delta = galsim.utilities.parse_pos_args(args, kwargs, 'dx', 'dy', integer=True)
        self._shift(delta)

    def _shift(self, delta):
        # The parse_pos_args function is a bit slow, so go directly to this point when we
        # call shift from setCenter or setOrigin.
        if delta.x != 0 or delta.y != 0:
            self.image.shift(delta)
            if self.wcs is not None:
                self.wcs = self.wcs.withOrigin(delta)

    def setCenter(self, *args, **kwargs):
        """Set the center of the image to the given (integral) (xcen, ycen)

        The arguments here may be either (xcen, ycen) or a PositionI instance.
        Or you can provide xcen, ycen as named kwargs.

        In terms of the rows and columns, xcen is the new x value for the central column, and ycen
        is the new y value of the central row.  For even-sized arrays, there is no central column
        or row, so the convention we adopt in this case is to round up.  For example:

            >>> im = galsim.Image(numpy.array(range(16),dtype=float).reshape((4,4)))
            >>> im(1,1)
            0.0
            >>> im(4,1)
            3.0
            >>> im(4,4)
            15.0
            >>> im(3,3)
            10.0
            >>> im.setCenter(0,0)
            >>> im(0,0)
            10.0
            >>> im(-2,-2)
            0.0
            >>> im(1,-2)
            3.0
            >>> im(1,1)
            15.0
            >>> im.setCenter(234,456)
            >>> im(234,456)
            10.0
            >>> im.bounds
            galsim.BoundsI(xmin=232, xmax=235, ymin=454, ymax=457)
        """
        cen = galsim.utilities.parse_pos_args(args, kwargs, 'xcen', 'ycen', integer=True)
        self._shift(cen - self.image.bounds.center())

    def setOrigin(self, *args, **kwargs):
        """Set the origin of the image to the given (integral) (x0, y0)

        The arguments here may be either (x0, y0) or a PositionI instance.
        Or you can provide x0, y0 as named kwargs.

        In terms of the rows and columns, x0 is the new x value for the first column,
        and y0 is the new y value of the first row.  For example:

            >>> im = galsim.Image(numpy.array(range(16),dtype=float).reshape((4,4)))
            >>> im(1,1)
            0.0
            >>> im(4,1)
            3.0
            >>> im(1,4)
            12.0
            >>> im(4,4)
            15.0
            >>> im.setOrigin(0,0)
            >>> im(0,0)
            0.0
            >>> im(3,0)
            3.0
            >>> im(0,3)
            12.0
            >>> im(3,3)
            15.0
            >>> im.setOrigin(234,456)
            >>> im(234,456)
            0.0
            >>> im.bounds
            galsim.BoundsI(xmin=234, xmax=237, ymin=456, ymax=459)
         """
        origin = galsim.utilities.parse_pos_args(args, kwargs, 'x0', 'y0', integer=True)
        self._shift(origin - self.image.bounds.origin())

    def center(self):
        """Return the current nominal center (xcen,ycen) of the image as a PositionI instance.

        In terms of the rows and columns, xcen is the x value for the central column, and ycen
        is the y value of the central row.  For even-sized arrays, there is no central column
        or row, so the convention we adopt in this case is to round up.  For example:

            >>> im = galsim.Image(numpy.array(range(16),dtype=float).reshape((4,4)))
            >>> im.center()
            galsim.PositionI(x=3, y=3)
            >>> im(im.center())
            10.0
            >>> im.setCenter(56,72)
            >>> im.center()
            galsim.PositionI(x=56, y=72)
            >>> im(im.center())
            10.0
        """
        return self.bounds.center()

    def trueCenter(self):
        """Return the current true center of the image as a PositionD instance.

        Unline the nominal center returned by im.center(), this value may be half-way between
        two pixels if the image has an even number of rows or columns.  It gives the position
        (x,y) at the exact center of the image, regardless of whether this is at the center of
        a pixel (integer value) or halfway between two (half-integer).  For example:

            >>> im = galsim.Image(numpy.array(range(16),dtype=float).reshape((4,4)))
            >>> im.center()
            galsim.PositionI(x=3, y=3)
            >>> im.trueCenter()
            galsim.PositionI(x=2.5, y=2.5)
            >>> im.setCenter(56,72)
            >>> im.center()
            galsim.PositionI(x=56, y=72)
            >>> im.trueCenter()
            galsim.PositionD(x=55.5, y=71.5)
            >>> im.setOrigin(0,0)
            >>> im.trueCenter()
            galsim.PositionD(x=1.5, y=1.5)
        """
        return self.bounds.trueCenter()

    def origin(self):
        """Return the origin of the image.  i.e. the (x,y) position of the lower-left pixel.

        In terms of the rows and columns, this is the (x,y) coordinate of the first column, and
        first row of the array.  For example:

            >>> im = galsim.Image(numpy.array(range(16),dtype=float).reshape((4,4)))
            >>> im.origin()
            galsim.PositionI(x=1, y=1)
            >>> im(im.origin())
            0.0
            >>> im.setOrigin(23,45)
            >>> im.origin()
            galsim.PositionI(x=23, y=45)
            >>> im(im.origin())
            0.0
            >>> im(23,45)
            0.0
            >>> im.bounds
            galsim.BoundsI(xmin=23, xmax=26, ymin=45, ymax=48)
        """
        return self.bounds.origin()

    def __call__(self, *args, **kwargs):
        """Get the pixel value at given position

        The arguments here may be either (x, y) or a PositionI instance.
        Or you can provide x, y as named kwargs.
        """
        pos = galsim.utilities.parse_pos_args(args, kwargs, 'x', 'y', integer=True)
        return self.image(pos.x, pos.y)

    def at(self, x, y):
        """This method is a synonym for im(x,y).  It is a bit faster than im(x,y), since GalSim
        does not have to parse the different options available for __call__.  (i.e. im(x,y) or
        im(pos) or im(x=x,y=y))
        """
        return self.image(x,y)

    def setValue(self, *args, **kwargs):
        """Set the pixel value at given (x,y) position

        The arguments here may be either (x, y, value) or (pos, value) where pos is a PositionI.
        Or you can provide x, y, value as named kwargs.
        """
        pos, value = galsim.utilities.parse_pos_args(args, kwargs, 'x', 'y', integer=True,
                                                     others=['value'])
        self.image.setValue(pos.x, pos.y, value)

    def fill(self, value):
        """Set all pixel values to the given `value`
        """
        self.image.fill(value)

    def setZero(self):
        """Set all pixel values to zero.
        """
        self.image.setZero()

    def invertSelf(self):
        """Set all pixel values to their inverse: x -> 1/x.
        """
        self.image.invertSelf()

    def calculateHLR(self, center=None, flux=None, flux_frac=0.5):
        """Returns the half-light radius of a drawn object.

        This method is equivalent to GSObject.calculateHLR when the object has already been
        been drawn onto an image.  Note that the profile should be drawn using a method that
        integrates over pixels and does not add noise. (The default method='auto' is acceptable.)

        If the image has a wcs other than a PixelScale, an AttributeError will be raised.

        @param center       The position in pixels to use for the center, r=0.
                            [default: self.trueCenter()]
        @param flux         The total flux.  [default: sum(self.array)]
        @param flux_frac    The fraction of light to be enclosed by the returned radius.
                            [default: 0.5]

        @returns an estimate of the half-light radius in physical units defined by the pixel scale.
        """
        if center is None:
            center = self.trueCenter()

        if flux is None:
            flux = np.sum(self.array)

        # Use radii at centers of pixels as approximation to the radial integral
        x,y = np.meshgrid(range(self.array.shape[1]), range(self.array.shape[0]))
        x = x - center.x + self.bounds.xmin
        y = y - center.y + self.bounds.ymin
        rsq = x*x + y*y

        # Sort by radius
        indx = np.argsort(rsq.ravel())
        rsqf = rsq.ravel()[indx]
        data = self.array.ravel()[indx]
        cumflux = np.cumsum(data)

        # Find the first value with cumflux > 0.5 * flux
        k = np.argmax(cumflux > flux_frac * flux)
        flux_k = cumflux[k] / flux  # normalize to unit total flux

        # Interpolate (linearly) between this and the previous value.
        if k == 0:
            hlrsq = rsqf[0] * (flux_frac / flux_k)
        else:
            fkm1 = cumflux[k-1] / flux
            # For brevity in the next formula:
            fk = flux_k
            f = flux_frac
            hlrsq = (rsqf[k-1] * (fk-f) + rsqf[k] * (f-fkm1)) / (fk-fkm1)

        # This has all been done in pixels.  So normalize according to the pixel scale.
        hlr = np.sqrt(hlrsq) * self.scale

        return hlr


    def calculateMomentRadius(self, center=None, flux=None, rtype='det'):
        """Returns an estimate of the radius based on unweighted second moments of a drawn object.

        This method is equivalent to GSObject.calculateMomentRadius when the object has already
        been drawn onto an image.  Note that the profile should be drawn using a method that
        integrates over pixels and does not add noise. (The default method='auto' is acceptable.)

        If the image has a wcs other than a PixelScale, an AttributeError will be raised.

        @param center       The position in pixels to use for the center, r=0.
                            [default: self.trueCenter()]
        @param flux         The total flux.  [default: sum(self.array)]
        @param rtype        There are three options for this parameter:
                            - 'trace' means return sqrt(T/2)
                            - 'det' means return det(Q)^1/4
                            - 'both' means return both: (sqrt(T/2), det(Q)^1/4)
                            [default: 'det']

        @returns an estimate of the radius in physical units defined by the pixel scale
                 (or both estimates if rtype == 'both').
        """
        if rtype not in ['trace', 'det', 'both']:
            raise ValueError("rtype must be one of 'trace', 'det', or 'both'")

        if center is None:
            center = self.trueCenter()

        if flux is None:
            flux = np.sum(self.array)

        # Use radii at centers of pixels as approximation to the radial integral
        x,y = np.meshgrid(range(self.array.shape[1]), range(self.array.shape[0]))
        x = x - center.x + self.bounds.xmin
        y = y - center.y + self.bounds.ymin

        if rtype in ['trace', 'both']:
            # Calculate trace measure:
            rsq = x*x + y*y
            Irr = np.sum(rsq * self.array) / flux

            # This has all been done in pixels.  So normalize according to the pixel scale.
            sigma_trace = (Irr/2.)**0.5 * self.scale

        if rtype in ['det', 'both']:
            # Calculate det measure:
            Ixx = np.sum(x*x * self.array) / flux
            Iyy = np.sum(y*y * self.array) / flux
            Ixy = np.sum(x*y * self.array) / flux

            # This has all been done in pixels.  So normalize according to the pixel scale.
            sigma_det = (Ixx*Iyy-Ixy**2)**0.25 * self.scale

        if rtype == 'trace':
            return sigma_trace
        elif rtype == 'det':
            return sigma_det
        else:
            return sigma_trace, sigma_det


    def calculateFWHM(self, center=None, Imax=0.):
        """Returns the full-width half-maximum (FWHM) of a drawn object.

        This method is equivalent to GSObject.calculateMomentRadius when the object has already
        been drawn onto an image.  Note that the profile should be drawn using a method that
        does not integrate over pixels, so either 'sb' or 'no_pixel'.  Also, if there is a
        significant amount of noise in the image, this method may not work well.

        If the image has a wcs other than a PixelScale, an AttributeError will be raised.

        @param center       The position in pixels to use for the center, r=0.
                            [default: self.trueCenter()]
        @param Imax         The maximum surface brightness.  [default: max(self.array)]
                            Note: If Imax is provided, and the maximum pixel value is larger than
                            this value, Imax will be updated to use the larger value.

        @returns an estimate of the full-width half-maximum in physical units defined by the
                 pixel scale.
        """
        if center is None:
            center = self.trueCenter()

        # If the full image has a larger maximum, use that.
        Imax2 = np.max(self.array)
        if Imax2 > Imax: Imax = Imax2

        # Use radii at centers of pixels.
        x,y = np.meshgrid(range(self.array.shape[1]), range(self.array.shape[0]))
        x = x - center.x + self.bounds.xmin
        y = y - center.y + self.bounds.ymin
        rsq = x*x + y*y

        # Sort by radius
        indx = np.argsort(rsq.ravel())
        rsqf = rsq.ravel()[indx]
        data = self.array.ravel()[indx]

        # Find the first value with I < 0.5 * Imax
        k = np.argmax(data < 0.5 * Imax)
        Ik = data[k] / Imax

        # Interpolate (linearly) between this and the previous value.
        if k == 0:
            rsqhm = rsqf[0] * (0.5 / Ik)
        else:
            Ikm1 = data[k-1] / Imax
            rsqhm = (rsqf[k-1] * (Ik-0.5) + rsqf[k] * (0.5-Ikm1)) / (Ik-Ikm1)

        # This has all been done in pixels.  So normalize according to the pixel scale.
        fwhm = 2. * np.sqrt(rsqhm) * self.scale

        return fwhm

    def __eq__(self, other):
        # Note that numpy.array_equal can return True if the dtypes of the two arrays involved are
        # different, as long as the contents of the two arrays are logically the same.  For example:
        #
        # >>> double_array = np.arange(1024).reshape(32, 32)*np.pi
        # >>> int_array = np.arange(1024).reshape(32, 32)
        # >>> assert galsim.ImageD(int_array) == galsim.ImageF(int_array) # passes
        # >>> assert galsim.ImageD(double_array) == galsim.ImageF(double_array) # fails

        return ( isinstance(other, Image) and
                 self.bounds == other.bounds and
                 self.wcs == other.wcs and
                 np.array_equal(self.array,other.array) )
    def __ne__(self, other): return not self.__eq__(other)

    __hash__ = None


# These are essentially aliases for the regular Image with the correct dtype
def ImageS(*args, **kwargs):
    """Alias for galsim.Image(..., dtype=numpy.int16)
    """
    kwargs['dtype'] = np.int16
    return Image(*args, **kwargs)

def ImageI(*args, **kwargs):
    """Alias for galsim.Image(..., dtype=numpy.int32)
    """
    kwargs['dtype'] = np.int32
    return Image(*args, **kwargs)

def ImageF(*args, **kwargs):
    """Alias for galsim.Image(..., dtype=numpy.float32)
    """
    kwargs['dtype'] = np.float32
    return Image(*args, **kwargs)

def ImageD(*args, **kwargs):
    """Alias for galsim.Image(..., dtype=numpy.float64)
    """
    kwargs['dtype'] = np.float64
    return Image(*args, **kwargs)


################################################################################################
#
# Now we have to make some modifications to the C++ layer objects.  Mostly adding some
# arithemetic functions, so they work more intuitively.
#

def Image_setitem(self, key, value):
    self.subImage(key).copyFrom(value)

def Image_getitem(self, key):
    return self.subImage(key)

# Define a utility function to be used by the arithmetic functions below
def check_image_consistency(im1, im2):
    if ( isinstance(im2, Image) or
         type(im2) in _galsim.ImageAlloc.values() or
         type(im2) in _galsim.ImageView.values() or
         type(im2) in _galsim.ConstImageView.values()):
        if im1.array.shape != im2.array.shape:
            raise ValueError("Image shapes are inconsistent")

def Image_add(self, other):
    result = self.copy()
    result += other
    return result

def Image_iadd(self, other):
    check_image_consistency(self, other)
    try:
        a = other.array
        dt = a.dtype
    except AttributeError:
        a = other
        dt = type(a)
    if dt == self.array.dtype:
        self.array[:,:] += a
    else:
        self.array[:,:] = (self.array + a).astype(self.array.dtype)
    return self

def Image_sub(self, other):
    result = self.copy()
    result -= other
    return result

def Image_rsub(self, other):
    result = self.copy()
    result *= -1
    result += other
    return result

def Image_isub(self, other):
    check_image_consistency(self, other)
    try:
        a = other.array
        dt = a.dtype
    except AttributeError:
        a = other
        dt = type(a)
    if dt == self.array.dtype:
        self.array[:,:] -= a
    else:
        self.array[:,:] = (self.array - a).astype(self.array.dtype)
    return self

def Image_mul(self, other):
    result = self.copy()
    result *= other
    return result

def Image_imul(self, other):
    check_image_consistency(self, other)
    try:
        a = other.array
        dt = a.dtype
    except AttributeError:
        a = other
        dt = type(a)
    if dt == self.array.dtype:
        self.array[:,:] *= a
    else:
        self.array[:,:] = (self.array * a).astype(self.array.dtype)
    return self

def Image_div(self, other):
    result = self.copy()
    result /= other
    return result

def Image_rdiv(self, other):
    result = self.copy()
    result.invertSelf()
    result *= other
    return result

def Image_idiv(self, other):
    check_image_consistency(self, other)
    try:
        a = other.array
        dt = a.dtype
    except AttributeError:
        a = other
        dt = type(a)
    if dt == self.array.dtype:
        # Try numpy's idiv, but if that doesn't work, coerce it into the existing dtype.
        try:
            self.array[:,:] /= a
        except TypeError:
            self.array[:,:] = (self.array / a).astype(self.array.dtype)
    else:
        self.array[:,:] = (self.array / a).astype(self.array.dtype)
    return self

def Image_pow(self, other):
    result = self.copy()
    result **= other
    return result

def Image_ipow(self, other):
    if not isinstance(other, int) and not isinstance(other, float):
        raise TypeError("Can only raise an image to a float or int power!")
    self.array[:,:] **= other
    return self

def Image_neg(self, other):
    result = self.copy()
    result *= -1
    return result

# Define &, ^ and | only for integer-type images
def Image_and(self, other):
    result = self.copy()
    result &= other
    return result

def Image_iand(self, other):
    check_image_consistency(self, other)
    try:
        self.array[:,:] &= other.array
    except AttributeError:
        self.array[:,:] &= other
    return self

def Image_xor(self, other):
    result = self.copy()
    result ^= other
    return result

def Image_ixor(self, other):
    check_image_consistency(self, other)
    try:
        self.array[:,:] ^= other.array
    except AttributeError:
        self.array[:,:] ^= other
    return self

def Image_or(self, other):
    result = self.copy()
    result |= other
    return result

def Image_ior(self, other):
    check_image_consistency(self, other)
    try:
        self.array[:,:] |= other.array
    except AttributeError:
        self.array[:,:] |= other
    return self

def Image_copy(self):
    # self can be an ImageAlloc or an ImageView, but the return type needs to be an ImageAlloc.
    # So use the array.dtype.type attribute to get the type of the underlying data,
    # which in turn can be used to index our ImageAlloc dictionary:
    return _galsim.ImageAlloc[self.array.dtype.type](self)

# Some functions to enable pickling of images
def ImageView_getinitargs(self):
    return self.array, self.xmin, self.ymin

# An image is really pickled as an ImageView
def ImageAlloc_getstate(self):
    return self.array, self.xmin, self.ymin

def ImageAlloc_setstate(self, args):
    self_type = args[0].dtype.type
    self.__class__ = _galsim.ImageView[self_type]
    self.__init__(*args)

# inject the arithmetic operators as methods of the Image class:
Image.__add__ = Image_add
Image.__radd__ = Image_add
Image.__iadd__ = Image_iadd
Image.__sub__ = Image_sub
Image.__rsub__ = Image_rsub
Image.__isub__ = Image_isub
Image.__mul__ = Image_mul
Image.__rmul__ = Image_mul
Image.__imul__ = Image_imul
Image.__div__ = Image_div
Image.__rdiv__ = Image_div
Image.__truediv__ = Image_div
Image.__rtruediv__ = Image_rdiv
Image.__idiv__ = Image_idiv
Image.__itruediv__ = Image_idiv
Image.__ipow__ = Image_ipow
Image.__pow__ = Image_pow
Image.__neg__ = Image_neg
Image.__and__ = Image_and
Image.__xor__ = Image_xor
Image.__or__ = Image_or
Image.__iand__ = Image_iand
Image.__ixor__ = Image_ixor
Image.__ior__ = Image_ior

# inject these as methods of ImageAlloc classes
for Class in _galsim.ImageAlloc.values():
    Class.__setitem__ = Image_setitem
    Class.__getitem__ = Image_getitem
    Class.__add__ = Image_add
    Class.__radd__ = Image_add
    Class.__iadd__ = Image_iadd
    Class.__sub__ = Image_sub
    Class.__rsub__ = Image_rsub
    Class.__isub__ = Image_isub
    Class.__mul__ = Image_mul
    Class.__rmul__ = Image_mul
    Class.__imul__ = Image_imul
    Class.__div__ = Image_div
    Class.__rdiv__ = Image_div
    Class.__truediv__ = Image_div
    Class.__rtruediv__ = Image_rdiv
    Class.__idiv__ = Image_idiv
    Class.__itruediv__ = Image_idiv
    Class.__ipow__ = Image_ipow
    Class.__neg__ = Image_neg
    Class.__pow__ = Image_pow
    Class.copy = Image_copy
    Class.__getstate_manages_dict__ = 1
    Class.__getstate__ = ImageAlloc_getstate
    Class.__setstate__ = ImageAlloc_setstate
    Class.__hash__ = None

for Class in _galsim.ImageView.values():
    Class.__setitem__ = Image_setitem
    Class.__getitem__ = Image_getitem
    Class.__add__ = Image_add
    Class.__radd__ = Image_add
    Class.__iadd__ = Image_iadd
    Class.__sub__ = Image_sub
    Class.__rsub__ = Image_rsub
    Class.__isub__ = Image_isub
    Class.__mul__ = Image_mul
    Class.__rmul__ = Image_mul
    Class.__imul__ = Image_imul
    Class.__div__ = Image_div
    Class.__rdiv__ = Image_rdiv
    Class.__truediv__ = Image_div
    Class.__rtruediv__ = Image_rdiv
    Class.__idiv__ = Image_idiv
    Class.__itruediv__ = Image_idiv
    Class.__ipow__ = Image_ipow
    Class.__pow__ = Image_pow
    Class.__neg__ = Image_neg
    Class.copy = Image_copy
    Class.__getinitargs__ = ImageView_getinitargs
    Class.__hash__ = None

for Class in _galsim.ConstImageView.values():
    Class.__getitem__ = Image_getitem
    Class.__add__ = Image_add
    Class.__radd__ = Image_add
    Class.__sub__ = Image_sub
    Class.__rsub__ = Image_rsub
    Class.__mul__ = Image_mul
    Class.__rmul__ = Image_mul
    Class.__div__ = Image_div
    Class.__rdiv__ = Image_rdiv
    Class.__truediv__ = Image_div
    Class.__rtruediv__ = Image_rdiv
    Class.__pow__ = Image_pow
    Class.__neg__ = Image_neg
    Class.copy = Image_copy
    Class.__getinitargs__ = ImageView_getinitargs
    Class.__hash__ = None

for int_type in [ np.int16, np.int32 ]:
    for Class in [ _galsim.ImageAlloc[int_type], _galsim.ImageView[int_type],
                   _galsim.ConstImageView[int_type] ]:
        Class.__and__ = Image_and
        Class.__xor__ = Image_xor
        Class.__or__ = Image_or
    for Class in [ _galsim.ImageAlloc[int_type], _galsim.ImageView[int_type] ]:
        Class.__iand__ = Image_iand
        Class.__ixor__ = Image_ixor
        Class.__ior__ = Image_ior

del Class    # cleanup public namespace

galsim._galsim.ImageAllocS.__repr__ = lambda self: 'galsim._galsim.ImageAllocS(%r,%r)'%(
        self.bounds, self.array)
galsim._galsim.ImageAllocI.__repr__ = lambda self: 'galsim._galsim.ImageAllocI(%r,%r)'%(
        self.bounds, self.array)
galsim._galsim.ImageAllocF.__repr__ = lambda self: 'galsim._galsim.ImageAllocF(%r,%r)'%(
        self.bounds, self.array)
galsim._galsim.ImageAllocD.__repr__ = lambda self: 'galsim._galsim.ImageAllocD(%r,%r)'%(
        self.bounds, self.array)

galsim._galsim.ImageViewS.__repr__ = lambda self: 'galsim._galsim.ImageViewS(%r,%r,%r)'%(
        self.array, self.xmin, self.ymin)
galsim._galsim.ImageViewI.__repr__ = lambda self: 'galsim._galsim.ImageViewI(%r,%r,%r)'%(
        self.array, self.xmin, self.ymin)
galsim._galsim.ImageViewF.__repr__ = lambda self: 'galsim._galsim.ImageViewF(%r,%r,%r)'%(
        self.array, self.xmin, self.ymin)
galsim._galsim.ImageViewD.__repr__ = lambda self: 'galsim._galsim.ImageViewD(%r,%r,%r)'%(
        self.array, self.xmin, self.ymin)

galsim._galsim.ConstImageViewS.__repr__ = lambda self: 'galsim._galsim.ConstImageViewS(%r,%r,%r)'%(
        self.array, self.xmin, self.ymin)
galsim._galsim.ConstImageViewI.__repr__ = lambda self: 'galsim._galsim.ConstImageViewI(%r,%r,%r)'%(
        self.array, self.xmin, self.ymin)
galsim._galsim.ConstImageViewF.__repr__ = lambda self: 'galsim._galsim.ConstImageViewF(%r,%r,%r)'%(
        self.array, self.xmin, self.ymin)
galsim._galsim.ConstImageViewD.__repr__ = lambda self: 'galsim._galsim.ConstImageViewD(%r,%r,%r)'%(
        self.array, self.xmin, self.ymin)
