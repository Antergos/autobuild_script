#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# redis_connection.py
#
# Copyright © 2013-2016 Antergos
#
# This file is part of The Antergos Build Server, (AntBS).
#
# AntBS is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# AntBS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# The following additional terms are in effect as per Section 7 of the license:
#
# The preservation of all legal notices and author attributions in
# the material or in the Appropriate Legal Notices displayed
# by works containing it is required.
#
# You should have received a copy of the GNU General Public License
# along with AntBS; If not, see <http://www.gnu.org/licenses/>.


import errno
import json
import os

import redis
import time

db = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', decode_responses=True)


class RedisObject:
    """ A base object backed by redis. This class should not be used directly. """

    db = db

    def __init__(self, full_key=None, *args, **kwargs):
        """ Create or load a RedisObject. """
        self.attrib_lists = dict(string=[], bool=[], int=[], list=[], set=[], path=[])

        if full_key:
            self.full_key = full_key
        else:
            raise ValueError('A key is required to initialize a redis object.')

    def __bool__(self):
        """ Tests if this object currently exists in redis. """
        if isinstance(self, RedisList) and len(self) < 1:
            return False
        return self.db.exists(self.full_key)

    def __nonzero__(self):
        return self.__bool__()

    def __eq__(self, other):
        """ Tests if two redis objects are equal (they have the same full_key). """
        return self.full_key == other.full_key

    def __str__(self):
        """ Return this object's full_key as a string. This can be extended by subclasses. """
        return self.full_key

    def __iter__(self):
        raise NotImplementedError

    def __getitem__(self, index):
        """ Load an item by index where index is either an int or a slice. """

        if not isinstance(self, (RedisList, RedisZSet)):
            raise NotImplementedError('Cannot __getitem__ of RedisHash object')

        if isinstance(index, slice):
            if index.step and index.step > 1:
                raise NotImplementedError('Cannot specify a step to a {0} object slice'.format(
                                          self.__class__.__name__))

            if isinstance(self, RedisList):
                return [
                    RedisObject.decode_value(self.item_type, el)
                    for el in self.db.lrange(self.full_key, index.start, index.stop)
                    ]
            if isinstance(self, RedisZSet):
                return [
                    RedisObject.decode_value(self.item_type, el)
                    for el in self.db.zrange(self.full_key, index.start, index.stop)
                    ]

        else:
            return RedisObject.decode_value(self.item_type, self.db.lindex(self.full_key, index))

    def delete(self):
        """ Delete this object from redis. """
        self.db.delete(self.full_key)

    def __jsonable__(self):
        """
        Returns this object as a python built-in type so it can be serialized by the json module.

        """
        res = None
        if isinstance(self, (RedisList, RedisZSet)):
            res = list(self.__iter__())

        elif 'ServerStatus' == self.__class__.__name__:
            raise RuntimeError(
                'ServerStatus object cant be converted to json (it contains private data!!)'
            )

        elif isinstance(self, RedisHash):
            as_dict = dict()

            for key in self.all_attribs:
                if key in ['log_str', 'log', 'pkgbuild']:
                    continue

                val = getattr(self, key)

                if not isinstance(val, (str, dict, bool, int)) and hasattr(val, '__jsonable__'):
                    as_dict[key] = val.__jsonable__()
                else:
                    as_dict[key] = val

            res = as_dict

        return res

    def json(self):
        """ Return this object as a json serialized string. """
        return json.dumps(self.__jsonable__())

    @classmethod
    def as_child(cls, parent, tag, item_type):
        """
        Alternative callable constructor that instead defines this as a child object.
        This allows you to store classes derived from `RedisObject` inside other classes
        that are also derived from `RedisObject`.

        Args:
            parent (RedisHash):    The parent object.
            tag (str):             Short name for this object. It will be combined with parent
                                   object's `full_key` to create this object's `full_key`.
            item_type (type(str)): The built-in type object for the type of data stored in this
                                   object.
        """

        def helper(_=None):
            return cls(parent.full_key + ':' + tag, item_type)

        return helper()

    @staticmethod
    def decode_value(obj_type, value):
        """ Decode a value if it is non-None, otherwise, decode with no arguments. """
        if value is None:
            return obj_type()
        else:
            return obj_type(value)

    @staticmethod
    def encode_value(value):
        """ Encode a value using json.dumps, with default = str. """
        return str(value)


