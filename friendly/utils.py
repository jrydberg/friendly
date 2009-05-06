import objc


class KeyValueBindingSupport:
    """
    Class that helps the user to implement the
    NSKeyValueBindingCreation protocol.
    """

    def __init__(self, instance):
        self.bindings = {}
        self.instance = instance
        self.ignore = list()

    def bind(self, binding, toObject, keyPath, options, realize=True):
        """
        Establishes binding between the given property C{binding} and
        the property of the given object specified by C{keyPath}.

        @param realize: True if the binding should be realized now.
        """
        toObject.addObserver_forKeyPath_options_context_(self.instance, keyPath, 0, None)
        self.bindings[(toObject, keyPath)] = binding
        if realize:
            self.observe(keyPath, toObject, {})

    def unbind(self, binding):
        bindings = list()
        for (object, keypath), value in self.bindings.iteritems():
            if value == binding:
                bindings.append((object, keypath))
        for object, keypath in bindings:
            del self.bindings[(object, keypath)]

    def realize(self):
        """
        Realize all bindings.
        """
        for object, keypath in self.bindings:
            self.observe(keyPath, object, {})

    def observe(self, keyPath, object, change):
        if (object, keyPath) in self.ignore:
            return
        try:
            binding = self.bindings[(object, keyPath)]
        except IndexError:
            return
        self.ignore.append((object, keyPath))
        self.instance.setValue_forKey_(object.valueForKey_(keyPath), binding)
        self.ignore.remove((object, keyPath))


def selector(signature):
    def decorator(fn, signature=signature):
        return objc.selector(fn, signature=signature)
    return decorator


def initWithSuper(original):
    """
    Method decorator to simply writing init-method for PyObjC classes.
    
    This decorator eliminates the need to call [super init] and check
    the result of None.  Plus you do not have to remember to return
    'self', since that is already done for you.
    """
    def method(self, *args):
        initMethod = self.__class__.__bases__[0].init
        self = initMethod(self)
        if self is None:
            return None
        original(self, *args)
        return self
    return method

