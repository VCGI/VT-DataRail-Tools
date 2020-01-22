#PURPOSE
#   For each of a given list of data items (feature classes, tables, rasters, etc.),
#   reads the item's metadata and determines if the ISO-Core metadata-elements are
#   populated--per the VT GIS Metadata Standard.
#
#   Writes a .txt report on findings. The report is appended if it already exists; this
#   allows 1 report to be provided for multiple items.

#README NOTES
#   vtDataRail_InspectMetadata.py is intended to be run in ArcGIS Desktop as a script tool
#   within a custom toolbox w/ the toolbox alias "vtDataRail".
#
#   This script only works when run in ArcGIS Desktop as a script tool. It doesn't work as
#   a stand-alone script; this is because this script uses
#   arcpy.ExportMetadata_conversion(), which doesn't work in stand-alone scripts.
#   arcpy.ExportMetadata_conversion() might have a 32-bit-process/64-bit-process issue.
#
#   In this script's scope, the important thing is having key (core) metadata in the data
#   item, regardless of the metadata style that is applied.
#
#   This script reads an item's metadata by exporting its metadata to 2 temporary files:
#      One is an FGDC-CSDGM XML-file.
#      The other is an ISO XML-file.
#   In case you are wondering why metadata is exported to 2 formats for reading:
#      -Some metadata content is more script-readable in 1 format vs. the other.
#      -Some FGDC CSDGM content isn't directly translatable to ISO, but can still be important.
#
#   In case you aren't very familiar with how metadata is stored and processed in ArcGIS...
#   The ArcGIS metadata format is a container of other formats (e.g., ISO 19115 NAP, FGDC
#   CSDGM, etc.). Metadata that is wired into an ArcGIS data-item (e.g., a feature class) is
#   always stored in the ArcGIS format; ArcGIS-format metadata contains elements that are
#   translatable to any ArcGIS-supported metadata standard PLUS some elements (e.g.,
#   thumbnail, geoprocessing history, etc.) that are only in the ArcGIS metadata format.
#
#   A metadata style is an ArcGIS setting that determines how metadata is viewed and edited
#   in the ArcGIS metadata editor. If a standard-related style (e.g., ISO 19115 NAP) is
#   applied, the metadata editor shows all elements of that style PLUS ArcGIS elements
#   that are extraneous to that style (e.g., thumbnail, geoprocessing history, etc.). An
#   execption to style yielding a superset is the Item Description style, which only shows
#   a subset of ArcGIS-metadata elements--even if the underlying metadata has been edited
#   to include content beyond the Item Description style.
#
#   To select a metadata style in ArcGIS Desktop:
#      Customize | *Options | Metadata tab

#HOW TO USE
#   Run as a script tool; pass in arguments per arguments described in script's section that
#   is commented w/:
#      #***** GET ARGUMENTS *****.

#HISTORY
#   DATE         ORGANIZATION     PROGRAMMER          NOTES
#   04/26/2019   VCGI             Ivan Brown          First stable release. Built w/ ArcGIS
#                                                     Desktop (arcpy) 10.6.1 and Python 2.7.14.

#PSEUDO CODE
#   Set major variables (via script arguments):
#      -semicolon-delimited string of data items (Data Elements)
#      -path of a folder (scratch folder) where temporary files are written
#      -path of output report-file (.txt)
#
#   Start output report by writing a header (append to the report file if it already exists).
#
#   For each given item:
#      Export the item's metadata to a temporary ISO file and a temporary FGDC-CSDGM XML file in scratch folder.
#      For each ISO-Core-element requirement:
#         Look for that element, either in the ISO file or as a counterpart in the CSDGM file.
#         If the element isn't populated, make note in report file.
#         Write other helpful findings into report file.
#         Delete the temporary files.
#
#   Finalize output report.

#IMPORT MODULES
print "IMPORTING MODULES..."
import time, sys, arcpy, uuid, os
import xml.etree.ElementTree as ET