class RedisList(RedisObject, list):
    """
    A list where all items are stored in Redis.

    Args:
        full_key (str):     Use this as the redis key.
        item_type (object): The constructor to use when reading items from redis.
        items (list):       Default values to store during construction.

    """

    def __init__(self, full_key=None, item_type=str, items=None):

        super().__init__(full_key=full_key)
        self.item_type = item_type

        if items:
            for item in items:
                self.append(item)

    def __str__(self):
        """ Return this object as a string """
        return str([x for x in self.__iter__()])

    def __setitem__(self, index, val):
        """ Update an item by index. """
        self.db.lset(self.full_key, index, super().encode_value(val))

    def __len__(self):
        """ Return the size of the list. """
        return self.db.llen(self.full_key)

    def __delitem__(self, index):
        """ Delete an item from this list by index. """
        self.db.lset(self.full_key, index, '__DELETED__')
        self.db.lrem(self.full_key, 1, '__DELETED__')

    def __iter__(self):
        """ Iterate over all items in this list. """
        for el in self.db.lrange(self.full_key, 0, -1):
            yield super().decode_value(self.item_type, el)

    def __contains__(self, item):
        """ Check if item is in this list. """
        items = self.db.lrange(self.full_key, 0, -1)
        return item in items

    def __add__(self, other_list):
        """ Combine elements from this list (self) and other_list into a new list. """
        return [x for x in self.__iter__()] + [x for x in other_list.__iter__()]

    def lpop(self):
        """ Remove and return a value from the left (low) end of the list. """
        return super().decode_value(self.item_type, self.db.lpop(self.full_key))

    def rpop(self):
        """ Remove a value from the right (high) end of the list. """
        return super().decode_value(self.item_type, self.db.rpop(self.full_key))

    def lpush(self, val):
        """ Add an item to the left (low) end of the list. """
        self.db.lpush(self.full_key, super().encode_value(val))

    def rpush(self, val):
        """ Add an item to the right (high) end of the list. """
        self.db.rpush(self.full_key, super().encode_value(val))

    def append(self, val):
        self.rpush(val)

    def reverse(self):
        cp = list(self.db.lrange(self.full_key, 0, -1))
        return cp.reverse()

    def remove(self, val):
        self.db.lrem(self.full_key, 0, val)


class RedisZSet(RedisObject, set):
    """
    A sorted set where all items are stored in Redis.

    Args:
        full_key (str): use this as the redis key.
        item_type (object): The constructor to use when reading items from redis.
        values (list): Default values to store during construction.

    """

    def __init__(self, full_key=None, item_type=str, items=None):

        super().__init__(full_key=full_key)
        self.item_type = item_type

        if items:
            for item in items:
                self.add(item)

    def __len__(self):
        """ Return the size of the set. """
        return self.db.zcard(self.full_key) if self.db.exists(self.full_key) else 0

    def __iter__(self):
        """ Iterate over all items in this set. """
        for el in self.db.zrange(self.full_key, 0, -1):
            yield super().decode_value(self.item_type, el)

    def __str__(self):
        """ Return this object as a string """
        return str([x for x in self.__iter__()])

    def __contains__(self, item):
        """ Check if item is in the set. """
        return item in self.db.zrange(self.full_key, 0, -1)

    def add(self, *values):
        """ Add member to set if it doesn't exist. """
        vals = []
        for val in values:
            vals.append(1)
            vals.append(val)
        self.db.zadd(self.full_key, *vals)

    def remove(self, val):
        """ Remove a member from the set. """
        self.db.zrem(self.full_key, super().encode_value(val))

    def ismember(self, val):
        """ Check if value is a member of set. """
        rank = self.db.zrank(self.full_key, super().encode_value(val))
        return True if rank else False


