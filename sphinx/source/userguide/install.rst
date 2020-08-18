Installing dr2xml
=================

Prerequisites
-------------

You need Python 2.7. For some examples provided as iPython notebooks, you need either iPython or
the pure-python version of the notebooks (they are provided).

You need to have the CMIP6 Data Request package (available at
http://proj.badc.rl.ac.uk/svn/exarch/CMIP6dreq/tags/latest ) installed.

.. code-block:: bash

    svn co http://proj.badc.rl.ac.uk/svn/exarch/CMIP6dreq/tags/latest <My-CMIP6Dreq-Rep>
    cd <My-CMIP6Dreq-Rep>
    python setup.py install --user

And you must include <My-CMIP6Dreq-Rep>/dreqPy in your PYTHONPATH .

You will also need a local copy of CMIP6 Controlled Vocabulary. You will need to provide the path
<My-CMIP6CVs-Rep> where you install this CMIP6_CVs later on, at the dr2xml configuration stage.

.. code-block:: bash

    git clone https://github.com/WCRP-CMIP/CMIP6_CVs <My-CMIP6CVs-Rep>

Installing dr2xml
-----------------

Dr2xml is available on GitHub: https://github.com/rigoudyg/dr2xml

.. code-block:: bash

    git clone https://github.com/rigoudyg/dr2xml <My-dr2xml-Rep>