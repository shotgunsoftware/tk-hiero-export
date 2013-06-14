"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------
"""
from tank import Hook
import tank.templatekey


class HieroTranslateTemplate(Hook):
    def execute(self, template, **kwargs):
        mapping = {
            '{Sequence}': '{sequence}',
            '{Shot}': '{shot}',
            '{name}': '{clip}',
            '{Step}': self.parent.context.step['name'],
        }
        raw = template.definition

        # simple string to string replacement
        ret = raw
        for (orig, repl) in mapping.iteritems():
            ret = ret.replace(orig, repl)

        # replace {SEQ} style keys with their translated string value
        for (name, key) in template.keys.iteritems():
            if isinstance(key, tank.templatekey.SequenceKey):
                ret = ret.replace('{%s}' % name, key.str_from_value())

        self.parent.log_debug("HieroTranslateTemplate.execute(%s) = %s" % (raw, ret))
        return ret