#***** GET ARGUMENTS *****
#
#      PASS ARGUMENTS TO SCRIPT IN SAME ORDER AS PRESENTED HERE, WHICH IS:
#
#         <item_list> <SCRATCH_path> <report_path>
#
#Set "item_list" argument to a semicolon-delimited string of Data Element items for which metadata is inspected.
#   *****README!: Don't use enterprise-geodatabase items via a path that begins w/ "Database Connections\" as
#                 in ArcCatalog--items used via that type of path don't work! Instead, use an .sde file with a
#                 drive-based path (e.g., C:\myEGDBconnections\MyOrg.org-Planning_GDB.sde).
item_list = arcpy.GetParameterAsText(0)
#
#Set "scratch_path" argument to full path of folder in which temporary files are written. The temporary
#   files are metadata exports the script makes in order to read metadata. The files are named with GUIDs (e.g.,
#   164f13a4-8d4b-4d44-9fad-9d97a46c2382.xml). The script tries to delete the files when it is done reading.
#
scratch_path = arcpy.GetParameterAsText(1)
#
#Set "report_path" argument to full path of output report (.txt) to be written. The file is appended if
#   it already exists.
report_path = arcpy.GetParameterAsText(2)
#***** END OF SECTION FOR GETTING ARGUMENTS *****

#FUNCTIONS

#THIS FUNCTION CAPTURES A GIVEN STRING AND MAKES NOTE WITH IT PER ARGUMENTS
#   ARGUMENT 1 (STRING): THE STRING.
#   ARGUMENT 2 (INTEGER >= 0 AND <= 2): SET TO 0 IF NOTING INFO, 1 IF NOTING A WARNING, OR 2 IF NOTING AN ERROR.
def make_note(the_note, severity = 0):
   print the_note
   if severity == 0:
      arcpy.AddMessage(the_note)
   elif severity == 1:
      arcpy.AddWarning(the_note)
   else:
      arcpy.AddError(the_note)

#THIS FUNCTION SIMPLY CAPTURES THE CURRENT DATE AND RETURNS IT IN A PRESENTABLE
#   TEXT FORMAT MM/DD/YYYY.
#   FOR EXAMPLE:
#      04/11/2019
def tell_the_time():
   s = time.localtime()
   the_year = str(s.tm_year)
   the_month = str(s.tm_mon)
   the_day = str(s.tm_mday)
   #FORMAT THE MONTH TO HAVE 2 CHARACTERS
   while len(the_month) < 2:
      the_month = "0" + the_month
   #FORMAT THE DAY TO HAVE 2 CHARACTERS
   while len(the_day) < 2:
      the_day = "0" + the_day
   the_output = the_month + "/" + the_day + "/" + the_year
   return the_output

#THIS FUNCTION SIMPLY TAKES A STRING ARGUMENT AND THEN WRITES THE GIVEN STRING INTO
#   THE SCRIPT'S OUTPUT REPORT-FILE.
def add_to_report(the_string):
   report_file = open(report_path, "a")
   report_file.write(the_string)
   report_file.close()

#THIS FUNCTION LOOKS FOR A PARTICULAR SUB ELEMENT OF A GIVEN ELEMENT
#   ARGUMENT 1 IS THE PARENT ELEMENT.
#   ARGUMENT 2 IS THE SUB ELEMENT.
#   ARGUMENT 3 (OPTIONAL) IS A DICTIONARY THAT RELATES XML-NAMESPACE NAMES TO CORRESPONDING URLs.
#               FOR EXAPMLE, A GIVEN SUB-ELEMENT'S TAG LOOKS LIKE THIS INTERNALLY IN THE XML:
#                  {http://www.isotc211.org/2005/gco}CharacterString
#                  THE DICTIONARY RELATES "gco" TO "http://www.isotc211.org/2005/gco", SO THAT THE SUB-ELEMENTS ARE SEARCHED W/ A GIVEN SUB-ELEMENT TAG THAT LOOKS LIKE THIS:
#                    gco:CharacterString
#               DEFAULT IS None
#RETURNS A LIST OF SUB-ELEMENT OBJECTS
def find_sub(the_element, the_sub, the_namespaces = None):
   sub_list = []
   for i in the_element:
      the_str = i.tag
      #IF NAMESPACE DICTIONARY GIVEN, TRANSLATE
      if the_namespaces != None:
         if the_str[0:1] == "{":
            j = the_str.find("}")
            if j != -1:
               the_url = the_str[1:j]
               for k in the_namespaces:
                  if the_namespaces[k] == the_url:
                     the_str = k + ":" + the_str[j + 1:len(the_str)]
      if the_str.lower() == the_sub.lower():
         sub_list.append(i)
   return sub_list

