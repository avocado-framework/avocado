#!/usr/bin/python
import unittest
import logging

import common
import propcan


class TestPropCanBase(unittest.TestCase):

    def test_empty_init(self):
        self.assertRaises(NotImplementedError, propcan.PropCanBase)

    def test_empty_params_init(self):
        self.assertRaises(NotImplementedError,
                          propcan.PropCanBase,
                          {'foo': 'bar'})

    def test_single_init(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCanBase):
            __slots__ = ('foo',)
        testcan = FooBar(foo='bar')
        self.assertEqual(len(testcan), 1)
        self.assertEqual(testcan['foo'], 'bar')
        self.assertEqual(testcan.foo, 'bar')

    def test_double_init(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCanBase):
            __slots__ = ('foo', 'bar')
        testcan = FooBar(foo='bar', bar='foo')
        self.assertEqual(len(testcan), 2)
        self.assertEqual(testcan['foo'], 'bar')
        self.assertEqual(testcan['bar'], 'foo')
        self.assertEqual(len(testcan), 2)
        self.assertEqual(testcan.foo, 'bar')
        self.assertEqual(testcan.bar, 'foo')

    def test_slots_restrict(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCanBase):
            __slots__ = ('foo',)
        testcan = FooBar(foo='bar')
        self.assertEqual(len(testcan), 1)
        self.assertEqual(testcan['foo'], 'bar')
        self.assertEqual(testcan.foo, 'bar')
        self.assertRaises(AttributeError, setattr, testcan, 'bar', 'foo')
        self.assertRaises(KeyError, testcan.__setitem__, 'bar', 'foo')

    def test_mixed_init(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCanBase):
            __slots__ = ('foo', 'bar')
        testcan = FooBar({'foo': 'bar'})
        self.assertEqual(len(testcan), 1)
        self.assertEqual(testcan['foo'], 'bar')
        self.assertEqual(len(testcan), 1)
        self.assertEqual(testcan.foo, 'bar')
        self.assertRaises(KeyError, testcan.__getitem__, 'bar')
        self.assertRaises(AttributeError, getattr, testcan, 'bar')
        self.assertRaises(KeyError, testcan.__delitem__, 'bar')
        self.assertRaises(AttributeError, delattr, testcan, 'bar')

    def test_subclass_single_init_setter(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCanBase):
            __slots__ = ('foo', )
            it_works = False

            def set_foo(self, value):
                self.__dict_set__('foo', value)
                if value == 'bar':
                    self.__super_set__('it_works', True)
        testcan = FooBar()
        self.assertEqual(len(testcan), 0)
        self.assertFalse(testcan.it_works)
        self.assertRaises(KeyError, testcan.__getitem__, 'foo')
        self.assertRaises(AttributeError, getattr, testcan, 'foo')
        testcan['foo'] = 'bar'
        self.assertEqual(len(testcan), 1)
        self.assertTrue(testcan.it_works)

    def test_subclass_single_init_getter(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCanBase):
            __slots__ = ('foo', )
            it_works = False

            def get_foo(self):
                value = self.__dict_get__('foo')
                if value == 'bar':
                    self.__super_set__('it_works', True)
                return value
        testcan = FooBar()
        self.assertFalse(testcan.it_works)
        self.assertEqual(len(testcan), 0)
        testcan['foo'] = 'bar'
        self.assertEqual(len(testcan), 1)
        # verify __super_set__() doesn't call getter
        self.assertFalse(testcan.it_works)
        self.assertEqual(testcan['foo'], 'bar')
        self.assertEqual(testcan.foo, 'bar')
        self.assertTrue(testcan.it_works)

    def test_subclass_single_init_delter(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCanBase):
            __slots__ = ('foo', )
            it_works = False

            def del_foo(self):
                value = self.__dict_get__('foo')
                if value == 'bar':
                    self.__super_set__('it_works', True)
                self.__dict_del__('foo')
        testcan = FooBar()
        self.assertEqual(len(testcan), 0)
        self.assertFalse(testcan.it_works)
        self.assertFalse(hasattr(testcan, 'foo'))
        self.assertFalse(testcan.has_key('foo'))
        testcan['foo'] = 'bar'
        self.assertEqual(len(testcan), 1)
        self.assertEqual(testcan['foo'], 'bar')
        self.assertEqual(testcan.foo, 'bar')
        del testcan['foo']
        self.assertEqual(len(testcan), 0)
        self.assertTrue(testcan.it_works)

    def test_subclass_no_mask_attributeerror(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCanBase):
            __slots__ = ('foo', )

            def del_foo(self):
                raise AttributeError("Del Test")

            def set_foo(self, value):
                raise AttributeError("Set Test")

            def get_foo(self):
                raise AttributeError("Get Test")
        testcan = FooBar()
        self.assertRaises(AttributeError, testcan.__getitem__, 'foo')
        self.assertRaises(AttributeError, testcan.__setitem__, 'foo', None)
        self.assertRaises(AttributeError, testcan.__delitem__, 'foo')
        self.assertRaises(AttributeError, testcan.__getattr__, 'foo')
        self.assertRaises(AttributeError, testcan.__setattr__, 'foo', None)
        self.assertRaises(AttributeError, testcan.__delattr__, 'foo')

    def test_dict_methods_1(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCanBase):
            __slots__ = ('foo', 'bar')
        testcan = FooBar(foo='bar', bar='foo')
        testdict = {}
        for key, value in testcan.items():
            testdict[key] = value
        self.assertEqual(testcan, testdict)

    def test_dict_methods_2(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCanBase):
            __slots__ = ('foo', 'bar')
        testcan = FooBar(foo='bar', bar='foo')
        testdict = testcan.copy()
        self.assertEqual(testcan, testdict)
        testcan['foo'] = 'foo'
        testcan['bar'] = 'bar'
        self.assertTrue(testcan.foo != testdict.foo)
        self.assertTrue(testcan.bar != testdict.bar)
        testdict['foo'] = 'foo'
        testdict['bar'] = 'bar'
        self.assertTrue(testcan.foo == testdict.foo)
        self.assertTrue(testcan.bar == testdict.bar)

    def test_update(self):
        class FooBar(propcan.PropCanBase):
            __slots__ = ('foo', 'bar')

        testdict = FooBar()
        other = {'foo': 1, 'bar': 2}
        testdict.update(other)
        self.assertEqual(testdict, other)

        other = 'string'
        self.assertRaises(ValueError, testdict.update, other)

        other = {'foo': 1, 'bar': 2, 'v3': 3}
        self.assertRaises(KeyError, testdict.update, other)

        kwargs = {'foo': "foo", 'bar': "bar"}
        testdict.update(**kwargs)
        self.assertEqual(testdict, kwargs)


