/* -*- c++ -*-
 * Copyright (c) 2012-2016 by the GalSim developers team on GitHub
 * https://github.com/GalSim-developers
 *
 * This file is part of GalSim: The modular galaxy image simulation toolkit.
 * https://github.com/GalSim-developers/GalSim
 *
 * GalSim is free software: redistribution and use in source and binary forms,
 * with or without modification, are permitted provided that the following
 * conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions, and the disclaimer given in the accompanying LICENSE
 *    file.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions, and the disclaimer given in the documentation
 *    and/or other materials provided with the distribution.
 */

#include "galsim/IgnoreWarnings.h"

#define BOOST_NO_CXX11_SMART_PTR
#include "boost/python.hpp"
#include "Random.h"

namespace bp = boost::python;


// Note that class docstrings for all of these are now added in galsim/random.py     

namespace galsim {

    // Need this special CallBack version that inherits from bp::wrapper whenever
    // you are wrapping something that has virtual functions you want to call from
    // python and have them resolve correctly.
    class BaseDeviateCallBack : public BaseDeviate,
                                public bp::wrapper<BaseDeviate>
    {
    public:
        BaseDeviateCallBack(long lseed=0) : BaseDeviate(lseed) {}
        BaseDeviateCallBack(const BaseDeviate& rhs) : BaseDeviate(rhs) {}
        BaseDeviateCallBack(std::string& str) : BaseDeviate(str) {}
        ~BaseDeviateCallBack() {}

    protected:
        // This is the special magic needed so the virtual function calls back to the 
        // function defined in the python layer.
        double _val()
        {
            if (bp::override py_func = this->get_override("_val")) 
                return py_func();
            else 
                return BaseDeviate::_val();
        }
    };

    struct PyBaseDeviate {

        static void wrap() {
            bp::class_<BaseDeviateCallBack>
                pyBaseDeviate("BaseDeviate", "", bp::no_init);
            pyBaseDeviate
                .def(bp::init<long>(bp::arg("seed")=0))
                .def(bp::init<const BaseDeviate&>(bp::arg("seed")))
                .def(bp::init<std::string>(bp::arg("seed")))
                .def("seed", (void (BaseDeviate::*) (long) )&BaseDeviate::seed,
                     (bp::arg("seed")=0))
                .def("reset", (void (BaseDeviate::*) (long) )&BaseDeviate::reset,
                     (bp::arg("seed")=0))
                .def("reset", (void (BaseDeviate::*) (const BaseDeviate&) )&BaseDeviate::reset, 
                     (bp::arg("seed")))
                .def("clearCache", &BaseDeviate::clearCache)
                .def("serialize", &BaseDeviate::serialize)
                .def("duplicate", &BaseDeviate::duplicate)
                .def("discard", &BaseDeviate::discard)
                .def("raw", &BaseDeviate::raw)
                .def("__repr__", &BaseDeviate::repr)
                .def("__str__", &BaseDeviate::str)
                .enable_pickling()
                ;

            // This lets python recognize functions that return a shared_ptr<BaseDeviate>
            // as a python BaseDeviate object.  This is needed for the BaseNoise::getRNG()
            // function _if_ the BaseNoise was default constructed.  As far as I understand it,
            // if you construct a BaseDeviate object in python and then use that to construct
            // a BaseNoise object:
            //
            //     >>> rng = galsim.BaseDeviate()
            //     >>> gn = galsim.GauusianNoise(rng)
            //
            // then the `gn.getRNG()` call doesn't need anything special because the actual
            // BaseDeviate being wrapped in the shared_ptr is really a BaseDeviateCallBack.
            // So boost python knows how to handle it.  
            //
            // But if the BaseDeviate was constructed in the C++ layer, which happens when you
            // default construct the BaseNoise object:
            //
            //     >>> gn = galsim.GaussianNoise()
            //
            // then the `gn.getRNG()` call returns a real BaseDeviate object in the shared_ptr.
            // So python doesn't really know what that is without this next line.  The
            // register_ptr_to_python call tells boost that a shared_ptr<BaseDeviate> in the 
            // C++ layer should be treated like a BaseDeviate in the python layer.
            bp::register_ptr_to_python< boost::shared_ptr<BaseDeviate> >();
        }

    };

    struct PyUniformDeviate {

        static void wrap() {
            bp::class_<UniformDeviate, bp::bases<BaseDeviate> >
                pyUniformDeviate("UniformDeviate", "", bp::no_init);
            pyUniformDeviate
                .def(bp::init<long>(bp::arg("seed")=0))
                .def(bp::init<const BaseDeviate&>(bp::arg("seed")))
                .def(bp::init<std::string>(bp::arg("seed")))
                .def("duplicate", &UniformDeviate::duplicate)
                .def("__call__", &UniformDeviate::operator())
                .enable_pickling()
                ;
        }

    };

    struct PyGaussianDeviate {

        static void wrap() {
            bp::class_<GaussianDeviate, bp::bases<BaseDeviate> >
                pyGaussianDeviate("GaussianDeviate", "", bp::no_init);
            pyGaussianDeviate
                .def(bp::init<long, double, double>(
                        (bp::arg("seed")=0, bp::arg("mean")=0., bp::arg("sigma")=1.)
                ))
                .def(bp::init<const BaseDeviate&, double, double>(
                        (bp::arg("seed"), bp::arg("mean")=0., bp::arg("sigma")=1.)
                ))
                .def(bp::init<std::string, double, double>(
                        (bp::arg("seed"), bp::arg("mean")=0., bp::arg("sigma")=1.)
                ))
                .def("duplicate", &GaussianDeviate::duplicate)
                .def("__call__", &GaussianDeviate::operator())
                .def("getMean", &GaussianDeviate::getMean)
                .def("getSigma", &GaussianDeviate::getSigma)
                .def("_setMean", &GaussianDeviate::setMean)
                .def("_setSigma", &GaussianDeviate::setSigma)
                .enable_pickling()
                ;
        }

    };