#THIS FUNCTION TAKES:
#   ARGUMENT 1: AN ELEMENT OBJECT
#   ARGUMENT 2: AN ELEMENT-OBJECT PATH, RELATIVE TO ARGUMENT-1 ELEMENT OBJECT (USE FORWARD SLASHES!)
#                  FOR EXAMPLE:
#                     Movies/Movie represents a path relative to "Theater" ELEMENT:
#                        <Theater>
#                           <Movies>
#                              <Movie>Bee Movie</Movie>
#                              <Movie>Boss Baby</Movie>
#   ARGUMENT 3: (OPTIONAL) A DICTIONARY THAT RELATES XML-NAMESPACE NAMES TO CORRESPONDING URLs.
#               FOR EXAPMLE, A GIVEN ELEMENT TAG LOOKS LIKE THIS:
#                  <gco:CharacterString>
#                  THE DICTIONARY RELATES "gco" TO "http://www.isotc211.org/2005/gco", SO THAT THE ELEMENTS ARE SEARCHED W/ THIS:
#                    {http://www.isotc211.org/2005/gco}CharacterString
#               DEFAULT IS None
#RETURNS A LIST OF SUB-ELEMENT OBJECTS THAT ARE ON ACCORD W/ THE PATH'S ENDING ELEMENT.
def find_sub_by_path(the_element, the_path, the_namespaces = None):
   #IF NAMESPACE DICTIONARY GIVEN, TRANSLATE
   if the_namespaces != None:
      the_path = the_path.split("/")
      i = 0
      while i < len(the_path):
         j = the_path[i].find(":")
         if j != -1:
            the_ns = the_path[i][0:j]
            if the_ns in the_namespaces:
               the_path[i] = "{" + the_namespaces[the_ns] + "}" + the_path[i][j + 1:len(the_path[i])]
         i += 1
      new_path = ""
      i = 0
      while i < len(the_path):
         new_path += the_path[i]
         if i < len(the_path) - 1:
            new_path += "/"
         i += 1
      the_path = new_path
   #RETURN ALL ELEMENTS THAT ARE ON ACCORD W/ GIVEN PATH
   return the_element.findall(the_path)

