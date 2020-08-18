Annexe: Some Data Request vocabulary
====================================

In the Data Request world, there are different collections used to describe and refer to variables. It is
useful to have their definition in mind.

MIP Variable
------------

A MIP Variable (‘MIPvar’) defines a variable name and refers to the corresponding CF-standard
name when that standard exists. There is no notion of frequency nor spatial or temporal dimensions
for a MIP Variable.

A MIP variable is defined by the following attributes (for the exhaustive list of attributes see for
example, http://clipcservices.ceda.ac.uk/dreq/u/0e5d376315a376cd2b1e37f440fe43d3.html ):

- A label (e.g.: label=’tos’);
- A title (e.g.: title=’Sea Surface Temperature’);
- (possibly) A CF standard name (e.g: standarname=’SeaSurfaceTemperature’);
- Units (e.g.: units=‘K’).

Note that several MIP variables can refer the same CF standard name, e.g. the following MIP
variables all refer to the CF standard name ‘SurfaceAlbedo’:

- al: Albedo [%]
- alb: Surface Albedo
- albsrfc: surface albedo
- fal: Forecast Albedo
- lialb: Land ice or snow albedo
- lialbIs: Ice Sheet Ice or Snow Albedo
- surf-albedo: surface_albedo

CMOR Variable
-------------

A CMOR Variable (‘CMORvar’) is a declination of a MIP variable, associated to a realm and to a MIP
table with a particular output frequency and spatial/temporal structure.

A CMOR Variable is defined by the following attributes (for the exhaustive list of attributes see for
example, http://clipc-services.ceda.ac.uk/dreq/u/baa52de0-e5dd-11e5-8482-ac72891c3257.html)

- a variable identifier (e.g: vid=’0e5d376315a376cd2b1e37f440fe43d3’) that links to the base
  MIP Variable;
- a label (e.g.: label=’tos’ );
- a title (eg: title=’Sea Surface Temperature’ );
- a sampling frequency (e.g.: frequency=’mon’ );
- a modelling realm (e.g.: realm=’atmos’ );
- a mipTable (e.g.: table=’Omon’ );
- a structure identifier (e.g.: stid=’f7ddef0c-562c-11e6-a2a4-ac72891c3257’ ) that
  gather both temporal and spatial shapes information
- a default priority ( DefaultPriority =1)

Note that the label of the CMOR Variable may differ from the label associated MIP Variable (e.g.:
‘hus10’ and ‘hus27’ – specific humidity on different sets of pressure levels- are CMOR Variables
referring to the same MIP Variable ‘hus’ )
