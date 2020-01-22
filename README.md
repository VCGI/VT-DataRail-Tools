# VT-DataRail-Tools
VT DataRail Tools are tools that support sharing and exchange of geospatial-data resources per the VT EGC ([Enterprise GIS Consortium](https://vcgi.vermont.gov/partners/enterprise-gis-consortium)) Geospatial Data Exchange Protocol.

The tools are built with **arcpy**–via **ArcGIS Desktop 10.6.1 and Python 2.7.14**.

:heavy_exclamation_mark:Read the VT EGC Geospatial Data Exchange Protocol for important background information, protocol requirements, and definitions (**hub**, **spoke**, **push**, **pull**, etc.).

Each tool is either a script tool that is run via a provided toolbox named **VT DataRail Tools.tbx** or a stand-alone script that should be run directly in Python.


### Folder Structure ###
The repository root folder contains a toolbox--**VT DataRail Tools.tbx**, which references scripts by relative paths.

The **\scripts** subfolder contains:
- scripts that are referenced by **VT DataRail Tools.tbx**.
- stand-alone scripts (to be run directly in Python).

Each script has its own subfolder under **\scripts** .


More info on what **VT DataRail Tools** are and how to use them is in **\docs** subfolder.
