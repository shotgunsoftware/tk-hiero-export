# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class HieroTranslateTemplate(HookBaseClass):
    """
    Translates a template object into a hiero export string.
    """ 
    
    def execute(self, template, output_type, **kwargs):
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
        pass
