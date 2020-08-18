Running dr2xml
==============

Once filled-in the previous two dictionaries of settings, dr2xml is simply executed by:

1. importing the appropriate module from dr2xml:

.. code-block:: python

   from dr2xml import generate_file_defs

2. setting the paths to your local copy of CMIP6 CVs:

.. code-block:: python

   my_cvspath=<My-CMIP6CVs-Rep>

3. generating file_def for one of the context defined in the settings, here “nemo”:

.. code-block:: python

   generate_file_defs(lab_and_model_settings, simulation_settings, year=2000,context='nemo',
                      printout=True, cvs_path=my_cvspath)

where year is an optional argument (default is None) that allows to take into account the current
simulated year in the Data Request filtering.

..  note::
    To configure and run dr2xml, you can either use the iPython notebook DR2xml.ipynb available in
    dr2xml/ repository or the classical Python script DR2xml.py available in dr2xml/doc/.