class TestPropCan(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.INFO)

    def test_extranious_init(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCan):
            __slots__ = ('foo', )
        testcan = FooBar((('foo', 'bar'), ('bar', 'foo'),))
        self.assertEqual(len(testcan), 1)
        testcan = FooBar(bar='foo')
        self.assertEqual(len(testcan), 0)

    def test_init_None_value(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCan):
            __slots__ = ('foo', )
        testcan = FooBar(foo=None)
        self.assertEqual(len(testcan), 0)
        self.assertEqual(testcan['foo'], None)
        self.assertEqual(testcan.foo, None)

    def test_compare(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCan):
            __slots__ = ('foo', 'bar')
        testcan = FooBar(foo=None, bar='foo')
        self.assertEqual(len(testcan), 1)
        self.assertTrue(testcan == {'bar': 'foo'})
        testcan.foo = 'bar'
        self.assertEqual(len(testcan), 2)
        self.assertTrue(testcan == {'bar': 'foo', 'foo': 'bar'})
        self.assertTrue(testcan == {'foo': 'bar', 'bar': 'foo'})
        testcan.bar = None
        self.assertEqual(len(testcan), 1)
        self.assertTrue(testcan == {'foo': 'bar'})

    def test_odd_values(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCan):
            __slots__ = ('foo', 'bar', 'baz')
        testcan = FooBar()
        self.assertEqual(len(testcan), 0)
        testcan.foo = type('blah', (), {})
        self.assertEqual(len(testcan), 1)
        testcan['bar'] = testcan
        self.assertEqual(len(testcan), 2)
        setattr(testcan, 'baz', lambda self: str(self))
        self.assertEqual(len(testcan), 3)

    def test_printables(self):
        # Pylint false negative
        # pylint: disable=E1001
        class FooBar(propcan.PropCan):
            __slots__ = ('foo', 'bar', 'baz')
        testcan = FooBar()
        self.assertEqual(len(testcan), 0)
        for value in ('foobar', u'foobar', 1, 1.1, 12345L, ):
            setattr(testcan, 'bar', value)
            self.assertEqual(len(testcan), 1)
            self.assertTrue(testcan == {'bar': value})
            self.assertEqual(str(testcan), str({'bar': value}))

if __name__ == '__main__':
    unittest.main()
