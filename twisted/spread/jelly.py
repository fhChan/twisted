"""S-expression-based persistence of python objects.

I do something very much like Pickle; however, pickle's main goal seems to be
efficiency (both in space and time); jelly's main goals are security, human
readability, and portability to other environments.
"""

import string
import pickle
import sys
import types
import copy

try:
    from new import instancemethod
except:
    from org.python.core import PyMethod
    instancemethod = PyMethod

None_atom = "None"                  # N
class_atom = "class"                # c
dereference_atom = 'dereference'    # D
dictionary_atom = "dictionary"      # d
function_atom = "function"          # f
instance_atom = 'instance'          # i
list_atom = 'list'                  # l
module_atom = "module"              # m
persistent_atom = 'persistent'      # p
reference_atom = 'reference'        # r
# sexp_atom = 'sexp'                  # s
tuple_atom = "tuple"                # t
unpersistable_atom = "unpersistable"# u

class Unpersistable:
    """
    This is an instance of a class that comes back when something couldn't be
    persisted.
    """
    def __init__(self, reason):
        """
        Initialize an unpersistable object with a descriptive `reason' string.
        """
        self.reason = reason

    def __repr__(self):
        return "Unpersistable(%s)" % repr(self.reason)

class _Jellier:
    """(Internal) This class manages state for a call to jelly()
    """
    def __init__(self, taster, persistentStore):
        """Initialize.
        """
        self.taster = taster
        # `preseved' is a dict of previously seen instances.
        self.preserved = {}
        # `cooked' is a dict of previously backreferenced instances to their `ref' lists.
        self.cooked = {}
        self._ref_id = 1
        self.persistentStore = persistentStore

    def _cook(self, object):
        """(internal)
        backreference an object
        """
        aList = self.preserved[id(object)]
        newList = copy.copy(aList)
        # make a new reference ID
        refid = self._ref_id
        self._ref_id = self._ref_id + 1
        # replace the old list in-place, so that we don't have to track the
        # previous reference to it.
        aList[:] = [reference_atom, refid, newList]
        self.cooked[id(object)] = [dereference_atom, refid]
        return aList

    def _prepare(self, object):
        """(internal)
        create a list for persisting an object to.  this will allow
        backreferences to be made internal to the object. (circular
        references).
        """
        # create a placeholder list to be preserved
        self.preserved[id(object)] = []
        return []

    def _preserve(self, object, sexp):
        """(internal)
        mark an object's persistent list for later referral
        """
        #if I've been cooked in the meanwhile,
        if self.cooked.has_key(id(object)):
            # replace the placeholder empty list with the real one
            self.preserved[id(object)][2] = sexp
            # but give this one back.
            sexp = self.preserved[id(object)]
        else:
            self.preserved[id(object)] = sexp
        return sexp

    def jelly(self, object):
        """(internal) make a list
        """
        # if it's been previously backreferenced, then we're done
        if self.cooked.has_key(id(object)):
            return self.cooked[id(object)]
        # if it's been previously seen but NOT backreferenced,
        # now's the time to do it.
        if self.preserved.has_key(id(object)):
            self._cook(object)
            return self.cooked[id(object)]
        typnm = string.replace(type(object).__name__, ' ', '_')
        typfn = getattr(self, "_jelly_%s" % typnm, None)
        if typfn:
            return typfn(object)
        else:
            return self.unpersistable("type: %s" % type(object).__name__)

    def _jelly_string(self, st):
        """(internal) Return the serialized representation of a string.

        This just happens to be the string itself.
        """
        return st

    def _jelly_int(self, nt):
        """(internal)
        Return the serialized representation of an integer (which is the
        integer itself).
        """
        return nt

    def _jelly_float(self, loat):
        """(internal)
        Return the serialized representation of a float (which is the float
        itself).
        """
        return loat

    ### these have to have unjelly equivalents

    def _jelly_instance(self, instance):
        '''Jelly an instance.

        In the default case, this returns a list of 3 items::

          (instance (class ...) (dictionary ("attrib" "val")) )

        However, if I was created with a persistentStore method, then that
        method will be called with the 'instance' argument.  If that method
        returns a string, I will return::
        
          (persistent "...")
        '''
        # like pickle's persistent_id
        sxp = self._prepare(instance)
        persistent = None
        if self.persistentStore:
            persistent = self.persistentStore(instance, self)
        if persistent is not None:
            tp = type(persistent)
            sxp.append(persistent_atom)
            sxp.append(persistent)
        elif self.taster.isModuleAllowed(instance.__class__.__module__):
            if self.taster.isClassAllowed(instance.__class__):
                sxp.append(instance_atom)
                sxp.append(self.jelly(instance.__class__))
                if hasattr(instance, '__getstate__'):
                    state = instance.__getstate__()
                else:
                    state = instance.__dict__
                sxp.append(self.jelly(state))
            else:
                self.unpersistable("instance of class %s deemed insecure" % str(instance.__class__), sxp)
        else:
            self.unpersistable("instance from module %s deemed insecure" % str(instance.__class__.__module__), sxp)
        return self._preserve(instance, sxp)


    def _jelly_class(self, klaus):
        ''' (internal) Jelly a class.
        returns a list of 3 items: (class "module" "name")
        '''
        if self.taster.isModuleAllowed(klaus.__module__):
            if self.taster.isClassAllowed(klaus):
                jklaus = self._prepare(klaus)
                jklaus.append(class_atom)
                jklaus.append(self.jelly(sys.modules[klaus.__module__]))
                jklaus.append(klaus.__name__)
                return self._preserve(klaus, jklaus)
            else:
                return self.unpersistable("class %s deemed insecure" % str(klaus))
        else:
            return self.unpersistable("class from module %s deemed insecure" % str(klaus.__module__))
                

    def _jelly_dictionary(self, dict):
        ''' (internal) Jelly a dictionary.
        returns a list of n items of the form (dictionary (attribute value) (attribute value) ...)
        '''
        jdict = self._prepare(dict)
        jdict.append(dictionary_atom)
        for key, val in dict.items():
            jkey = self.jelly(key)
            jval = self.jelly(val)
            jdict.append([jkey, jval])
        return self._preserve(dict, jdict)

    def _jelly_list(self, lst):
        ''' (internal) Jelly a list.
        returns a list of n items of the form (list "value" "value" ...)
        '''
        jlst = self._prepare(lst)
        jlst.append(list_atom)
        for item in lst:
            jlst.append(self.jelly(item))
        return self._preserve(lst, jlst)

    def _jelly_None(self, nne):
        ''' (internal) Jelly "None".
        returns the list (none).
        '''
        return [None_atom]
        
    def _jelly_instance_method(self, im):
        ''' (internal) Jelly an instance method.
        return a list of the form (method "name" (instance ...) (class ...))
        '''
        jim = self._prepare(im)
        jim.append("method")
        jim.append(im.im_func.__name__)
        jim.append(self.jelly(im.im_self))
        jim.append(self.jelly(im.im_class))
        return self._preserve(im, jim)
    
    def _jelly_tuple(self, tup):
        ''' (internal) Jelly a tuple.
        returns a list of n items of the form (tuple "value" "value" ...)
        '''
        jtup = self._prepare(tup)
        jtup.append(tuple_atom)
        for item in tup:
            jtup.append(self.jelly(item))
        return self._preserve(tup, jtup)

    def _jelly_builtin_function_or_method(self, lst):
        """(internal)
        Jelly a builtin function.  This is currently unimplemented.
        """
        raise 'currently unimplemented'

    def _jelly_function(self, func):
        ''' (internal) Jelly a function.
        Returns a list of the form (function "name" (module "name"))
        '''
        name = func.__name__
        module = sys.modules[pickle.whichmodule(func, name)]
        if self.taster.isModuleAllowed(module.__name__):
            jfunc = self._prepare(func)
            jfunc.append(function_atom)
            jfunc.append(name)
            jfunc.append(self.jelly(module))
            return self._preserve(func, jfunc)
        else:
            return self.unpersistable("module %s deemed insecure" % str(module.__name__))

    def _jelly_module(self, module):
        '''(internal)
        Jelly a module.  Return a list of the form (module "name")
        '''
        if self.taster.isModuleAllowed(module.__name__):
            jmod = self._prepare(module)
            jmod.append(module_atom)
            jmod.append(module.__name__)
            return self._preserve(module, jmod)
        else:
            return self.unpersistable("module %s deemed insecure" % str(module.__name__))

    def unpersistable(self, reason, sxp=None):
        '''(internal)
        Returns an sexp: (unpersistable "reason").  Utility method for making
        note that a particular object could not be serialized.
        '''
        if sxp is None:
            sxp = []
        sxp.append(unpersistable_atom)
        sxp.append(reason)
        return sxp
            

