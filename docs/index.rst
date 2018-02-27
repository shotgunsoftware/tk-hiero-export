Shotgun Hiero Export API reference, |release|
###################################################


The ``tk-hiero-export`` app adds custom Shotgun export processors to the Hiero/Nuke Studio export framework.

Via custom export processors, the user can create and update entities in the current Project in Shotgun.

During the export process a number things can happen:

- Status of associated Shot entities can be updated
- Nuke scripts can be written into the project's filesystem structure for each Shot that's processed
- Sequence and Shot entity data can be updated in Shotgun
- Cuts can be update to include new CutItems built from the exported sequences

Several aspects of the process are customizable via the following Hooks:

.. py:currentmodule:: base_hooks

Creating custom UI elements
---------------------------------

.. autoclass:: HieroCustomizeExportUI
    :members:


Updating Shot entities
----------------------------

.. autoclass:: HieroUpdateShot
    :members:


Updating and Creating Cut and CutItem entities
----------------------------------------------------

.. autoclass:: HieroUpdateCuts
    :members:


Getting Shot entities for Hiero TrackItems
------------------------------------------------

.. autoclass:: HieroGetShot
    :members:


Customizing Quicktime export settings
-------------------------------------------

.. autoclass:: HieroGetQuicktimeSettings
    :members:


Customizing PublishedFile data
------------------------------------

.. autoclass:: HieroGetExtraPublishData


Executing logic after Version entity creation
---------------------------------------------------

.. autoclass:: HieroPostVersionCreation


Executing logic prior to export
-------------------------------------

.. autoclass:: HieroPreExport


Resolving strings into Shotgun-queried values
---------------------------------------------------

.. autoclass:: HieroResolveCustomStrings


Resolving Shotgun Toolkit templates into export string representations
----------------------------------------------------------------------------

.. autoclass:: HieroTranslateTemplate


Customizing Version entity data
-------------------------------------

.. autoclass:: HieroUpdateVersionData


Uploading Thumbnails to Shotgun
-------------------------------------

.. autoclass:: HieroUploadThumbnail





