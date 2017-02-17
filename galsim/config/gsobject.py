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
import galsim
import logging

# This file handles the building of GSObjects in the config['psf'] and config['gal'] fields.
# This file includes many of the simple object types.  Additional types are defined in
# gsobject_ring.py, input_real.py, and input_cosmos.py.

# This module-level dict will store all the registered gsobject types.
# See the RegisterObjectType function at the end of this file.
# The keys will be the (string) names of the object types, and the values are the function
# to call to build an object of that type.
valid_gsobject_types = {}

# A list of gsobject types that define a block of inter-related stamps.  This is only necessary
# to support the deprecated Ring gsobject type.  Once that feature is fully removed, we can 
# remove this structure.
block_gsobject_types = []

class SkipThisObject(Exception):
    """
    A class that a builder can throw to indicate that nothing went wrong, but for some
    reason, this particular object should be skipped and just move onto the next object.
    The constructor takes an optional message that will be output to the logger if 
    logging is active.
    """
    def __init__(self, message=None):
        # Using self.message gives a deprecation warning.  Avoid this by using a different name.
        self.msg = message


def BuildGSObject(config, key, base=None, gsparams={}, logger=None):
    """Build a GSObject from the parameters in config[key].

    @param config       A dict with the configuration information.
    @param key          The key name in config indicating which object to build.
    @param base         The base dict of the configuration. [default: config]
    @param gsparams     Optionally, provide non-default GSParams items.  Any `gsparams` specified
                        at this level will be added to the list.  This should be a dict with
                        whatever kwargs should be used in constructing the GSParams object.
                        [default: {}]
    @param logger       Optionally, provide a logger for logging debug statements.
                        [default: None]

    @returns the tuple `(gsobject, safe)`, where `gsobject` is the built object, and `safe` is
             a bool that says whether it is safe to use this object again next time.
    """
    if base is None:
        base = config

    if logger:
        logger.debug('obj %d: Start BuildGSObject %s',base['obj_num'],key)

    # If key isn't in config, then just return None.
    try:
        param = config[key]
    except KeyError:
        return None, True

    # Save these, so we can edit them based on parameters at this level in the tree to take
    # effect on all lower branches, and then we can reset it back to this at the end.
    orig_index_key = base.get('index_key',None)
    orig_rng = base.get('rng',None)

    # Check what index key we want to use for this object.
    # Note: this call will also set base['index_key'] and base['rng'] to the right values
    index, index_key = galsim.config.value._get_index(param, base)

    # Get the type to be parsed.
    if not 'type' in param:
        raise AttributeError("type attribute required in config.%s"%key)
    type_name = param['type']

    # If we are repeating, then we get to use the current object for repeat times.
    if 'repeat' in param:
        repeat = galsim.config.ParseValue(param, 'repeat', base, int)[0]
    else:
        repeat = 1

    # Check if we can use the current cached object
    if ('current_val' in param and
            (param['current_safe'] or param['current_index']//repeat == index//repeat)):
        # If logging, explain why we are using the current object.
        if logger:
            if param['current_safe']:
                logger.debug('obj %d: current is safe',base['obj_num'])
            elif repeat > 1:
                logger.debug('obj %d: repeat = %d, index = %d, use current object',
                             base['obj_num'],repeat,index)
            else:
                logger.debug('obj %d: This object is already current', base['obj_num'])

        # Make sure to reset these values in case they were changed.
        if orig_index_key is not None:
            base['index_key'] = orig_index_key
        if orig_rng is not None:
            base['rng'] = orig_rng

        return param['current_val'], param['current_safe']

    # Check if we need to skip this object
    if 'skip' in param:
        skip = galsim.config.ParseValue(param, 'skip', base, bool)[0]
        if skip:
            if logger:
                logger.debug('obj %d: Skipping because field skip=True',base['obj_num'])
            raise SkipThisObject()

    # Set up the initial default list of attributes to ignore while building the object:
    ignore = [
        'dilate', 'dilation', 'ellip', 'rotate', 'rotation', 'scale_flux',
        'magnify', 'magnification', 'shear', 'shift',
        'gsparams', 'skip',
        'current_val', 'current_safe', 'current_value_type', 'current_index', 'current_index_key',
        'index_key', 'repeat'
    ]
    # There are a few more that are specific to which key we have.
    if key == 'gal':
        ignore += [ 'resolution', 'signal_to_noise', 'redshift', 're_from_res' ]
    elif key == 'psf':
        ignore += [ 'saved_re' ]
    else:
        # As long as key isn't psf, allow resolution.
        # Ideally, we'd like to check that it's something within the gal hierarchy, but
        # I don't know an easy way to do that.
        ignore += [ 'resolution' , 're_from_res' ]

    # Allow signal_to_noise for PSFs only if there is not also a galaxy.
    if 'gal' not in base and key == 'psf':
        ignore += [ 'signal_to_noise']

    # If we are specifying the size according to a resolution, then we 
    # need to get the PSF's half_light_radius.
    if 'resolution' in param:
        if 'psf' not in base:
            raise AttributeError(
                "Cannot use gal.resolution if no psf is set.")
        if 'saved_re' not in base['psf']:
            raise AttributeError(
                'Cannot use gal.resolution with psf.type = %s'%base['psf']['type'])
        psf_re = base['psf']['saved_re']
        resolution = galsim.config.ParseValue(param, 'resolution', base, float)[0]
        gal_re = resolution * psf_re
        if 're_from_res' not in param:
            # The first time, check that half_light_radius isn't also specified.
            if 'half_light_radius' in param:
                raise AttributeError(
                    'Cannot specify both gal.resolution and gal.half_light_radius')
            param['re_from_res'] = True
        param['half_light_radius'] = gal_re

    # Make sure the PSF gets flux=1 unless explicitly overridden by the user.
    if key == 'psf' and 'flux' not in param and 'signal_to_noise' not in param:
        param['flux'] = 1

    if 'gsparams' in param:
        gsparams = UpdateGSParams(gsparams, param['gsparams'], base)

    # See if this type has a specialized build function:
    if type_name in valid_gsobject_types:
        build_func = valid_gsobject_types[type_name]
        gsobject, safe = build_func(param, base, ignore, gsparams, logger)
    # Next, we check if this name is in the galsim dictionary.
    elif type_name in galsim.__dict__:
        if issubclass(galsim.__dict__[type_name], galsim.GSObject):
            gsobject, safe = _BuildSimple(param, base, ignore, gsparams, logger)
        else:
            TypeError("Input config type = %s is not a GSObject."%type_name)
    # Otherwise, it's not a valid type.
    else:
        raise NotImplementedError("Unrecognised config type = %s"%type_name)

    # If this is a psf, try to save the half_light_radius in case gal uses resolution.
    if key == 'psf':
        try : 
            param['saved_re'] = gsobject.getHalfLightRadius()
        except :
            pass
    
    # Apply any dilation, ellip, shear, etc. modifications.
    gsobject, safe1 = TransformObject(gsobject, param, base, logger)
    safe = safe and safe1
 
    param['current_val'] = gsobject
    param['current_safe'] = safe
    param['current_value_type'] = None
    param['current_index'] = index
    param['current_index_key'] = index_key

    # Reset these values in case they were changed.
    if orig_index_key is not None:
        base['index_key'] = orig_index_key
    if orig_rng is not None:
        base['rng'] = orig_rng

    return gsobject, safe


def UpdateGSParams(gsparams, config, base):
    """@brief Add additional items to the `gsparams` dict based on config['gsparams'].
    """
    opt = galsim.GSObject._gsparams
    kwargs, safe = galsim.config.GetAllParams(config, base, opt=opt)
    # When we update gsparams, we don't want to corrupt the original, so we need to
    # make a copy first, then update with kwargs.
    ret = {}
    ret.update(gsparams)
    ret.update(kwargs)
    return ret


# 
# The following are private functions to implement the simpler GSObject types.
# These are not imported into galsim.config namespace.
#

def _BuildSimple(config, base, ignore, gsparams, logger):
    """@brief Build a simple GSObject (i.e. one without a specialized _Build function) or
    any other GalSim object that defines _req_params, _opt_params and _single_params.
    """
    # Build the kwargs according to the various params objects in the class definition.
    type_name = config['type']
    if type_name in galsim.__dict__:
        init_func = eval("galsim."+type_name)
    else:
        init_func = eval(type_name)
    if logger:
        logger.debug('obj %d: BuildSimple for type = %s',base['obj_num'],type_name)

    kwargs, safe = galsim.config.GetAllParams(config, base,
                                              req = init_func._req_params,
                                              opt = init_func._opt_params,
                                              single = init_func._single_params,
                                              ignore = ignore)
    if gsparams: kwargs['gsparams'] = galsim.GSParams(**gsparams)

    if init_func._takes_rng:
        if 'rng' not in base:
            raise ValueError("No base['rng'] available for type = %s"%type_name)
        kwargs['rng'] = base['rng']
        safe = False

    if logger:
        logger.debug('obj %d: kwargs = %s',base['obj_num'],kwargs)

    # Finally, after pulling together all the params, try making the GSObject.
    return init_func(**kwargs), safe


def _BuildNone(config, base, ignore, gsparams, logger):
    """@brief Special type=None returns None.
    """
    return None, True


def _BuildAdd(config, base, ignore, gsparams, logger):
    """@brief  Build a Sum object.
    """
    req = { 'items' : list }
    opt = { 'flux' : float }
    # Only Check, not Get.  We need to handle items a bit differently, since it's a list.
    galsim.config.CheckAllParams(config, req=req, opt=opt, ignore=ignore)

    gsobjects = []
    items = config['items']
    if not isinstance(items,list):
        raise AttributeError("items entry for type=Add is not a list.")
    safe = True

    for i in range(len(items)):
        gsobject, safe1 = BuildGSObject(items, i, base, gsparams, logger)
        # Skip items with flux=0
        if 'flux' in items[i] and galsim.config.GetCurrentValue('flux',items[i],float,base) == 0.:
            if logger:
                logger.debug('obj %d: Not including component with flux == 0',base['obj_num'])
            continue
        safe = safe and safe1
        gsobjects.append(gsobject)

    if len(gsobjects) == 0:
        raise ValueError("No valid items for type=Add")
    elif len(gsobjects) == 1:
        gsobject = gsobjects[0]
    else:
        # Special: if the last item in a Sum doesn't specify a flux, we scale it
        # to bring the total flux up to 1.
        if ('flux' not in items[-1]) and all('flux' in item for item in items[0:-1]):
            sum = 0
            for item in items[0:-1]:
                sum += galsim.config.GetCurrentValue('flux',item,float,base)
            f = 1. - sum
            if (f < 0):
                import warnings
                warnings.warn(
                    "Automatically scaling the last item in Sum to make the total flux\n" +
                    "equal 1 requires the last item to have negative flux = %f"%f)
            gsobjects[-1] = gsobjects[-1].withFlux(f)
        if gsparams: gsparams = galsim.GSParams(**gsparams)
        else: gsparams = None
        gsobject = galsim.Add(gsobjects,gsparams=gsparams)

    if 'flux' in config:
        flux, safe1 = galsim.config.ParseValue(config, 'flux', base, float)
        if logger:
            logger.debug('obj %d: flux == %f',base['obj_num'],flux)
        gsobject = gsobject.withFlux(flux)
        safe = safe and safe1

    return gsobject, safe

def _BuildConvolve(config, base, ignore, gsparams, logger):
    """@brief  Build a Convolution object.
    """
    req = { 'items' : list }
    opt = { 'flux' : float }
    # Only Check, not Get.  We need to handle items a bit differently, since it's a list.
    galsim.config.CheckAllParams(config, req=req, opt=opt, ignore=ignore)

    gsobjects = []
    items = config['items']
    if not isinstance(items,list):
        raise AttributeError("items entry for type=Convolve is not a list.")
    safe = True
    for i in range(len(items)):
        gsobject, safe1 = BuildGSObject(items, i, base, gsparams, logger)
        safe = safe and safe1
        gsobjects.append(gsobject)

    if len(gsobjects) == 0:
        raise ValueError("No valid items for type=Convolve")
    elif len(gsobjects) == 1:
        gsobject = gsobjects[0]
    else:
        if gsparams: gsparams = galsim.GSParams(**gsparams)
        else: gsparams = None
        gsobject = galsim.Convolve(gsobjects,gsparams=gsparams)
    
    if 'flux' in config:
        flux, safe1 = galsim.config.ParseValue(config, 'flux', base, float)
        if logger:
            logger.debug('obj %d: flux == %f',base['obj_num'],flux)
        gsobject = gsobject.withFlux(flux)
        safe = safe and safe1

    return gsobject, safe

def _BuildList(config, base, ignore, gsparams, logger):
    """@brief  Build a GSObject selected from a List.
    """
    req = { 'items' : list }
    opt = { 'index' : float , 'flux' : float }
    # Only Check, not Get.  We need to handle items a bit differently, since it's a list.
    galsim.config.CheckAllParams(config, req=req, opt=opt, ignore=ignore)

    items = config['items']
    if not isinstance(items,list):
        raise AttributeError("items entry for type=List is not a list.")

    # Setup the indexing sequence if it hasn't been specified using the length of items.
    galsim.config.SetDefaultIndex(config, len(items))
    index, safe = galsim.config.ParseValue(config, 'index', base, int)
    if index < 0 or index >= len(items):
        raise AttributeError("index %d out of bounds for List"%index)

    gsobject, safe1 = BuildGSObject(items, index, base, gsparams, logger)
    safe = safe and safe1

    if 'flux' in config:
        flux, safe1 = galsim.config.ParseValue(config, 'flux', base, float)
        if logger:
            logger.debug('obj %d: flux == %f',base['obj_num'],flux)
        gsobject = gsobject.withFlux(flux)
        safe = safe and safe1

    return gsobject, safe

def _BuildOpticalPSF(config, base, ignore, gsparams, logger):
    """@brief Build an OpticalPSF.
    """
    kwargs, safe = galsim.config.GetAllParams(config, base,
        req = galsim.OpticalPSF._req_params,
        opt = galsim.OpticalPSF._opt_params,
        single = galsim.OpticalPSF._single_params,
        ignore = [ 'aberrations' ] + ignore)
    if gsparams: kwargs['gsparams'] = galsim.GSParams(**gsparams)

    if 'aberrations' in config:
        aber_list = [0.0] * 4  # Initial 4 values are ignored.
        aberrations = config['aberrations']
        if not isinstance(aberrations,list):
            raise AttributeError("aberrations entry for config.OpticalPSF entry is not a list.")
        for i in range(len(aberrations)):
            value, safe1 = galsim.config.ParseValue(aberrations, i, base, float)
            aber_list.append(value)
            safe = safe and safe1
        kwargs['aberrations'] = aber_list
            
    return galsim.OpticalPSF(**kwargs), safe


#
# Now the functions for performing transformations
#

def TransformObject(gsobject, config, base, logger):
    """@brief Applies ellipticity, rotation, gravitational shearing and centroid shifting to a
    supplied GSObject, in that order.

    @returns transformed GSObject.
    """
    # The transformations are applied in the following order:
    _transformation_list = [
        ('dilate', _Dilate),
        ('dilation', _Dilate),
        ('ellip', _Shear),
        ('rotate', _Rotate),
        ('rotation', _Rotate),
        ('scale_flux', _ScaleFlux),
        ('shear', _Shear),
        ('magnify', _Magnify),
        ('magnification', _Magnify),
        ('shift', _Shift),
    ]

    safe = True
    for key, func in _transformation_list:
        if key in config:
            gsobject, safe1 = func(gsobject, config, key, base, logger)
            safe = safe and safe1
    return gsobject, safe

def _Shear(gsobject, config, key, base, logger):
    shear, safe = galsim.config.ParseValue(config, key, base, galsim.Shear)
    if logger:
        logger.debug('obj %d: shear = %f,%f',base['obj_num'],shear.g1,shear.g2)
    gsobject = gsobject.shear(shear)
    return gsobject, safe

def _Rotate(gsobject, config, key, base, logger):
    theta, safe = galsim.config.ParseValue(config, key, base, galsim.Angle)
    if logger:
        logger.debug('obj %d: theta = %f rad',base['obj_num'],theta.rad())
    gsobject = gsobject.rotate(theta)
    return gsobject, safe

def _ScaleFlux(gsobject, config, key, base, logger):
    flux_ratio, safe = galsim.config.ParseValue(config, key, base, float)
    if logger:
        logger.debug('obj %d: flux_ratio  = %f',base['obj_num'],flux_ratio)
    gsobject = gsobject * flux_ratio
    return gsobject, safe

def _Dilate(gsobject, config, key, base, logger):
    scale, safe = galsim.config.ParseValue(config, key, base, float)
    if logger:
        logger.debug('obj %d: scale  = %f',base['obj_num'],scale)
    gsobject = gsobject.dilate(scale)
    return gsobject, safe

def _Magnify(gsobject, config, key, base, logger):
    mu, safe = galsim.config.ParseValue(config, key, base, float)
    if logger:
        logger.debug('obj %d: mu  = %f',base['obj_num'],mu)
    gsobject = gsobject.magnify(mu)
    return gsobject, safe

def _Shift(gsobject, config, key, base, logger):
    shift, safe = galsim.config.ParseValue(config, key, base, galsim.PositionD)
    if logger:
        logger.debug('obj %d: shift  = %f,%f',base['obj_num'],shift.x,shift.y)
    gsobject = gsobject.shift(shift.x,shift.y)
    return gsobject, safe

def _GetMinimumBlock(config, base):
    """Get the minimum number of objects that should be done on the same process for a 
    particular object configuration.

    This function is only needed for backwards-compatibility support of gsobject type=Ring.

    @param config       A dict with the configuration information.
    @param base         The base dict of the configuration. [default: config]
    """
    if isinstance(config, dict) and 'type' in config:
        type_name = config['type']
        if type_name in block_gsobject_types:
            num = galsim.config.ParseValue(config, 'num', base, int)[0]
            return num
        else:
            return 1
    else:
        return 1


def RegisterObjectType(type_name, build_func, input_type=None, _is_block=False):
    """Register an object type for use by the config apparatus.

    A few notes about the signature of the build functions:

    1. The config parameter is the dict for the current object to be generated.  So it should
       be the case that config['type'] == type_name.
    2. The base parameter is the original config dict being processed.
    3. The ignore parameter  is a list of items that should be ignored in the config dict if they 
       are present and not valid for the object being built.
    4. The gsparams parameter is a dict of kwargs that should be used to build a GSParams object
       to use when building this object.
    5. The logger parameter is a logging.Logger object to use for logging progress if desired.
    6. The return value of build_func should be a tuple consisting of the object and a boolean,
       safe, which indicates whether the generated object is safe to use again rather than
       regenerate for subsequent postage stamps. e.g. if a PSF has all constant values, then it
       can be used for all the galaxies in a simulation, which lets it keep any FFTs that it has
       performed internally.  OpticalPSF is a good example of where this can have a significant
       speed up.

    @param type_name        The name of the 'type' specification in the config dict.
    @param build_func       A function to build a GSObject from the config information.
                            The call signature is
                                obj, safe = Build(config, base, ignore, gsparams, logger)
    @param input_type       If the type utilises an input object, give the key name of the input
                            type here.  (If it uses more than one, this may be a list.)
                            [default: None]
    """
    # Note: the _is_block parameter is an undocumented feature only needed to support the
    # now-deprecated type=Ring.  Once that feature is fully removed, we can remove the _is_block
    # parameter here.
    valid_gsobject_types[type_name] = build_func
    if _is_block:
        block_gsobject_types.append(type_name)
    if input_type is not None:
        from .input import RegisterInputConnectedType
        if isinstance(input_type, list):
            for key in input_type:
                RegisterInputConnectedType(key, type_name)
        else:
            RegisterInputConnectedType(input_type, type_name)

RegisterObjectType('None', _BuildNone)
RegisterObjectType('Add', _BuildAdd)
RegisterObjectType('Sum', _BuildAdd)
RegisterObjectType('Convolve', _BuildConvolve)
RegisterObjectType('Convolution', _BuildConvolve)
RegisterObjectType('List', _BuildList)
RegisterObjectType('OpticalPSF', _BuildOpticalPSF)