class _FalsePromise:
    """(internal)
    this is a no-op promise for immutable objects"""
    def __init__(self):
        """(internal)
        do nothing
        """

    def keep(self):
        """Do nothing, return false.
        """
        return 0

class _Promise:
    """(internal)
    This is a function which is used to aid in the unserialization of
    self-referential immutable objects.
    """
    def __init__(self, unjellier, preobj, type, rest):
        """Initialize.
        """
        
        self.unjellier = unjellier
        self.preobj = preobj
        self.type = type
        self.rest = rest
    
    kept = 0
    
    def keep(self):
        """Actually do the work, but only once.

        If I did any work, return true, otherwise return false.
        """
        if not self.kept:
            kept = 1
            method = getattr(self.unjellier, "_postunjelly_%s" % self.type)
            method(self.rest, self.preobj)
            return 1
        return 0


class _ExternalPromise:
    ### I don't know how to do this elegantly.
    def __init__(self, method, arg, unjellier):
        self.unjellier = unjellier
        self.method = method
        self.arg = arg

    kept = 0
    def keep(self):
        if not self.kept:
            self.kept = 1
            self.method(self.arg, self.unjellier)
            del self.method
            return 1
        return 0
    
class _Unjellier:
    """(internal) I represent the state of a serialization call.
    """
    def __init__(self, taster, persistentLoad):
        """(internal) initialize.
        """
        self._references = {}
        self.taster = taster
        self.persistentLoad = persistentLoad

    def _unjelly(self, obj):
        """(internal)
        Unserialize a single object.  This may be deeply recursive.
        """
        if isinstance(obj, types.ListType):
            typ = str(obj[0])
            if not self.taster.isTypeAllowed(typ):
                raise InsecureJelly("type not allowed: %s" % repr(typ))
            rest = obj[1:]
            method = getattr(self, "_unjelly_%s" % typ)
            return method(rest)
        else:
            return _FalsePromise(), obj

    def unjelly(self, obj):
        """(internal)
        Unserialize a single object and keep any promise it makes (e.g. fully
        unserialize it, even if it's mutable)
        """
        promise, obj = self._unjelly(obj)
        promise.keep()
        return obj

    def _unjelly_None(self, rest):
        """(internal)
        Return `None'.
        """
        self._reference(None)
        return _FalsePromise(), None

    def _unjelly_persistent(self, rest):
        """(internal)

        WARNING!  This source code for this method may cause your eyeballs to
        melt.
        """
        if self.persistentLoad:
            pid = rest[0]
            pload = self.persistentLoad(rest[0],self)
            # normally it should return instances!  PersistentStore is only
            # called with instances.
            if type(pload) is not types.InstanceType:
                # eyeball meltation in progress
                assert ((type(pload) == types.TupleType)
                        and (len(pload) == 2)
                        and (isinstance(pload[0], _ExternalPromise))), "tricky pload done wrong!"
                self._reference(pload[1])
                return pload
            return _FalsePromise(), pload
        else:
            return _FalsePromise(), Unpersistable("persistent callback not found")
            
    def _unjelly_module(self, rest):
        """(internal)
        Unjelly a module.
        """
        moduleName = rest[0]
        if type(moduleName) != types.StringType:
            raise InsecureJelly("Attempted to unjelly a module with a non-string name.")
        if not self.taster.isModuleAllowed(moduleName):
            raise InsecureJelly("Attempted to unjelly module named %s" % repr(moduleName))
        mod = __import__(moduleName,{},{},"x")
        self._reference(mod)
        return _FalsePromise(), mod

    def _unjelly_list(self, rest):
        """(internal)
        make a list.
        """
        lst = []
        self._reference(lst)
        return _Promise(self, lst, 'list', rest), lst
    
    def _postunjelly_list(self, rest, lst):
        """(internal)
        check it twice.
        """
        for item in rest:
            obj = self.unjelly(item)
            lst.append(obj)

    _refid = None
    
    def _reference(self, obj):
        """(internal)
        Cache a reference so it may be referred to later in the stream.
        """
        if self._refid is not None:
            self._references[self._refid] = obj
            del self._refid
        
    def _setReference(self, refid):
        """(internal)
        Set the `_refid' attribute; this gets called before a call to
        _reference in order to indicate that the next unserialized object
        *will* be referred to later in the stream.
        """
        self._refid = refid
        
    def _unjelly_reference(self, rest):
        """(internal)
        Unserialize a reference (see _setReference and _reference calls)
        """
        refid = rest[0]
        assert type(refid) == types.IntType, "reference IDs must be integers."
        self._setReference(refid)
        return self._unjelly(rest[1])

    def _unjelly_dereference(self, rest):
        """(internal)
        Unserialize a reference to a previous element in the stream, made with
        _unjelly_reference.
        """
        refid = rest[0]
        return _FalsePromise(), self._references[refid]

    def _unjelly_instance(self, rest):
        """(internal)
        Unjelly an instance.
        """
        inst = _Dummy()
        self._reference(inst)
        clz = self.unjelly(rest[0])
        if type(clz) is not types.ClassType:
            raise InsecureJelly("Instance found with non-class class.")
        inst.__class__ = clz
        return _Promise(self, inst, "instance", rest), inst
    
    def _postunjelly_instance(self, rest, inst):
        """(internal)
        Populate an instance.
        """
        clz = inst.__class__
        state = self.unjelly(rest[1])
        if hasattr(clz, "__setstate__"):
            inst.__setstate__(state)
        else:
            inst.__dict__ = state

    def _unjelly_class(self, rest):
        """(internal)
        unjelly a class.
        """
        mod = self.unjelly(rest[0])
        if type(mod) is not types.ModuleType:
            raise InsecureJelly("class has a non-module module")
        name = rest[1]
        klaus = getattr(mod, name)
        if type(klaus) is not types.ClassType:
            raise InsecureJelly("class %s unjellied to something that isn't a class: %s" % (repr(name), repr(klaus)))
        if not self.taster.isClassAllowed(klaus):
            raise InsecureJelly("class not allowed: %s" % str(klaus))
        self._reference(klaus)
        return _FalsePromise(), klaus


    def _unjelly_dictionary(self, rest):
        """(internal)
        unjelly a dictionary
        """
        dict = {}
        self._reference(dict)
        return _Promise(self, dict, "dictionary", rest), dict


    def _postunjelly_dictionary(self, rest, dict):
        """(internal)
        populate a dictionary
        """
        for kvp in rest:
            key = self.unjelly(kvp[0])
            val = self.unjelly(kvp[1])
            dict[key] = val


    def _unjelly_method(self, rest):
        ''' (internal) unjelly a method
        '''
        im_name = rest[0]
        promise, im_self = self._unjelly(rest[1])
        im_class = self.unjelly(rest[2])
        if im_class.__dict__.has_key(im_name):
            if im_self is None:
                im = getattr(im_class, im_name)
            else:
                im = instancemethod(im_class.__dict__[im_name],
                                    im_self,
                                    im_class)
        else:
            # perhaps, getattr(im_self, im_name) ... 
            raise 'instance method changed'
        self._reference(im)
        promise.keep()
        return _FalsePromise(), im

    def _unjelly_function(self, rest):
        """(internal)
        Unserialize a function.
        """
        module = self.unjelly(rest[1])
        if type(module) is not types.ModuleType:
            raise InsecureJelly("function references a non-module module")
        function = getattr(module, rest[0])
        self._reference(function)
        return _FalsePromise(), function

    def _unjelly_tuple(self, rest):
        """(internal)
        Unserialize a tuple.
        """
        pretup = []
        promises = []
        # collect everything I need to build the tuple
        for item in rest:
            
            # don't keep any of these promises yet -- the idea here is that we
            # want to be able to support circular references of immutable
            # objects; the only way to do that is to NOT actually unserialize
            # the bits which may cause a circular reference (mutable objects
            # contained within the immutable ones) until they've been
            # pre-unserialized.
            
            promise, unj = self._unjelly(item)
            pretup.append(unj)
            promises.append(promise)
        # convert it to a tuple
        tup = tuple(pretup)
        # give it a persistent ID if it needs one
        self._reference(tup)
        for promise in promises:
            promise.keep()
        return _FalsePromise(), tup


    def _unjelly_unpersistable(self, rest):
        """(internal)
        Return an instance of an Unpersistable which indicates why this
        couldn't be persisted.
        """
        unpr = Unpersistable(rest[0])
        self._reference(unpr)
        return _FalsePromise(), unpr

