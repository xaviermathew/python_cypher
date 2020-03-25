class Debug:
    class __Debug:
        def __init__(self, default_level = 'WARN', enabled = True, name=''):
            print('Debugger name: {}'.format(name))
            self.debug_levels = {
                'FATAL':0,
                'ERROR':1,
                'WARN':2,
                'INFO':3
            }
            self.is_debug_enabled = enabled
            self.debug_level = self.debug_levels.get(default_level, 0)
            self.name = name
            
        def debug(self, log, level='WARN'):
            """ Simple function to log processing with log levels
            :str log:
            :param log: String to be outputted

            :str level:
            :param level: Level of current log [FATAL, ERROR, WARN, INFO]

            :raises:

            :rtype:
            """

            debug_enabled = self.is_debug_enabled and self.debug_levels.get(level, 3) <= self.debug_level 
            if debug_enabled:
                print('[{}] => {}'.format(self.name, log))
        def set_debug_level(self, level):
            level_idx = self.debug_levels.get(level, -1)
            if level_idx != -1:
                self.debug_level = level_idx
            else:
                print('Invalid debug level: {}'.format(level))
        def toggle_debug(self, force_state=None):
            if force_state is None:
                self.is_debug_enabled = not self.is_debug_enabled
            else:
                self.is_debug_enabled = force_state
            print('[{}] => force_state: {} > Debug is now {}'.format(self.name, force_state, 'On' if self.is_debug_enabled else 'Off'))
    instance = None
    def __init__(self, name):
        if not Debug.instance:
            Debug.instance = Debug.__Debug(name=name)
    def __getattr__(self, name):
        return getattr(self.instance, name)
    