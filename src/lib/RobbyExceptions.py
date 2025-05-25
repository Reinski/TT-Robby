class ConfigurationException(Exception):
    """To be used whenever the configuration is considered invalid. 
       It indicates that the problem lies on the user's side (configuration) and not in the implementation.
       The message should help the user to identify the problem in the configuration.
    """

class ImplementationException(Exception):
    """To be used whenever processing cannot continue, because an invalid program state has been discovered. 
       It indicates that the problem lies in the implementation and definitely not on user's side.<br>
       Mainly used in implementation of generic code.
    """

class InputDataException(Exception):
    """To be used whenever data from external sources is considered invalid. 
       It indicates that the problem lies on the user's side and not in the implementation.
       The message should help the user to identify the problem in the data.
    """

class InvalidOperationException(Exception):
    """To be used whenever an operation triggered from external sources is (currently) not possible. 
       It indicates that the problem lies on the user's side and not in the implementation.
       The message should help the user to understand which operation wasn't possible and why.
    """