    struct PyBinomialDeviate {

        static void wrap() {
            bp::class_<BinomialDeviate, bp::bases<BaseDeviate> >
                pyBinomialDeviate("BinomialDeviate", "", bp::no_init);
            pyBinomialDeviate
                .def(bp::init<long, int, double>(
                        (bp::arg("seed")=0, bp::arg("N")=1, bp::arg("p")=0.5)
                ))
                .def(bp::init<const BaseDeviate&, int, double>(
                        (bp::arg("seed"), bp::arg("N")=1, bp::arg("p")=0.5)
                ))
                .def(bp::init<std::string, int, double>(
                        (bp::arg("seed")=0, bp::arg("N")=1, bp::arg("p")=0.5)
                ))
                .def("duplicate", &BinomialDeviate::duplicate)
                .def("__call__", &BinomialDeviate::operator())
                .def("getN", &BinomialDeviate::getN)
                .def("getP", &BinomialDeviate::getP)
                .def("_setN", &BinomialDeviate::setN)
                .def("_setP", &BinomialDeviate::setP)
                .enable_pickling()
                ;
        }

    };

    struct PyPoissonDeviate {

        static void wrap() {
            bp::class_<PoissonDeviate, bp::bases<BaseDeviate> >
                pyPoissonDeviate("PoissonDeviate", "", bp::no_init);
            pyPoissonDeviate
                .def(bp::init<long, double>(
                        (bp::arg("seed")=0, bp::arg("mean")=1.)
                ))
                .def(bp::init<const BaseDeviate&, double>(
                        (bp::arg("seed"), bp::arg("mean")=1.)
                ))
                .def(bp::init<std::string, double>(
                        (bp::arg("seed")=0, bp::arg("mean")=1.)
                ))
                .def("duplicate", &PoissonDeviate::duplicate)
                .def("__call__", &PoissonDeviate::operator())
                .def("getMean", &PoissonDeviate::getMean)
                .def("_setMean", &PoissonDeviate::setMean)
                .enable_pickling()
                ;
        }

    };

    struct PyWeibullDeviate {

        static void wrap() {

            bp::class_<WeibullDeviate, bp::bases<BaseDeviate> >
                pyWeibullDeviate("WeibullDeviate", "", bp::no_init);
            pyWeibullDeviate
                .def(bp::init<long, double, double>(
                        (bp::arg("seed")=0, bp::arg("a")=1., bp::arg("b")=1.)
                ))
                .def(bp::init<const BaseDeviate&, double, double>(
                        (bp::arg("seed"), bp::arg("a")=1., bp::arg("b")=1.)
                ))
                .def(bp::init<std::string, double, double>(
                        (bp::arg("seed")=0, bp::arg("a")=1., bp::arg("b")=1.)
                ))
                .def("duplicate", &WeibullDeviate::duplicate)
                .def("__call__", &WeibullDeviate::operator())
                .def("getA", &WeibullDeviate::getA)
                .def("getB", &WeibullDeviate::getB)
                .def("_setA", &WeibullDeviate::setA)
                .def("_setB", &WeibullDeviate::setB)
                .enable_pickling()
                ;
        }

    };

    struct PyGammaDeviate {

        static void wrap() {
            bp::class_<GammaDeviate, bp::bases<BaseDeviate> >
                pyGammaDeviate("GammaDeviate", "", bp::no_init);
            pyGammaDeviate
                .def(bp::init<long, double, double>(
                        (bp::arg("seed")=0, bp::arg("k")=1., bp::arg("theta")=1.)
                ))
                .def(bp::init<const BaseDeviate&, double, double>(
                        (bp::arg("seed"), bp::arg("k")=1., bp::arg("theta")=1.)
                ))
                .def(bp::init<std::string, double, double>(
                        (bp::arg("seed")=0, bp::arg("k")=1., bp::arg("theta")=1.)
                ))
                .def("duplicate", &GammaDeviate::duplicate)
                .def("__call__", &GammaDeviate::operator())
                .def("getK", &GammaDeviate::getK)
                .def("getTheta", &GammaDeviate::getTheta)
                .def("_setK", &GammaDeviate::setK)
                .def("_setTheta", &GammaDeviate::setTheta)
                .enable_pickling()
                ;
        }

    };

    struct PyChi2Deviate {

        static void wrap() {
            bp::class_<Chi2Deviate, bp::bases<BaseDeviate> >
                pyChi2Deviate("Chi2Deviate", "", bp::no_init);
            pyChi2Deviate
                .def(bp::init<long, double>(
                        (bp::arg("seed")=0, bp::arg("n")=1.)
                ))
                .def(bp::init<const BaseDeviate&, double>(
                        (bp::arg("seed"), bp::arg("n")=1.)
                ))
                .def(bp::init<std::string, double>(
                        (bp::arg("seed")=0, bp::arg("n")=1.)
                ))
                .def("duplicate", &Chi2Deviate::duplicate)
                .def("__call__", &Chi2Deviate::operator())
                .def("getN", &Chi2Deviate::getN)
                .def("_setN", &Chi2Deviate::setN)
                .enable_pickling()
                ;
        }

    };


    void pyExportRandom() {
        PyBaseDeviate::wrap();
        PyUniformDeviate::wrap();
        PyGaussianDeviate::wrap();
        PyBinomialDeviate::wrap();
        PyPoissonDeviate::wrap();
        PyWeibullDeviate::wrap();
        PyGammaDeviate::wrap();
        PyChi2Deviate::wrap();
    }

} // namespace galsim