class RedisHash(RedisObject):
    """
    This is the base class for all of the redis-backed classes in this application.
    The class provides access to predefined keys as class attributes which are stored in redis.

    Args:
        namespace (str): This is used as the first part of the redis key. It should
                         usually be the application name (top-most-level identifier)
        prefix (str):    This is used as the second part of the redis key. It should
                         describe all objects of the subclass type.
        key (str):       This is used as the last part of the redis key. It should
                         describe a single object of the subclass type (like an instance).

    Attributes:
        namespace (str):  See Args.
        prefix (str):     See Args.
        key (str):        See Args.
        full_key (str):   This objects redis key, eg. `namespace:prefix:key`.
        key_lists (dict): Contains lists of class attributes that are stored in redis
                          organized by their value type.
        all_keys (list):  List of all class attributes that are stored in redis.

    """

    def __init__(self, namespace='antbs', prefix='', key='', *args, **kwargs):
        if 'status' != prefix and not key and not prefix:
            raise ValueError('Both "prefix" and "key" are required')

        id_key = '{0}:{1}:{2}'.format(namespace, prefix, key)

        super().__init__(full_key=id_key)

        self.namespace = namespace
        self.prefix = prefix
        self.key = key
        self.full_key = id_key
        self.all_attribs = []

    def __namespaceinit__(self):
        """ Makes sure that the objects `full_key` and `all_attribs` attributes are set properly. """
        self.all_attribs = [item for sublist in self.attrib_lists.values() for item in sublist]

        if self.full_key[-1] == ':':
            self.full_key = self.full_key[:-1]

    def __keysinit__(self):
        """ Initializes the object's predefined attributes as hash fields in Redis. """
        for key in self.all_attribs:
            value = getattr(self, key, '')
            is_string = key in self.attrib_lists['string']
            initialized = (not is_string and '' != value) or (is_string and '_' != value)

            if initialized:
                continue

            if 'ServerStatus' == self.__class__.__name__:
                value = os.environ.get(key.upper())

            if key in self.attrib_lists['string'] + self.attrib_lists['path']:
                value = value or ''
                setattr(self, key, value)
            elif key in self.attrib_lists['bool']:
                value = value or False
                setattr(self, key, value)
            elif key in self.attrib_lists['int']:
                value = value or 0
                setattr(self, key, value)
            elif key in self.attrib_lists['list']:
                setattr(self, key, RedisList.as_child(self, key, str))
            elif key in self.attrib_lists['set']:
                setattr(self, key, RedisZSet.as_child(self, key, str))

    def __str__(self):
        """ Return this object as a friendly (human readable) string. """
        return '<{0} {1}>'.format(self.__class__.__name__, self.key)

    def __len__(self):
        """ Return the len of this object (total number of fields in its redis hash). """
        return int(self.db.hlen(self.full_key))

    def __getitem__(self, item):
        """ Get and return the value of a field (item) from this objects redis hash."""
        return self.__getattribute__(item)

    def __setitem__(self, key, value):
        """ Set the value of a field (item) from this objects redis hash."""
        return self.__setattribute__(key, value)

    def __iter__(self):
        """ Return an iterator with all the keys in redis hash. """
        return [key for key in self.all_attribs]

    def iterkeys(self):
        return self.__iter__()

    def __getattribute__(self, attrib):
        """ Get attribute value if stored in redis otherwise pass call to parent class """

        pass_list = ['attrib_lists', 'all_attribs', 'namespace', 'database', '_build',
                     'key', 'full_key', 'prefix', 'db', 'full_key']

        if attrib in pass_list or (attrib not in self.all_attribs and '__exp' not in attrib):
            return super().__getattribute__(attrib)

        key = self.full_key

        if attrib in self.attrib_lists['string'] + self.attrib_lists['path']:
            return self.db.hget(key, attrib) if self.db.hexists(key, attrib) else '_'

        elif attrib in self.attrib_lists['bool']:
            val = self.db.hget(key, attrib) if self.db.hexists(key, attrib) else ''
            return self.bool_string_helper(val) if '' != val else ''

        elif attrib in self.attrib_lists['int']:
            return int(self.db.hget(key, attrib)) if self.db.hexists(key, attrib) else ''

        elif attrib in self.attrib_lists['list']:
            return RedisList.as_child(self, attrib, str)

        elif attrib in self.attrib_lists['set']:
            return RedisZSet.as_child(self, attrib, str)

        elif attrib.endswith('__exp'):
            val = self.db.hget(key, attrib) if self.db.hexists(key, attrib) else time.time()
            return int(val) - 1

    def __setattr__(self, attrib, value, score=None):
        """ Set attribute value if stored in redis otherwise pass call to parent class """

        pass_list = ['attrib_lists', 'all_attribs', 'namespace', 'database', '_build',
                     'key', 'full_key', 'prefix', 'db', 'full_key']

        # Note: These two statements cannot be combined (causes an exception during object init)
        if attrib in pass_list or (attrib not in self.all_attribs and '__exp' not in attrib):
            return super().__setattr__(attrib, value)
        if attrib in self.attrib_lists['list'] + self.attrib_lists['set']:
            return super().__setattr__(attrib, value)

        key = self.full_key

        if attrib in self.attrib_lists['string'] + self.attrib_lists['int'] or attrib.endswith('__exp'):
            val = value if '_' != value else ''
            self.db.hset(key, attrib, val)

        elif attrib in self.attrib_lists['bool']:
            if value in [True, False]:
                self.db.hset(key, attrib, self.bool_string_helper(value))
            else:
                raise ValueError('{0}.{1} must be of type(bool), {2} given.'.format(
                    self.__class__.__name__, attrib, type(value)))

        elif attrib in self.attrib_lists['path']:
            if self.is_pathname_valid(value):
                self.db.hset(key, attrib, value)
            else:
                raise ValueError('{0}.{1} must be a valid pathname (str), {2} given.'.format(
                    self.__class__.__name__, attrib, value))

        else:
            raise AttributeError('class {0} has no attribute {1}.'.format(
                self.__class__.__name__, attrib))

    def __is_expired__(self, attrib):
        exp_key = attrib + '__exp'
        expire_time = self.db.hget(self.full_key, exp_key) or 0
        now = int(time.time())

        return now > int(expire_time)

    def expire_in(self, attrib, seconds):
        expires = int(time.time()) + seconds
        attrib_key = attrib + '__exp'

        self.db.hset(self.full_key, attrib_key, expires)


    @staticmethod
    def bool_string_helper(value):
        """
        Given a `str`, returns value as `bool`. Given a `bool`, returns value as `str`.

        """
        if isinstance(value, str):
            return True if 'True' == value else False
        elif isinstance(value, bool):
            return 'True' if value else 'False'
        else:
            raise ValueError(
                'value must be of type(bool) or type(str), {0} given.'.format(type(value))
            )

    @staticmethod
    def is_pathname_valid(pathname):
        """
        Determines whether or not a string is a valid pathname (linux only).

        Args:
            pathname (str): String to check.

        Returns:
            `True` if the passed pathname is a valid pathname. `False` otherwise.

        Notes:
            Modified version of this SO answer: http://stackoverflow.com/a/34102855/2639936
        """

        # If pathname is either not a string or empty, this pathname is invalid.
        if not isinstance(pathname, str) or not pathname:
            return False

        try:
            # Directory guaranteed to exist (the root directory).
            root_dirname = os.path.sep

            # Test whether each path component split from pathname is valid,
            # ignoring non-existent and non-readable path components.
            for pathname_part in pathname.split(os.path.sep):
                try:
                    os.lstat(root_dirname + pathname_part)
                except OSError as err:
                    if err.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                        return False

        except TypeError:
            # pathname is invalid.
            return False
        else:
            # All path components and hence pathname itself are valid.
            return True