class _Dummy:
    """(Internal)
    Dummy class, used for unserializing instances.
    """




#### Published Interface.


class InsecureJelly(Exception):
    """
    This exception will be raised when a jelly is deemed `insecure'; e.g. it
    contains a type, class, or module disallowed by the specified `taster'
    """



class DummySecurityOptions:
    """DummySecurityOptions() -> insecure security options
    Dummy security options -- this class will allow anything.
    """
    def isModuleAllowed(self, moduleName):
        """DummySecurityOptions.isModuleAllowed(moduleName) -> boolean
        returns 1 if a module by that name is allowed, 0 otherwise
        """
        return 1

    def isClassAllowed(self, klass):
        """DummySecurityOptions.isClassAllowed(class) -> boolean
        Assumes the module has already been allowed.  Returns 1 if the given
        class is allowed, 0 otherwise.
        """
        return 1

    def isTypeAllowed(self, typeName):
        """DummySecurityOptions.isTypeAllowed(typeName) -> boolean
        Returns 1 if the given type is allowed, 0 otherwise.
        """
        return 1
    


class SecurityOptions:
    """
    This will by default disallow everything, except for 'none'.
    """

    basicTypes = ["dictionary", "list", "tuple",
                  "reference", "dereference", "unpersistable",
                  "persistent"]
    
    def __init__(self):
        """SecurityOptions()
        Initialize.
        """
        # I don't believe any of these types can ever pose a security hazard,
        # except perhaps "reference"...
        self.allowedTypes = {"None": 1,
                             "string": 1,
                             "int": 1,
                             "float": 1}
        self.allowedModules = {}
        self.allowedClasses = {}

    def allowBasicTypes(self):
        """SecurityOptions.allowBasicTypes()
        Allow all `basic' types.  (Dictionary and list.  Int, string, and float are implicitly allowed.)
        """
        apply(self.allowTypes, self.basicTypes)

    def allowTypes(self, *types):
        """SecurityOptions.allowTypes(typeString): Allow a particular type, by its name.
        """
        for typ in types:
            self.allowedTypes[string.replace(typ, ' ', '_')]=1

    def allowInstancesOf(self, *classes):
        """SecurityOptions.allowInstances(klass, klass, ...): allow instances of the specified classes
        This will also allow the 'instance', 'class', and 'module' types, as well as basic types.
        """
        self.allowBasicTypes()
        self.allowTypes("instance", "class", "module")
        for klass in classes:
            self.allowModules(klass.__module__)
            self.allowedClasses[klass] = 1

    def allowModules(self, *modules):
        """SecurityOptions.allowModules(module, module, ...): allow modules by name
        This will also allow the 'module' type.
        """
        for module in modules:
            if type(module) == types.ModuleType:
                module = module.__name__
            self.allowedModules[module] = 1

    def isModuleAllowed(self, moduleName):
        """SecurityOptions.isModuleAllowed(moduleName) -> boolean
        returns 1 if a module by that name is allowed, 0 otherwise
        """
        return self.allowedModules.has_key(moduleName)

    def isClassAllowed(self, klass):
        """SecurityOptions.isClassAllowed(class) -> boolean
        Assumes the module has already been allowed.  Returns 1 if the given
        class is allowed, 0 otherwise.
        """
        return self.allowedClasses.has_key(klass)

    def isTypeAllowed(self, typeName):
        """SecurityOptions.isTypeAllowed(typeName) -> boolean
        Returns 1 if the given type is allowed, 0 otherwise.
        """
        return self.allowedTypes.has_key(typeName)





def jelly(object, taster = DummySecurityOptions(), persistentStore = None):
    """Serialize to s-expression.
    
    Returns a list which is the serialized representation of an object.  An
    optional 'taster' argument takes a SecurityOptions and will mark any
    insecure objects as unpersistable rather than serializing them.
    """
    return _Jellier(taster, persistentStore).jelly(object)


def unjelly(sexp, taster = DummySecurityOptions(), persistentLoad = None):
    """Unserialize from s-expression.
    
    Takes an list that was the result from a call to jelly() and unserializes
    an arbitrary object from it.  The optional 'taster' argument, an instance
    of SecurityOptions, will cause an InsecureJelly exception to be raised if a
    disallowed type, module, or class attempted to unserialize.
    """
    return _Unjellier(taster, persistentLoad).unjelly(sexp)