try:
   #TURN item_list INFO A REAL LIST
   item_list = item_list.split(";")

   #START OUTPUT REPORT BY WRITING HEADER
   make_note("Writing report header...")
   add_to_report("********************************************\n")
   add_to_report("METADATA-INSPECTION REPORT - " + tell_the_time() + "\n")

   #GET METADATA TRANSLATORs
   make_note("Getting metadata translators...")
   install_dir = arcpy.GetInstallInfo()["InstallDir"]
   translator_ISO = install_dir + "Metadata\\Translator\\ARCGIS2ISO19139.xml"
   translator_CSDGM = install_dir + "Metadata\\Translator\\ARCGIS2FGDC.xml"

   #ANALYZE EACH ITEM
   for i in item_list:
      make_note("Starting on " + i + "...")
      #MAKE GUID-BASED FILENAMES FOR THE TEMPORARY METADATA-FILES (XML)
      a_GUID = str(uuid.uuid4())
      temp_filename_ISO = a_GUID + "_ISO.xml"
      temp_filename_CSDGM = a_GUID + "_CSDGM.xml"
      #EXPORT ITEM'S METADATA TO TEMPORARY METADATA-FILES (XML)
      make_note("Exporting metadata to temporary metadata-files...")
      #(ISO)
      arcpy.ExportMetadata_conversion(i, translator_ISO, os.path.join(scratch_path, temp_filename_ISO))
      #(CSDGM)
      arcpy.ExportMetadata_conversion(i, translator_CSDGM, os.path.join(scratch_path, temp_filename_CSDGM))
      #GET XML ROOT-ELEMENTS AND NAMESPACES (ISO ONLY)
      make_note("Getting metadata-XML root-elements and namespaces...")
      #(ISO)
      ISO_tree = ET.parse(os.path.join(scratch_path, temp_filename_ISO))
      ISO_root = ISO_tree.getroot()
      ISO_ns = {"gmd":"http://www.isotc211.org/2005/gmd","gco":"http://www.isotc211.org/2005/gco","gts":"http://www.isotc211.org/2005/gts","srv":"http://www.isotc211.org/2005/srv","gml":"http://www.opengis.net/gml","xlink":"http://www.w3.org/1999/xlink","xsi":"http://www.w3.org/2001/XMLSchema-instance"}
      #(CSDGM)
      CSDGM_tree = ET.parse(os.path.join(scratch_path, temp_filename_CSDGM))
      CSDGM_root = CSDGM_tree.getroot()
      #
      add_to_report("\n++++++++++++++++++++++++++++++++++++++++++++\n")
      add_to_report(arcpy.Describe(i).baseName + "\n")
      #TRACK WHETHER ISSUES ARE FOUND FOR THE ITEM
      issues_found = False
      #title ELEMENT
      make_note("Analyzing title...")
      e = find_sub_by_path(CSDGM_root, "idinfo/citation/citeinfo/title")
      if len(e) == 0:
         add_to_report("ERROR: Doesn't have required title.\n")
         issues_found = True
      elif e[0].text == None:
         add_to_report("ERROR: Doesn't have required title.\n")
         issues_found = True
      else:
         pass
      #dataset reference date ELEMENTS
      make_note("Analyzing data reference-dates...")
      found_creation_date = False
      found_publication_date = False
      found_revision_date = False
      e = find_sub_by_path(ISO_root, "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date", ISO_ns)
      if len(e) > 0:
         for j in e:
            the_date = None
            f = find_sub_by_path(j, "gmd:CI_Date/gmd:date/gco:Date", ISO_ns)
            if len(f) == 0:
               f = find_sub_by_path(j, "gmd:CI_Date/gmd:date/gco:DateTime", ISO_ns)
            if len(f) > 0:
               the_date = f[0].text
            if the_date != None:
               f = find_sub_by_path(j, "gmd:CI_Date/gmd:dateType/gmd:CI_DateTypeCode", ISO_ns)
               if len(f) > 0:
                  if f[0].text != None:
                     the_datetype = f[0].text.lower()
                     if the_datetype == "creation":
                        found_creation_date = True
                     if the_datetype == "publication":
                        found_publication_date = True
                     if the_datetype == "revision":
                        found_revision_date = True
      if found_creation_date == False and found_publication_date == False and found_revision_date == False:
         add_to_report("ERROR: No dataset dates found.\n")
         issues_found = True
      if found_creation_date == False or found_revision_date == False:
         add_to_report("Best practice for dataset dates is to at least include a creation date and a revision date.\n")  
      #abstract ELEMENT
      print "Analyzing abstract..."
      e = find_sub_by_path(CSDGM_root, "idinfo/descript/abstract")
      if len(e) == 0:
         add_to_report("ERROR: Doesn't have required abstract.\n")
         issues_found = True
      elif e[0].text == None:
         add_to_report("ERROR: Doesn't have required abstract.\n")
         issues_found = True
      else:
         pass
      #dataset language ELEMENT
      make_note("Analyzing dataset language...")
      e = find_sub_by_path(ISO_root, "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode", ISO_ns)
      if len(e) == 0:
         add_to_report("ERROR: Doesn't have dataset language (3-character, such as eng for English).\n")
         issues_found = True
      elif e[0].text == None:
         add_to_report("ERROR: Doesn't have dataset language (3-character, such as eng for English).\n")
         issues_found = True
      else:
         pass
      #geographic-location (e.g, bounding coordinates) ELEMENTS
      make_note("Analyzing geographic-location info...")
      e = find_sub_by_path(ISO_root, "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox", ISO_ns)
      if len(e) > 0:
         e = e[0]
         west = None
         east = None
         south = None
         north = None
         f = find_sub_by_path(e, "gmd:westBoundLongitude/gco:Decimal", ISO_ns)
         if len(f) > 0:
            west = f[0].text
         f = find_sub_by_path(e, "gmd:eastBoundLongitude/gco:Decimal", ISO_ns)
         if len(f) > 0:
            east = f[0].text
         f = find_sub_by_path(e, "gmd:southBoundLatitude/gco:Decimal", ISO_ns)
         if len(f) > 0:
            south = f[0].text
         f = find_sub_by_path(e, "gmd:northBoundLatitude/gco:Decimal", ISO_ns)
         if len(f) > 0:
            north = f[0].text
         if west == None or east == None or south == None or north == None:
            add_to_report("ERROR: Doesn't have complete geographic bounding coordinates.\n")
            issues_found = True
      else:
         found_description = False
         e = find_sub_by_path(ISO_root, "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString", ISO_ns)
         if len(e) == 0:
            e = find_sub_by_path(ISO_root, "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString", ISO_ns)
         if len(e) == 0:
            add_to_report("ERROR: Doesn't have geographic bounding coordinates nor a geographic identifier.\n")
            issues_found = True
         else:
            if e[0].text == None:
               add_to_report("ERROR: Doesn't have geographic bounding coordinates nor a geographic identifier.\n")
               issues_found = True
            else:
               found_description = True
         if found_description == True:
            add_to_report("Didn't find geographic bounding coordinates. However, metadata does appear to have a geographic description (which meets the geographic-location requirement); consider adding geographic bounding coordinates.\n")
      #dataset characterset ELEMENT
      make_note("Analyzing dataset characterset...")
      e = find_sub_by_path(ISO_root, "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:characterSet/gmd:MD_CharacterSetCode", ISO_ns)
      if len(e) == 0:
         add_to_report("ERROR: Doesn't have a dataset characterset.\n")
         issues_found = True
      elif e[0].text == None:
         add_to_report("ERROR: Doesn't have a dataset characterset.\n")
         issues_found = True
      else:
         pass
      #point of contact ELEMENTS
      make_note("Analyzing points of contact...")
      e = find_sub_by_path(ISO_root, "gmd:contact/gmd:CI_ResponsibleParty", ISO_ns)
      if len(e) > 0:
         individual = None
         organization = None
         position = None
         f = find_sub_by_path(e[0], "gmd:individualName/gco:CharacterString", ISO_ns)
         if len(f) > 0:
            individual = f[0].text
         f = find_sub_by_path(e[0], "gmd:organisationName/gco:CharacterString", ISO_ns)
         if len(f) > 0:
            organization = f[0].text
         f = find_sub_by_path(e[0], "gmd:positionName/gco:CharacterString", ISO_ns)
         if len(f) > 0:
            position = f[0].text
         if individual == None and organization == None and position == None:
            add_to_report("ERROR: Doesn't have point-of-contanct info.\n")
            issues_found = True
      else:
         add_to_report("ERROR: Doesn't have point-of-contanct info.\n")
         issues_found = True
      #metadata date ELEMENT
      make_note("Analyzing metadata date...")
      e = find_sub_by_path(CSDGM_root, "metainfo/metd")
      if len(e) == 0:
         add_to_report("ERROR: Doesn't have metadata date.\n")
         issues_found = True
      elif e[0].text == None:
         add_to_report("ERROR: Doesn't have metadata date.\n")
         issues_found = True
      else:
         pass
      #topic-category ELEMENTS
      make_note("Analyzing topic-categories...")
      e = find_sub_by_path(ISO_root, "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode", ISO_ns)
      found_a_topic = False
      for j in e:
         if j.text != None:
            found_a_topic = True
      if found_a_topic == False:
         add_to_report("ERROR: Doesn't have topic categories.\n")
         issues_found = True
      #reference system ELEMENT
      make_note("Analyzing reference system...")
      e = find_sub_by_path(ISO_root, "gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString", ISO_ns)
      if len(e) == 0:
         add_to_report("ERROR: Doesn't have reference-system info.\n")
         issues_found = True
      elif e[0].text == None:
         add_to_report("ERROR: Doesn't have reference-system info.\n")
         issues_found = True
      else:
         pass
      #metadata language ELEMENT
      make_note("Analyzing metadata language...")
      e = find_sub_by_path(ISO_root, "gmd:language/gmd:LanguageCode", ISO_ns)
      if len(e) == 0:
         add_to_report("ERROR: Doesn't have metadata language.\n")
         issues_found = True
      elif e[0].text == None:
         add_to_report("ERROR: Doesn't have metadata language.\n")
         issues_found = True
      else:
         if e[0].text.find(";") == -1:
            add_to_report("Found metadata language '" + e[0].text + "'. Best practice for metadata language is 3-letter language code followed by a ';', followed by 3-letter country code (e.g., English in USA is 'eng; USA').\n")
      #metadata characterset ELEMENT
      make_note("Analyzing metadata characterset...")
      e = find_sub_by_path(ISO_root, "gmd:characterSet/gmd:MD_CharacterSetCode", ISO_ns)
      if len(e) == 0:
         add_to_report("ERROR: Doesn't have metadata characterset.\n")
         issues_found = True
      elif e[0].text == None:
         add_to_report("ERROR: Doesn't have metadata characterset.\n")
         issues_found = True
      else:
         pass
      #field descriptions (not required but very recommended)
      make_note("Finding out if item has fields...")
      has_fields = False
      found_empty_def = False
      try:
         the_fields = arcpy.Describe(i).fields
         field_list = []
         for j in the_fields:
            if j.type != "OID" and j.name.lower() != "shape":
               field_list.append({"name":j.name,"aliasName":j.aliasName,"in_metadata":False})
               has_fields = True
         field_starter = "FIELD DESCRIPTIONS---------------\n"
         for j in field_list:
            field_starter += j["name"] + " -" + j["aliasName"] + "\n"
         field_starter += "---------------------------------\n"
      except:
         pass
      if has_fields == True:
         make_note("Yes. The item has fields. Analyzing them...")
         e = find_sub_by_path(CSDGM_root, "eainfo/detailed/attr")
         for f in e:
            g = find_sub(f, "attrlabl")
            h = find_sub(f, "attrdef")
            if len(g) > 0 and len(h) > 0:
               if g[0].text != None and h[0].text != None:
                  for j in field_list:
                     if j["name"].lower() == g[0].text.lower():
                        j["in_metadata"] = True
         for j in field_list:
            if j["in_metadata"] == False:
               add_to_report("DIDN'T FIND field description for field " + j["name"] + ".\n")
               found_empty_def = True
            else:
               add_to_report("Found field description for field " + j["name"] + ".\n")
         if found_empty_def == True:
            add_to_report("Field descriptions aren't required but are very recommended.\n")
            add_to_report("Found incomplete field-descriptions in export's field-description section (CSDGM eainfo); that doesen't mean fields aren't described somewhere else in the metadata.\n")
            add_to_report("Helpful brief field descriptions can be entered into the 'abstract'.\n")
            add_to_report("For convenience, here is the item's field list, which can be copied as a starter for entering field descriptions in the abstract.\n")
            add_to_report(field_starter)
         else:
            pass
      else:
         make_note("No. The item doesn't have fields.")

      #DELETE TEMP XML-FILES
      make_note("Deleting temporary XML-files...")
      arcpy.Delete_management(os.path.join(scratch_path, temp_filename_ISO))
      arcpy.Delete_management(os.path.join(scratch_path, temp_filename_CSDGM))

      #FINALIZE REPORT ENTRY FOR ITEM
      if issues_found == True:
         add_to_report("DOESN'T APPEAR TO MEET STANDARD: Item's metadata doesn't appear to meet the ISO-Core metadata requirements of the VT GIS Metadata Standard.\n")
      elif has_fields == True and found_empty_def == True:
         add_to_report("CONSIDER MAKING SURE FIELD DESCRIPTIONS ARE CAPTURED IN METADATA. Item's metadata appears to meet the ISO-Core metadata requirements of the VT GIS Metadata Standard. However, it appears to have incomplete field descriptions (which aren't required but are very recommended).\n")
      else:
         add_to_report("SUPER! Item's metadata appears to meet the ISO-Core metadata requirements of the VT GIS Metadata Standard!\n")

   #FINALIZE REPORT
   add_to_report("\nEND OF REPORT\n")
   add_to_report("********************************************\n")

except:
   make_note("Script failed due to error condition.", 2)
