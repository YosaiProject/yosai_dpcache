
# Yosai DPCache:  "DogPile" Cache Integration

![](/img/cache_bw.png)

This is a Yosai integration using a fork of the dogpile project, authored by Mike Bayer. 

The dogpile project consists of two sub-projects:  ``dogpile.core`` and ``dogpile.cache``.
Yosai_DPCache is a fork of these projects, replacing pickle-based serialization with
serialization supported by Yosai and making a few other customizations.

## Serialization

![](/img/serialization_process.png)

Yosai reduces objects to their serializable form using the ``marshmallow`` library, 
encodes the "reductions" with msgpack, json, or other encoding scheme, and then caches
the objects.  

Objects obtained from cache are de-serialized back into their reduced forms and then 
re-materialized into Yosai objects. 


## Installation

Install YosaiDPCache from PyPI using pip: ``pip install yosai_dpcache``


## Setup

A YosaiDPCache.DPCacheHandler can be configured through one of two ways:

* Option 1: YAML Config File
    1. Define a system environment variable, YOSAI_CACHE_SETTINGS, that points to 
       the location of cache_settings.yaml file and make sure that the file
       permissions make it readable.
    
    2. Instantiate a DPCacheHandler without arguments.  

* Option 2: instantiate a DPCacheHandler, passing *all* of the required 
            arguments (see cachehandler.py and settings.py for detail)


## Dev Status (as of YosaiDPCache v0.0.5)

### Redis is Ready for Use

Only Redis support has been implemented and ad-hoc tested.

### Unit testing is Pending

Integrated testing of yosai includes YosaiDPCache, and so YosaiDPCache
is included with automated testing.  However, YosaiDPCache needs its own
unit tests covering its customizations.

