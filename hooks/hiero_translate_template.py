"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------
"""
from tank import Hook
import tank.templatekey


class HieroTranslateTemplate(Hook):
    """
    Translates a template object into a hiero export string.
    """ 
    
    def execute(self, template, **kwargs):
        """
        Takes a sgtk template object as input and returns a string
        representation which is suitable for hiero exports. The hiero export templates
        contain tokens such as {shot} or {clip} which are replaced by the exporter.
        
        This hook should convert a template object with its special custom fields into
        such a string. Depending on your template setup, you may have to do different 
        steps here in order to fully convert your template. The path returned will be 
        validated to check that no leftover template fields are present and that the 
        returned path is fully understood by hiero. 
        """
        
        # first convert basic fields
        mapping = { "{Sequence}": "{sequence}",
                    "{Shot}": "{shot}",
                    "{name}": "{clip}" }
        
        # get the string representation of the template object
        template_str = template.definition

        # simple string to string replacement
        for (orig, repl) in mapping.iteritems():
            template_str = template_str.replace(orig, repl)

        # replace {SEQ} style keys with their translated string value
        for (name, key) in template.keys.iteritems():
            if isinstance(key, tank.templatekey.SequenceKey):
                # this is a sequence template, for example {SEQ}
                # replace it with ####
                template_str = template_str.replace("{%s}" % name, key.str_from_value("FORMAT:#"))

        return template_str
