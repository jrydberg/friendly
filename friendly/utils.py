import objc


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

