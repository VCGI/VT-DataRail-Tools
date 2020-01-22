#PURPOSE
#Pushes or pulls data from a source geodatabase to a target geodatabase--supporting the
#Vermont Enterprise GIS Consortium (EGC) Geospatial Data Exchange Protocol.

#README NOTES
#Data-object types that can be pushed/pulled with this script are:
#   -feature class
#   -non-spatial table (must be discoverable by browsing geodatabase)
#   -view-based data, vector or non-spatial (must be discoverable by browsing geodatabase)
#   -raster dataset
#
#Integrity-assertion objects--such as a topolgies and network datasets--aren't pushed/pulled.
#Not pushing/pulling them is prudent, as they might not function in the target-location's
#geodatabase release.
#
#Most data can be exchanged without a lot of consideration around disk-space capacity in the target
#location. Exceptionally large datasets require particularly careful disk-space planning before
#being pushed/pulled. Check target-location capacity before pushing/pulling a large new
#dataset.
#
#BOTH geodatabases involved with the push/pull must have a populated non-spatial table named
#A_README as articulated in the EGC Geospatial Data Exchange Protocol.
#
#If a geodatabase is a SPOKE geodatabase, the SPOKE geodatabase must have a non-spatial table
#named A_XCHANGE_PARAMETERS as articulated in the EGC Geospatial Data Exchange Protocol.
#
#If a geodatabase is a HUB geodatabase, the HUB geodatabase must have a non-spatial table
#named A_XCHANGE_LOG as articulated in the EGC Geospatial Data Exchange Protocol.
#
#Stand-alone feature-classes are pushed/pulled as stand-alone feature-classes to the target.
#
#If a source feature-class is within a feature dataset, the script searches for a feature
#dataset that has the same name in the target. If the feature dataset is found in the target,
#the script pushes/pulls data to a feature class within the target feature-dataset. If the
#target feature-dataset isn't found in the target, the script creates the feature dataset in
#the target and pushes/pulls data to a feature class within the target feature-dataset.
#
#Source-geodatabase views (when discoverable by browsing the geodatabase) are pushed/pulled
#as non-view counterparts (e.g., regular feature-class) in the target.
#
#When a feature class or table (or view) is pushed/pulled and it already exists in the target
#geodatabase, fields of the target geodatabase that aren't reflected in the source geodatabase
#are populated with Null values, AND fields of the source geodatabase that aren't reflected
#in the target geodatabase don't carry their values to the target.
#
#When a raster dataset is pushed/pulled and it already exists in the target geodatabase, an
#exclusive lock is required for the target-geodatabase connection because the script
#deletes the target raster-dataset and then replaces it by copying from source geodatabase.
#An "exclusive lock" means that no other users can be connected to the data object.
#Consult with a DBA for more info.
#
#Source-geodatabase multi-versioned data-objects that don't already exist in the target
#geodatabase are pushed/pulled as non-versioned data-objects in the target. AVOID
#PUSHING/PULLING DATA TO MULTI-VERSIONED TARGET-GEODATABASE DATA-OBJECTS; DOING SO MIGHT
#CREATE ENORMOUS DELTA TABLES AND CAUSE POOR PERFORMANCE IN THE TARGET GEODATABASE.
#
#Metadata is only carried along through the push/pull if the data object doesn't already
#exist in the target location (because in that case, the data object is copied and pasted
#as opposed to loaded by row). Make sure that metadata is kept current in both the source
#data-object and its target counterpart.
#
#This script logs its activity to a log file (vtDataRail_SendFreight.log) which is written into the
#script's directory at execution time. Periodically truncate or delete the log file to
#preserve disk space.
#
#Run this script directly in Python--not in ArcGIS Desktop (ArcToolbox). In ArcToolbox (for
#an unknown reason), the script sometimes has a problem with getting a correct result from
#arcpy.ListTables().

#HOW TO USE
#   Run in Python (not in ArcGIS Desktop); set major variables in script's section that is
#   commented w/:
#      #********** SET MAJOR VARIABLES HERE **********.

#HISTORY
#   DATE         ORGANIZATION     PROGRAMMER          NOTES
#   09/26/2019   VCGI             Ivan Brown          First stable release. Built w/ ArcGIS
#                                                     Desktop (arcpy) 10.6.1 and Python 2.7.14.

#PSEUDO CODE
#   Set major variables (via script arguments):
#      source_gdb:          Path of the source geodatabase. A database-connection file that
#                           connects to an entperprise geodatabase (.sde) OR path of a file
#                           geodatabase. The database connection must have permission to
#                           read all data objects to be pushed/pulled.
#
#                           The connection must have permission to read the A_README table.
#
#                           If the geodatabase is a SPOKE geodatabase, the connection must
#                           have permission to read the A_XCHANGE_PARAMETERS table.
#
#      target_gdb:          Path of the target geodatabase. A database-connection file that
#                           connects to an entperprise geodatabase (.sde) OR path of a file
#                           geodatabase. The database connection must have permission to
#                           write and overwrite data objects. Consult with a DBA for more
#                           info.
#
#                           The connection must have permission to read the A_README table.
#
#                           If the geodatabase is a HUB geodatabase, the connection must
#                           have permission to write to the A_XCHANGE_LOG table.
#
#   Verify connectivity to each geodatabase.
#
#   Verify that source geodatabase has an A_README table and determine if source geodatabase
#   is a SPOKE geodatabase or a HUB geodatabase.
#
#   If the source geodatabase is a SPOKE geodatabase, verify existence of its
#   A_XCHANGE_PARAMETERS table.
#
#   Verify that target geodatabase has an A_README table and determine if target geodatabase
#   is a SPOKE geodatabase or a HUB geodatabase.
#
#   If the target geodatabase is a HUB geodatabase, verify existence of its A_XCHANGE_LOG
#   table.
#
#   Get lists of pre-existing data-objects for easy searching/finding:
#      List of source feature-classes w/ schema prefixes
#      List of source feature-class schema-prefixes
#      List of source feature-classes w/o schema prefixes
#      List of source corresponding feature-datasets w/ schema prefixes, "" if N/A
#      List of source corresponding feature-dataset schema prefixes, "" if N/A
#      List of source corresponding feature-datasets w/o schema prefixes, "" if N/A
#      List of source tables w/ schema prefixes (except for from A_README, A_XCHANGE_PARAMETERS, and A_XCHANGE_LOG tables)
#      List of source-table schema-prefixes (except for from A_README, A_XCHANGE_PARAMETERS, and A_XCHANGE_LOG tables)
#      List of source tables w/o schema prefixes (except for from A_README, A_XCHANGE_PARAMETERS, and A_XCHANGE_LOG tables)
#      List of source raster-datasets w/ schema prefixes
#      List of source-raster-dataset schema-prefixes
#      List of source raster-datasets w/o schema prefixes
#      List of target feature-classes w/ schema prefixes
#      List of target feature-class schema-prefixes
#      List of target feature-classes w/o schema prefixes
#      List of target corresponding feature-datasets w/ schema prefixes, "" if N/A
#      List of target corresponding feature-dataset schema prefixes, "" if N/A
#      List of target corresponding feature-datasets w/o schema prefixes, "" if N/A
#      List of target tables w/ schema prefixes (except for from A_README, A_XCHANGE_PARAMETERS, and A_XCHANGE_LOG tables)
#      List of target-table schema-prefixes (except for from A_README, A_XCHANGE_PARAMETERS, and A_XCHANGE_LOG tables)
#      List of target tables w/o schema prefixes (except for from A_README, A_XCHANGE_PARAMETERS, and A_XCHANGE_LOG tables)
#      List of target raster-datasets w/ schema prefixes
#      List of target-raster-dataset schema-prefixes
#      List of target raster-datasets w/o schema prefixes
#
#   Make a list called "freight_cars" to store dictionary objects that manage each data-object transfer.
#
#      Dictionaries have these keys and values:
#         KEY                              VALUE
#         source_prefix                    Schema prefix of data object on source side. Set to
#                                          None if source is a file geodatabase.
#
#         fds                              Name of feature dataset (w/o schema prefix) that
#                                          stores the data object. Set to None if data object
#                                          isn't in a feature dataset.
#
#         name                             Name of data object w/o schema prefix.
#
#         type                             Type of data object. "fclass" for feature class,
#                                          "table" table, "raster" for raster dataset.
#
#         detect_changes                   Boolean to indicate if the data object is
#                                          pushed/pulled only if changes (geometry and/or
#                                          attribute) are detected. Only in-play when "type"
#                                          is "fclass" or "table".
#
#         sort_field                       If "detect_changes" is True, set to field to sort
#                                          for change detection. Otherwise, set to None.
#
#         already_there                    Boolean to indicate if data object already exists on
#                                          target side.
#
#         target_prefix                    If the data object already exists on the target
#                                          side, the target data-object's schema prefix.
#                                          Otherwise, set to "".
#
#   If the source geodatabase is a SPOKE geodatabase and its A_XCHANGE_PARAMETERS table has rows:
#      For each A_XCHANGE_PARAMETERS row:
#         If IS_FDATASET is True:
#            If the feature dataset exists in the source geodatabase:
#               If the feature dataset doesn't exist in the target geodatabase:
#                  Create it
#               For each feature class in source feature-dataset:
#                  Add object to freight_cars list
#         Otherwise:
#            If the data object exists in the source geodatabase:
#               If the data object is in a feature dataset:
#                  If the feature dataset doesn't exist on the target side:
#                     Create it
#               Add object to freight_cars list
#
#   Otherwise:
#      For each source data object:
#         If the data object is in a feature dataset:
#            If the feature dataset doesn't exist in the target geodatabase:
#               Create it
#            Add object to freight_cars list
#
#   For each freight_cars item:
#      If the data object doesn't already exist in the target, copy it to target
#      Otherwise:
#         If the data object is a feature class or a table:
#            If detect_changes is True:
#               If changes are detected between source and target:
#                  Delete target-rows and then append from source to target
#               Otherwise:
#                  Make note that changes weren't found
#            Otherwise:
#               Delete target-rows and then append from source to target
#         Otherwise (it's a raster):
#            Delete the raster dataset from the target geodatabase
#            Copy the raster dataset from the source geodatabase to the target geodatabase
#      If data object is a feature class or table, capture:
#         source-geodatabase row-count
#         target-geodatabase row-count
#      If target geodatabase is a HUB geodatabase:
#         Write an entry in target geodatabase's A_XCHANGE_LOG to note the push/pull
#
#   Prepare and send an email w/ info collected during script execution.

#IMPORTS
print "IMPORTING MODULES..."
import arcpy, sys, time, smtplib

#********** SET MAJOR VARIABLES HERE **********
print "SETTING MAJOR VARIABLES..."
#source_gdb
#   Path of the source geodatabase. A database-connection file that
#   connects to an entperprise geodatabase (.sde) OR path of a file
#   geodatabase. The database connection must have permission to
#   read all data objects to be pushed/pulled.
#
#   The connection must have permission to read the A_README table.
#
#   If the geodatabase is a SPOKE geodatabase, the connection must
#   have permission to read the A_XCHANGE_PARAMETERS table.
#
#   If the source geodatabase is an enterprise goedatabase, connect
#   to the appropriate version.
#
#   If script will be run as an automated task, save password to
#   connection; connecting as a read-only login is recommended.
source_gdb = r""
#
#target_gdb
#   Path of the target geodatabase. A database-connection file that
#   connects to an entperprise geodatabase (.sde) OR path of a file
#   geodatabase. The database connection must have permission to
#   write and overwrite data objects. Consult with a DBA for more
#   info.
#
#   The connection must have permission to read the A_README table.
#
#   If the geodatabase is a HUB geodatabase, the connection must
#   have permission to write to the A_XCHANGE_LOG table.
#
#   If the target geodatabase is an enterprise geodatabase, set to
#   the path of an .sde file.
#
#   If the target geodatabase is an enterprise goedatabase, connect
#   to the appropriate version, which should be SDE.DEFAULT in most
#   cases and certainly SDE.DEFAULT when the target geodatabase is a
#   HUB geodatabase.
#
#   If script will be run as an automated task, save password to
#   connection.
target_gdb = r""
#
#email_server
#   The host name of the SMTP router to be used for sending email report.
#   If you don't want the script to send email, set to an empty string.
email_server = ""
#
#email_port
#   The port number of the SMTP router to be used for sending email. Set to a string.
#   If you don't want the script to send email, set to an empty string.
email_port = ""
#
#email_from
#   The sender email address to be used with email notifications (must be in
#   name@domain format). An email account that is used for automated notifications in
#   your organization can be used.
#   If you don't want the script to send email, set to an empty string.
email_from = ""
#
#to_list
#   This setting is used to store email addresses of email recipients (must be in
#   name@domain format). Set to a Python list.
#
#   If you don't want the script to send email, set to an empty list.
#
#   For example:
#
#      ["name1@domain1","name2@domain2"]
#
to_list = []
#********** END OF SECTION FOR SETTING MAJOR VARIABLES **********

#CONSTANTS
print "SETTING CONSTANTS..."
#IGNORE_PARAM STORES IGNORE OPTIONS FOR SPATIAL DATA COMPARISON
IGNORE_PARAM = ["IGNORE_M","IGNORE_Z","IGNORE_POINTID","IGNORE_EXTENSION_PROPERTIES","IGNORE_SUBTYPES","IGNORE_RELATIONSHIPCLASSES","IGNORE_REPRESENTATIONCLASSES","IGNORE_FIELDALIAS"]
#IGNORE_PARAM_T STORES IGNORE OPTIONS FOR NON-SPATIAL (TABLE) DATA COMPARISON
IGNORE_PARAM_T = ["IGNORE_EXTENSION_PROPERTIES","IGNORE_SUBTYPES","IGNORE_RELATIONSHIPCLASSES","IGNORE_FIELDALIAS"]

#OTHER VARIABLES
print "SETTING OTHER VARIABLES..."
#email_content COLLECTS STRINGS ALONG THE WAY TO ADD TO EMAIL-NOTIFICATION CONTENT
email_content = ""
#email_switch IS A BOOLEAN THAT INDICATES IF EMAIL OPTION IS BEING USED.
#(ANALYZE MAJOR VARIABLES TO DETERMINE IF USING EMAIL OPTION)
if email_server != "":
   email_switch = True
else:
   email_switch = False

#FUNCTIONS

#THIS FUNCTION SIMPLY CAPTURES THE CURRENT DATE AND TIME AND
#   RETURNS IN A PRESENTABLE TEXT FORMAT YYYYMMDD-HHMM
#   FOR EXAMPLE:
#      20171201-1433
def tell_the_time():
   the_year = str(time.localtime().tm_year)
   the_month = str(time.localtime().tm_mon)
   the_day = str(time.localtime().tm_mday)
   the_hour = str(time.localtime().tm_hour)
   the_minute = str(time.localtime().tm_min)
   #FORMAT THE MONTH TO HAVE 2 CHARACTERS
   while len(the_month) < 2:
      the_month = "0" + the_month
   #FORMAT THE DAY TO HAVE 2 CHARACTERS
   while len(the_day) < 2:
      the_day = "0" + the_day
   #FORMAT THE HOUR TO HAVE 2 CHARACTERS
   while len(the_hour) < 2:
      the_hour = "0" + the_hour
   #FORMAT THE MINUTE TO HAVE 2 CHARACTERS
   while len(the_minute) < 2:
      the_minute = "0" + the_minute
   the_output = the_year + the_month + the_day + "-" + the_hour + the_minute
   return the_output

#THIS FUNCTION SIMPLY TAKES A STRING ARGUMENT AND THEN
#   WRITES THE GIVEN STRING INTO THE SCRIPT'S LOG FILE.
#   SET FIRST ARGUMENT TO THE STRING. SET THE SECOND
#   ARGUMENT (BOOLEAN) TO True OR False TO INDICATE IF
#   STRING SHOULD ALSO BE PRINTED. SET THE THIRD
#   ARGUMENT (BOOLEAN) TO True OR False TO INDICATE IF
#   STRING SHOULD ALSO BE INCLUDED IN EMAIL NOTIFICATION.
#   ADDS CURRENT TIME TO BEGINNING OF the_note PARAMETER.
#   ADDS A \n TO the_note PARAMETER (FOR HARD RETURNS).
def make_note(the_note, print_it = False, email_it = False):
   the_note = tell_the_time() + "  " + the_note
   the_note += "\n"
   log_file = open(sys.path[0] + "\\vtDataRail_SendFreight.log", "a")
   log_file.write(the_note)
   log_file.close()
   if print_it == True:
      print the_note
      arcpy.AddMessage(the_note)
   if email_it == True:
      global email_content
      email_content += the_note

#THIS FUNCTION RETURNS SCHEMA PREFIX (DATABASE.OWNER.) FROM A GIVEN DATA-OBJECT NAME (FEATURE CLASS, TABLE, OR RASTER DATASET)
#   IF THE DATA OBJECT HAS NO SCHEMA PREFIX (E.G., FILE-GEODATABASE FEATURE-CLASS), RETURNS ""
def get_schema_prefix(the_data_object):
   i = the_data_object.rfind(".")
   if i == -1:
      return ""
   else:
      return the_data_object[0:i + 1]

#THIS FUNCTION RETURNS DATA-OBJECT NAME (MINUS SCHEMA PREFIX, (DATABASE.OWNER.)) FROM A GIVEN DATA-OBJECT NAME (FEATURE CLASS, TABLE, OR RASTER DATASET)
#   IF THE DATA OBJECT HAS NO SCHEMA PREFIX (E.G., FILE-GEODATABASE FEATURE-CLASS), RETURNS THE GIVEN NAME
def get_name(the_data_object):
   i = the_data_object.rfind(".")
   if i == -1:
      return the_data_object
   else:
      return the_data_object[i + 1:len(the_data_object)]

#THIS FUNCTION DELETES ROWS OF A TARGET DATA-OBJECT AND APPENDS ROWS TO TARGET DATA-OBJECT FROM SOURCE DATA-OBJECT
#   THE FIRST ARGUMENT IS THE FULL PATH OF THE SOURCE DATA-OBJECT
#   THE SECOND ARGUMENT IS THE FULL PATH OF THE TARGET DATA-OBJECT
def load_rows(source_obj, target_obj):
   arcpy.DeleteRows_management(target_obj)
   arcpy.Append_management(source_obj, target_obj, "NO_TEST")

#THIS FUNCTION COMPARES 2 FEATURECLASSES OR 2 TABLES AND REPORTS ON WHETHER THEY ARE THE SAME DATA.
#   THE FIRST ARGUMENT IS THE FULL PATH OF THE SOURCE DATA-OBJECT.
#   THE SECOND ARGUMENT IS THE FULL PATH OF THE TARGET DATA-OBJECT.
#   THE THIRD ARGUMENT IS A BUSINESS-FIELD NAME FOR FIELD TO BE USED FOR SORTING THE DATA OBJECTS
#      FOR COMPARING.
#   THE FOURTH ARGUMENT IS A BOOLEAN TO INDICATE IF THE DATA OBJECT IS NON-SPATIAL (A TABLE).
#      (True IF TABLE, False IF NOT TABLE)
#   RETURNS "same" IF THE DATA OBJECTS ARE THE SAME.
#   RETURNS "different" IF THE DATA OBJECTS ARE DIFFERENT.
#   RETURNS "error" IF SOMETHING GOES WRONG, LIKE THE BUSINESS FIELD NOT EXISTING IN ONE OF THE DATA OBJECTS
def compare_objects(source_obj = "", target_obj = "", sort_field = "", non_spatial = False):
   try:
      #IF DATA OBJECT IS SPATIAL
      if non_spatial == False:
         the_result = arcpy.FeatureCompare_management(target_obj, source_obj, sort_field, "ALL", IGNORE_PARAM, "0 METERS", 0, 0, "#", "OBJECTID")
         if the_result.getOutput(1) == "false":
            return "different"
         else:
            return "same"
      #OTHERWISE, IT MUST BE NON-SPATIAL
      else:
         the_result = arcpy.TableCompare_management(target_obj, source_obj, sort_field, "ALL", IGNORE_PARAM_T, "#", "OBJECTID")
         if the_result.getOutput(1) == "false":
            return "different"
         else:
            return "same"
   except:
      return "error"

#THIS FUNCTION TAKES A DATA OBJECT AND RETURNS ITS ROW COUNT (AS STRING).
def get_count(the_data_object):
   return arcpy.GetCount_management(the_data_object).getOutput(0)

#THIS FUNCTION SENDS A GIVEN MESSAGE TO AN EMAIL DISTRIBUTION-LIST
#   THE FIRST ARGUMENT IS THE EMAIL'S SUBJECT STRING
#   THE SECOND ARGUMENT IS THE EMAIL'S MESSAGE-CONTENT STRING
def send_email(the_subject = "", the_message = ""):
   the_header = 'From:  "Python" <' + email_from + '>\n'
   the_header += "To:  VT DataRail Tools User\n"
   the_header += "Subject:  " + the_subject + "\n"
   #INSTANTIATE AN SMTP OBJECT
   smtp_serv = smtplib.SMTP(email_server + ":" + email_port)
   #SEND THE EMAIL
   smtp_serv.sendmail(email_from, to_list, the_header + the_message)
   #QUIT THE SERVER CONNECTION
   smtp_serv.quit()

#THIS FUNCTION RETURNS A LIST OF FIELD NAMES OF A GIVEN TABLE OR FEATURE CLASS, EXCLUDING FIELD NAMED OBJECTID AND FIELD NAMES THAT BEGIN WITH SHAPE
#  ARGUMENT 1: THE TABLE OR FEATURE CLASS.
#  ARGUMENT 2: OPTIONAL. A LIST OF FIELD NAMES TO BE EXCLUDED FROM THE OUTPUT LIST. MUST USE ALL-CAPS.
def get_field_names(the_table, exclude_list = None):
   the_fields = arcpy.ListFields(the_table)
   the_field_names = []
   for i in the_fields:
      if i.name.upper() != "OBJECTID" and i.name.upper()[0:4] != "SHAPE":
         if exclude_list:
            if i.name.upper() not in exclude_list:
               the_field_names.append(i.name)
         else:
            the_field_names.append(i.name)
   return the_field_names

#THIS FUNCTION TAKES A LIST OBJECT (1ST ARGUMENT) AND A STRING (2ND ARGUMENT)
#   FINDS THE FIRST LIST ITEM EQUAL TO THE GIVEN STRING (NOT CASE-SENSITIVE)
#   RETURNS THE INDEX OF THAT LIST ITEM
#   RETURNS -1 IF STRING WASN'T FOUND IN LIST
def get_index(the_list, the_string):
   found_it = False
   i = 0
   while i < len(the_list) and found_it == False:
      if the_list[i].upper() == the_string.upper():
         found_it = True
      else:
         i += 1
   if found_it == True:
      return i
   else:
      return -1

#THIS FUNCTION CREATES AND RETURNS A DICTIONAIRY OBJECT (A FREIGHT CAR) TO ADD TO freight_cars LIST
def create_freight_car(source_prefix, fds, name, type, detect_changes, sort_field, already_there, target_prefix):
   return {"source_prefix":source_prefix,"fds":fds,"name":name,"type":type,"detect_changes":detect_changes,"sort_field":sort_field,"already_there":already_there,"target_prefix":target_prefix}

try:
   #VERIFY GEODATABASE CONNECTIONS
   make_note("Verifying geodatabase connections...")
   if arcpy.Exists(source_gdb) != True:
      make_note("Can't connect to source geodatabase:  " + source_gdb, True, True)
      sys.exit()
   if arcpy.Exists(target_gdb) != True:
      make_note("Can't connect to target geodatabase:  " + target_gdb, True, True)
      sys.exit()
   make_note("Source geodatabase: " + source_gdb, True, True)
   make_note("Target geodatabase: " + target_gdb, True, True)

   #READ AND ANALYZE SOURCE-GEODATABASE'S A_README TABLE
   make_note("Reading and analyzing source-geodatabase's A_README table...")
   arcpy.env.workspace = source_gdb
   the_tables = arcpy.ListTables()
   found_it = False
   i = 0
   while found_it == False and i < len(the_tables):
      if get_name(the_tables[i]).upper() == "A_README":
         found_it = True
      else:
         i += 1
   if found_it == True:
      the_cursor = arcpy.da.SearchCursor(the_tables[i], ["PROTOCOL","DB_TYPE","CONSTRAINTS","NOTE"])
      the_row = the_cursor.next()
      if the_row[0].strip().upper() != "EGC GEOSPATIAL DATA EXCHANGE PROTOCOL":
         make_note("Source geodatabase's A_README table isn't attributed for EGC Geospatial Data Exchange Protocol. Check its A_README table's PROTOCOL field.", True, True)
         sys.exit()
      if the_row[1].strip().upper() == "HUB":
         source_db_type = "hub"
      elif the_row[1].strip().upper() == "SPOKE":
         source_db_type = "spoke"
      else:
         make_note("Source geodatabase's A_README table isn't properly attributed. DB_TYPE field should be 'hub' or 'spoke'.", True, True)
         sys.exit()
      del the_cursor
      del the_row
      make_note("Source geodatabase is a " + source_db_type + " geodatabase.", True, True)
   else:
      make_note("Source geodatabase doesn't have an A_README table, which is required.", True, True)
      sys.exit()

   #IF SOURCE GEODATABASE IS A SPOKE GEODATABASE, VERIFY EXISTENCE OF ITS A_XCHANGE_PARAMETERS TABLE
   #(GET ITS NAME. FIND OUT IF IT HAS ROWS.)
   params_table_name = ""
   params_table_has_rows = False
   if source_db_type == "spoke":
      make_note("Verifying source geodatabase (spoke) has an A_XCHANGE_PARAMETERS table...")
      found_it = False
      i = 0
      while found_it == False and i < len(the_tables):
         if get_name(the_tables[i]).upper() == "A_XCHANGE_PARAMETERS":
            params_table_name = the_tables[i]
            if int(get_count(the_tables[i])) > 0:
               params_table_has_rows = True
            found_it = True
         else:
            i += 1
      if found_it != True:
         make_note("Source geodatabase doesn't have an A_XCHANGE_PARAMETERS table, which is required for a spoke geodatabase (can be an empty table if optional special directives aren't used).", True, True)
         sys.exit()

   #READ AND ANALYZE TARGET-GEODATABASE'S A_README TABLE
   make_note("Reading and analyzing target-geodatabase's A_README table...")
   arcpy.env.workspace = target_gdb
   the_tables = arcpy.ListTables()
   found_it = False
   i = 0
   while found_it == False and i < len(the_tables):
      if get_name(the_tables[i]).upper() == "A_README":
         found_it = True
      else:
         i += 1
   if found_it == True:
      the_cursor = arcpy.da.SearchCursor(the_tables[i], ["PROTOCOL","DB_TYPE","CONSTRAINTS","NOTE"])
      the_row = the_cursor.next()
      if the_row[0].strip().upper() != "EGC GEOSPATIAL DATA EXCHANGE PROTOCOL":
         make_note("Target geodatabase's A_README table isn't attributed for EGC Geospatial Data Exchange Protocol. Check its A_README table's PROTOCOL field.", True, True)
         sys.exit()
      if the_row[1].strip().upper() == "HUB":
         target_db_type = "hub"
      elif the_row[1].strip().upper() == "SPOKE":
         target_db_type = "spoke"
      else:
         make_note("Target geodatabase's A_README table isn't properly attributed. DB_TYPE field should be 'hub' or 'spoke'.", True, True)
         sys.exit()
      del the_cursor
      del the_row
      make_note("Target geodatabase is a " + target_db_type + " geodatabase.", True, True)
   else:
      make_note("Target geodatabase doesn't have an A_README table, which is required.", True, True)
      sys.exit()

   #IF TARGET GEODATABASE IS A HUB GEODATABASE, VERIFY EXISTENCE OF ITS A_XCHANGE_LOG TABLE
   if target_db_type == "hub":
      make_note("Verifying target geodatabase (hub) has an A_XCHANGE_LOG table...")
      found_it = False
      i = 0
      while found_it == False and i < len(the_tables):
         if get_name(the_tables[i]).upper() == "A_XCHANGE_LOG":
            hub_logtable_name = the_tables[i]
            found_it = True
         else:
            i += 1
      if found_it != True:
         make_note("Target geodatabase doesn't have an A_XCHANGE_LOG table, which is required for a hub geodatabase.", True, True)
         sys.exit()

   #LISTS THAT CAPTURE INFO ON PRE-EXISTING DATA-OBJECTS. ESTABLISH LISTS; THEN FILL THEM.
   make_note("Collecting info on pre-existing data-objects...")
   #(SOURCE FEATURE-CLASSES)
   source_fclasses_prefixed_names = []
   source_fclasses_prefixes = []
   source_fclasses_names = []
   source_fdatasets_prefixed_names = []
   source_fdatasets_prefixes = []
   source_fdatasets_names = []

   #(SOURCE TABLES)
   source_tables_prefixed_names = []
   source_tables_prefixes = []
   source_tables_names = []

   #(SOURCE RASTERS)
   source_rasters_prefixed_names = []
   source_rasters_prefixes = []
   source_rasters_names = []

   #(TARGET FEATURE-CLASSES)
   target_fclasses_prefixed_names = []
   target_fclasses_prefixes = []
   target_fclasses_names = []
   target_fdatasets_prefixed_names = []
   target_fdatasets_prefixes = []
   target_fdatasets_names = []

   #(TARGET TABLES)
   target_tables_prefixed_names = []
   target_tables_prefixes = []
   target_tables_names = []

   #(TARGET RASTERS)
   target_rasters_prefixed_names = []
   target_rasters_prefixes = []
   target_rasters_names = []

   #(TARGET EMPTY FEATURE-DATASET NAMES (FEATURE DATASET IS THERE BUT HAS NO FEATURE CLASSES))
   target_empty_fdatasets = []

   #(SOURCE FEATURE-CLASSES)
   arcpy.env.workspace = source_gdb
   the_fdatasets = arcpy.ListDatasets("*","Feature")
   for a_fdataset in the_fdatasets:
      the_fclasses = arcpy.ListFeatureClasses("*", "All", a_fdataset)
      for a_fclass in the_fclasses:
         source_fclasses_prefixed_names.append(a_fclass)
         source_fclasses_prefixes.append(get_schema_prefix(a_fclass))
         source_fclasses_names.append(get_name(a_fclass))
         source_fdatasets_prefixed_names.append(a_fdataset)
         source_fdatasets_prefixes.append(get_schema_prefix(a_fdataset))
         source_fdatasets_names.append(get_name(a_fdataset))

   the_fclasses = arcpy.ListFeatureClasses()
   for a_fclass in the_fclasses:
      source_fclasses_prefixed_names.append(a_fclass)
      source_fclasses_prefixes.append(get_schema_prefix(a_fclass))
      source_fclasses_names.append(get_name(a_fclass))
      source_fdatasets_prefixed_names.append("")
      source_fdatasets_prefixes.append("")
      source_fdatasets_names.append("")

   #(SOURCE TABLES)
   the_tables = arcpy.ListTables()
   for a_table in the_tables:
      table_name = get_name(a_table).upper()
      #(DON'T WANT CERTAIN TABLES IN THE LISTS)
      if table_name != "A_README" and table_name != "A_XCHANGE_PARAMETERS" and table_name != "A_XCHANGE_LOG":
         source_tables_prefixed_names.append(a_table)
         source_tables_prefixes.append(get_schema_prefix(a_table))
         source_tables_names.append(table_name)

   #(SOURCE RASTERS)
   the_rasters = arcpy.ListRasters()
   for a_raster in the_rasters:
      source_rasters_prefixed_names.append(a_raster)
      source_rasters_prefixes.append(get_schema_prefix(a_raster))
      source_rasters_names.append(get_name(a_raster))

   #(TARGET FEATURE-CLASSES)
   arcpy.env.workspace = target_gdb
   the_fdatasets = arcpy.ListDatasets("*","Feature")
   for a_fdataset in the_fdatasets:
      the_fclasses = arcpy.ListFeatureClasses("*", "All", a_fdataset)
      #IF EMPTY FEATURE DATASET...
      if len(the_fclasses) == 0:
         target_empty_fdatasets.append(a_fdataset)
      #OTHERWISE...
      else:
         for a_fclass in the_fclasses:
            target_fclasses_prefixed_names.append(a_fclass)
            target_fclasses_prefixes.append(get_schema_prefix(a_fclass))
            target_fclasses_names.append(get_name(a_fclass))
            target_fdatasets_prefixed_names.append(a_fdataset)
            target_fdatasets_prefixes.append(get_schema_prefix(a_fdataset))
            target_fdatasets_names.append(get_name(a_fdataset))

   the_fclasses = arcpy.ListFeatureClasses()
   for a_fclass in the_fclasses:
      target_fclasses_prefixed_names.append(a_fclass)
      target_fclasses_prefixes.append(get_schema_prefix(a_fclass))
      target_fclasses_names.append(get_name(a_fclass))
      target_fdatasets_prefixed_names.append("")
      target_fdatasets_prefixes.append("")
      target_fdatasets_names.append("")

   #(TARGET TABLES)
   the_tables = arcpy.ListTables()
   for a_table in the_tables:
      table_name = get_name(a_table).upper()
      #(DON'T WANT CERTAIN TABLES IN THE LISTS)
      if table_name != "A_README" and table_name != "A_XCHANGE_PARAMETERS" and table_name != "A_XCHANGE_LOG":
         target_tables_prefixed_names.append(a_table)
         target_tables_prefixes.append(get_schema_prefix(a_table))
         target_tables_names.append(table_name)

   #(TARGET RASTERS)
   the_rasters = arcpy.ListRasters()
   for a_raster in the_rasters:
      target_rasters_prefixed_names.append(a_raster)
      target_rasters_prefixes.append(get_schema_prefix(a_raster))
      target_rasters_names.append(get_name(a_raster))

   #PRINT LISTS
   print "***** LISTS OF PRE-EXISTING DATA OBJECTS *****"
   print "SOURCE FEATURE-CLASSES:"
   i = 0
   while i < len(source_fclasses_prefixed_names):
      print "     " + source_fclasses_prefixed_names[i]
      print "          PREFIX: " + source_fclasses_prefixes[i]
      print "          NAME W/O PREFIX: " + source_fclasses_names[i]
      print "          CONTAINING FEATURE-DATASET: " + source_fdatasets_prefixed_names[i]
      print "          CONTAINING FEATURE-DATASET PREFIX: " + source_fdatasets_prefixes[i]
      print "          CONTAINING FEATURE-DATASET NAME W/O PREFIX: " + source_fdatasets_names[i]
      i += 1
   print "SOURCE TABLES:"
   i = 0
   while i < len(source_tables_prefixed_names):
      print "     " + source_tables_prefixed_names[i]
      print "          PREFIX: " + source_tables_prefixes[i]
      print "          NAME W/O PREFIX: " + source_tables_names[i]
      i += 1
   print "SOURCE RASTERS:"
   i = 0
   while i < len(source_rasters_prefixed_names):
      print "     " + source_rasters_prefixed_names[i]
      print "          PREFIX: " + source_rasters_prefixes[i]
      print "          NAME W/O PREFIX: " + source_rasters_names[i]
      i += 1

   print "TARGET FEATURE-CLASSES:"
   i = 0
   while i < len(target_fclasses_prefixed_names):
      print "     " + target_fclasses_prefixed_names[i]
      print "          PREFIX: " + target_fclasses_prefixes[i]
      print "          NAME W/O PREFIX: " + target_fclasses_names[i]
      print "          CONTAINING FEATURE-DATASET: " + target_fdatasets_prefixed_names[i]
      print "          CONTAINING FEATURE-DATASET PREFIX: " + target_fdatasets_prefixes[i]
      print "          CONTAINING FEATURE-DATASET NAME W/O PREFIX: " + target_fdatasets_names[i]
      i += 1
   print "TARGET TABLES:"
   i = 0
   while i < len(target_tables_prefixed_names):
      print "     " + target_tables_prefixed_names[i]
      print "          PREFIX: " + target_tables_prefixes[i]
      print "          NAME W/O PREFIX: " + target_tables_names[i]
      i += 1
   print "TARGET RASTERS:"
   i = 0
   while i < len(target_rasters_prefixed_names):
      print "     " + target_rasters_prefixed_names[i]
      print "          PREFIX: " + target_rasters_prefixes[i]
      print "          NAME W/O PREFIX: " + target_rasters_names[i]
      i += 1
   print "TARGET EMPTY FEATURE-DATASETS (CONTAIN NO FEATURE CLASSES):"
   i = 0
   while i < len(target_empty_fdatasets):
      print "     " + target_empty_fdatasets[i]
      i += 1

   #MAKE freight_cars LIST TO STORE DICTIONARIES THAT MANAGE AND TRACK DATA TRANSFERS
   freight_cars = []

   #START LISTS TO TRACK TARGET FEATURE-DATASETS THAT ARE CREATED BECAUSE THEY DON'T ALREADY EXIST (OR IF ALREADY EXISTS IN TARGET BUT IS EMPTY)
   created_fdatasets_prefixed_names = []
   created_fdatasets_names = []
   for i in target_empty_fdatasets:
      created_fdatasets_prefixed_names.append(i)
      created_fdatasets_names.append(get_name(i))

   #FOR SOURCE FEATURE DATASETS THAT DON'T EXIST IN TARGET GEODATABASE, CREATE THEM IN TARGET GEODATABASE
   i = 0
   while i < len(source_fdatasets_prefixed_names):
      if source_fdatasets_prefixed_names[i] != "":
         #IF TARGET GEODATABASE DIDN'T HAVE FEATURE CLASSES CONTAINED BY THAT FEATURE DATASET WHEN SCRIPT STARTED...
         j = get_index(target_fdatasets_names, source_fdatasets_names[i])
         #IF FEATURE DATASET HASN'T ALREADY BEEN CREATED BY THIS SCRIPT AND IT ISN'T AN EMPTY FEATURE DATASET...
         if j == -1:
            if get_index(created_fdatasets_names, source_fdatasets_names[i]) == -1:
               #CREATE THE FEATURE DATASET IN THE TARGET GEODATABASE AND CAPTURE ITS INFO
               make_note("Feature-dataset " + source_fdatasets_names[i] + " doesn't already exist in target geodatabase; creating it...", True, True)
               arcpy.env.workspace = source_gdb
               arcpy.CreateFeatureDataset_management(target_gdb, source_fdatasets_names[i], source_fclasses_prefixed_names[i])
               arcpy.env.workspace = target_gdb
               the_fdatasets = arcpy.ListDatasets("*","Feature")
               j = 0
               found_it = False
               while j < len(the_fdatasets) and found_it == False:
                  if get_name(the_fdatasets[j]).upper() == source_fdatasets_names[i].upper():
                     created_fdatasets_prefixed_names.append(the_fdatasets[j])
                     created_fdatasets_names.append(get_name(the_fdatasets[j]))
                     found_it = True
                  j += 1
               #IF FOR SOME WEIRD REASON, FEATURE DATASET'S PREFIXED NAME CAN'T BE CAPTURED, EXIT DUE TO ERROR CONDITION
               if found_it == False:
                  make_note("Script encountered error condition when trying to get full name (prefixed) of feature-dataset " + source_fdatasets_names[i] + " from target geodatabase.", True, True)
                  sys.exit()
      i += 1

   #IF SOURCE GEODATABASE IS A SPOKE GEODATABASE AND ITS A_XCHANGE_PARAMETERS TABLE HAS ROWS...
   if source_db_type == "spoke" and params_table_has_rows == True:
      make_note("Source geodatabase is a spoke geodatabase w/ directives in A_XCHANGE_PARAMETERS table. Analyzing A_XCHANGE_PARAMETERS table...", True, True)
      #WORK EACH A_XCHANGE_PARAMETERS ROW
      arcpy.env.workspace = source_gdb
      the_cursor = arcpy.da.SearchCursor(params_table_name, ["OBJECT_NAME","IS_FDATASET","DIRECTIVE","SORT_FIELD","NOTE"])
      for a_row in the_cursor:
         the_directive = a_row[2]
         if the_directive == None:
            the_directive = ""
         the_directive = the_directive.upper().strip()
         #IF DIRECTIVE APPLIES TO A FEATURE DATASET...
         if a_row[1] == 1 and the_directive != "STATIC":
            #FIND OUT IF THE FEATURE DATASET EXISTS IN SOURCE GEODATABASE
            i = get_index(source_fdatasets_prefixed_names, a_row[0])
            #IF FEATURE DATASET DOES EXIST IN SOURCE GEODATABASE...
            if i != -1:
               #FOR EACH FEATURE CLASS OF THE SOURCE FEATURE-DATASET, LOAD A FREIGHT CAR
               the_fclasses = arcpy.ListFeatureClasses("*", "All", a_row[0])
               for a_fclass in the_fclasses:
                  source_prefix = get_schema_prefix(a_fclass)
                  fds = get_name(a_row[0])
                  name = get_name(a_fclass)
                  type = "fclass"
                  if the_directive == "DETECT_CHANGES":
                     detect_changes = True
                     sort_field = a_row[3].strip()
                  else:
                     detect_changes = False
                     sort_field = None
                  i = get_index(target_fclasses_names, get_name(a_fclass))
                  if i != -1:
                     already_there = True
                     target_prefix = target_fclasses_prefixes[i]
                  else:
                     already_there = False
                     target_prefix = ""
                  freight_cars.append(create_freight_car(source_prefix, fds, name, type, detect_changes, sort_field, already_there, target_prefix))
            #OTHERWISE, MAKE NOTE THAT FEATURE DATASET DOESN'T EXIST IN SOURCE GEODATABASE
            else:
               make_note("A_XCHANGE_PARAMETERS table has a directive for a feature dataset named " + a_row[0] + ". However source geodatabase doesn't have a feature dataset by that name. Skipping it.", True, True)
         #OTHERWISE, DIRECTIVE APPLIES TO AN INDIVIDUAL FEATURE-CLASS, TABLE, OR RASTER DATASET
         else:
            #DETERMINE IF DIRECTIVE APPLIES TO A FEATURE CLASS, TABLE, RASTER DATASET, OR A DATA OBJECT THAT DOESN'T EXIST (OR DATA OBJECT TO BE SKIPPED)
            if the_directive != "STATIC":
               i = get_index(source_fclasses_prefixed_names, a_row[0])
               if i != -1:
                  applies_to = "fclass"
               else:
                  i = get_index(source_tables_prefixed_names, a_row[0])
                  if i != -1:
                     applies_to = "table"
                  else:
                     i = get_index(source_rasters_prefixed_names, a_row[0])
                     if i != -1:
                        applies_to = "raster"
                     else:
                        applies_to = "nothing"
            else:
               applies_to = "skip"
            #IF FEATURE CLASS, LOAD A FREIGHT CAR THIS WAY
            if applies_to == "fclass":
               source_prefix = source_fclasses_prefixes[i]
               if source_fdatasets_names[i] == "":
                  fds = None
               else:
                  fds = source_fdatasets_names[i]
               name = source_fclasses_names[i]
               type = "fclass"
               if the_directive == "DETECT_CHANGES":
                  detect_changes = True
                  sort_field = a_row[3].strip()
               else:
                  detect_changes = False
                  sort_field = None
               i = get_index(target_fclasses_names, name)
               if i != -1:
                  already_there = True
                  target_prefix = target_fclasses_prefixes[i]
               else:
                  already_there = False
                  target_prefix = ""
               freight_cars.append(create_freight_car(source_prefix, fds, name, type, detect_changes, sort_field, already_there, target_prefix))
            #IF TABLE, LOAD A FREIGHT CAR THIS WAY
            elif applies_to == "table":
               source_prefix = source_tables_prefixes[i]
               fds = None
               name = source_tables_names[i]
               type = "table"
               if the_directive == "DETECT_CHANGES":
                  detect_changes = True
                  sort_field = a_row[3].strip()
               else:
                  detect_changes = False
                  sort_field = None
               i = get_index(target_tables_names, name)
               if i != -1:
                  already_there = True
                  target_prefix = target_tables_prefixes[i]
               else:
                  already_there = False
                  target_prefix = ""
               freight_cars.append(create_freight_car(source_prefix, fds, name, type, detect_changes, sort_field, already_there, target_prefix))
            #IF RASTER DATASET, LOAD A FREIGHT CAR THIS WAY
            elif applies_to == "raster":
               source_prefix = source_rasters_prefixes[i]
               fds = None
               name = source_rasters_names[i]
               type = "raster"
               detect_changes = False
               sort_field = None
               i = get_index(target_rasters_names, name)
               if i != -1:
                  already_there = True
                  target_prefix = target_rasters_prefixes[i]
               else:
                  already_there = False
                  target_prefix = ""
               freight_cars.append(create_freight_car(source_prefix, fds, name, type, detect_changes, sort_field, already_there, target_prefix))
            elif applies_to == "skip":
               pass
            #OTHERWISE, DATA OBJECT DOESN'T EXIST. MAKE NOTE.
            else:
               make_note("A_XCHANGE_PARAMETERS table has a directive for a data object named " + a_row[0] + ". However source geodatabase doesn't have a data object by that name. Skipping it.", True, True)
      del the_cursor
   #OTHERWISE, NOT WORKING THROUGH A_XCHANGE_PARAMETERS TABLE
   else:
      make_note("Analyzing source data-objects...", True, True)
      #FEATURE CLASSES
      i = 0
      while i < len(source_fclasses_prefixed_names):
         source_prefix = source_fclasses_prefixes[i]
         if source_fdatasets_names[i] == "":
            fds = None
         else:
            fds = source_fdatasets_names[i]
         name = source_fclasses_names[i]
         type = "fclass"
         detect_changes = False
         sort_field = None
         j = get_index(target_fclasses_names, name)
         if j != -1:
            already_there = True
            target_prefix = target_fclasses_prefixes[j]
         else:
            already_there = False
            target_prefix = ""
         freight_cars.append(create_freight_car(source_prefix, fds, name, type, detect_changes, sort_field, already_there, target_prefix))
         i += 1
      #TABLES
      i = 0
      while i < len(source_tables_prefixed_names):
         source_prefix = source_tables_prefixes[i]
         fds = None
         name = source_tables_names[i]
         type = "table"
         detect_changes = False
         sort_field = None
         j = get_index(target_tables_names, name)
         if j != -1:
            already_there = True
            target_prefix = target_tables_prefixes[j]
         else:
            already_there = False
            target_prefix = ""
         freight_cars.append(create_freight_car(source_prefix, fds, name, type, detect_changes, sort_field, already_there, target_prefix))
         i += 1
      #RASTER DATASETS
      i = 0
      while i < len(source_rasters_prefixed_names):
         source_prefix = source_rasters_prefixes[i]
         fds = None
         name = source_rasters_names[i]
         type = "raster"
         detect_changes = False
         sort_field = None
         j = get_index(target_rasters_names, name)
         if j != -1:
            already_there = True
            target_prefix = target_rasters_prefixes[j]
         else:
            already_there = False
            target_prefix = ""
         freight_cars.append(create_freight_car(source_prefix, fds, name, type, detect_changes, sort_field, already_there, target_prefix))
         i += 1

   #PRINT FREIGHT CAR INFO
   print "***** HERE IS HOW THE TRAIN IS LINED UP *****"
   for i in freight_cars:
      print "FREIGHT CAR:"
      print "     source_prefix: " + i["source_prefix"]
      print "     fds: " + str(i["fds"])
      print "     name: " + i["name"]
      print "     type: " + i["type"]
      print "     detect_changes: " + str(i["detect_changes"])
      print "     sort_field: " + str(i["sort_field"])
      print "     already_there: " + str(i["already_there"])
      print "     target_prefix: " + i["target_prefix"]

   #SEND FREIGHT DOWN THE TRACK
   for i in freight_cars:
      #IF A FEATURE CLASS...
      if i["type"] == "fclass":
         #IF FEATURE CLASS DOESN'T ALREADY EXIST IN TARGET GEODATABASE...
         if i["already_there"] == False:
            #IF FEATURE CLASS IS IN A FEATURE DATASET...
            if i["fds"] != None:
               #GET SOURCE FEATURE-DATASET NAME
               source_fds_name = source_fdatasets_prefixed_names[get_index(source_fdatasets_names, i["fds"])]
               #GET TARGET FEATURE-DATASET NAME
               j = get_index(target_fdatasets_names, i["fds"])
               if j != -1:
                  target_fds_name = target_fdatasets_prefixed_names[j]
               else:
                  target_fds_name = created_fdatasets_prefixed_names[get_index(created_fdatasets_names, i["fds"])]
               #COPY THE FEATURE CLASS FROM ONE FEATURE-DATASET TO THE OTHER
               arcpy.Copy_management(source_gdb + "\\" + source_fds_name + "\\" + i["source_prefix"] + i["name"], target_gdb + "\\" + target_fds_name + "\\" + i["name"])
               #GET ROW COUNTS
               source_row_count = get_count(source_gdb + "\\" + source_fds_name + "\\" + i["source_prefix"] + i["name"])
               target_row_count = get_count(target_gdb + "\\" + target_fds_name + "\\" + get_schema_prefix(target_fds_name) + i["name"])
               #IF TARGET GEODATABASE IS A HUB GEODATABASE, RECORD ACTION IN ITS A_XCHANGE_LOG TABLE
               if target_db_type == "hub":
                  cur_log = arcpy.da.InsertCursor(target_gdb + "\\" + hub_logtable_name, ["DATE","NOTE"])
                  the_string = tell_the_time()
                  todays_date = the_string[4:6] + "/" + the_string[6:8] + "/" + the_string[0:4]
                  cur_log.insertRow([todays_date,"Copied in new feature-class " + target_fds_name + "\\" + get_schema_prefix(target_fds_name) + i["name"]])
                  del cur_log
               make_note("Copied " + i["fds"] + "\\" + i["name"] + " to target geodatabase. Source Row Count: " + source_row_count + ". Target Row Count (after load): " + target_row_count + ".", True, True)
            #OTHERWISE, IT'S A STAND-ALONE FEATURE-CLASS
            else:
               #COPY FEATURE CLASS FROM SOURCE GEODATABASE TO TARGET GEODATABASE
               arcpy.Copy_management(source_gdb + "\\" + i["source_prefix"] + i["name"], target_gdb + "\\" + i["name"])
               #GET SOURCE ROW COUNT
               source_row_count = get_count(source_gdb + "\\" + i["source_prefix"] + i["name"])
               #NEED TO LOOP THROUGH FEATURECLASSES TO GET SCHEMA PREFIX OF NEW FEATURE CLASS IN TARGET, IN ORDER TO COUNT ROWS IN TARGET
               arcpy.env.workspace = target_gdb
               the_fclasses = arcpy.ListFeatureClasses()
               j = 0
               found_it = False
               while j < len(the_fclasses) and found_it == False:
                  if get_name(the_fclasses[j]).upper() == i["name"].upper():
                     the_prefix = get_schema_prefix(the_fclasses[j])
                     found_it = True
                  else:
                     j += 1
               target_row_count = get_count(target_gdb + "\\" + the_prefix + i["name"])
               #IF TARGET GEODATABASE IS A HUB GEODATABASE, RECORD ACTION IN ITS A_XCHANGE_LOG TABLE
               if target_db_type == "hub":
                  cur_log = arcpy.da.InsertCursor(target_gdb + "\\" + hub_logtable_name, ["DATE","NOTE"])
                  the_string = tell_the_time()
                  todays_date = the_string[4:6] + "/" + the_string[6:8] + "/" + the_string[0:4]
                  cur_log.insertRow([todays_date,"Copied in new feature-class " + the_prefix + i["name"]])
                  del cur_log
               make_note("Copied " + i["name"] + " to target geodatabase. Source Row Count: " + source_row_count + ". Target Row Count (after load): " + target_row_count + ".", True, True)
         #OTHERWISE, FEATURE CLASS ALREADY EXISTS IN TARGET GEODATABASE
         else:
            #IF FEATURE CLASS IS IN A FEATURE DATASET...
            if i["fds"] != None:
               #GET SOURCE FEATURE-DATASET NAME
               source_fds_name = source_fdatasets_prefixed_names[get_index(source_fdatasets_names, i["fds"])]
               #GET TARGET FEATURE-DATASET NAME
               target_fds_name = target_fdatasets_prefixed_names[get_index(target_fdatasets_names, i["fds"])]
               go_ahead = False
               #IF ONLY UPDATING THE FEATURE CLASS IF CHANGES EXIST, DETECT CHANGES
               if i["detect_changes"] == True:
                  x = compare_objects(source_gdb + "\\" + source_fds_name + "\\" + i["source_prefix"] + i["name"], target_gdb + "\\" + target_fds_name + "\\" + get_schema_prefix(target_fds_name) + i["name"], i["sort_field"])
                  if x == "different":
                     make_note("Change detected for " + source_gdb + "\\" + source_fds_name + "\\" + i["source_prefix"] + i["name"] + ".", True, True)
                     go_ahead = True
                  elif x == "same":
                     make_note("Change NOT detected for " + source_gdb + "\\" + source_fds_name + "\\" + i["source_prefix"] + i["name"] + ".", True, True)
                  else:
                     make_note("Error... Couldn't conduct change-detection for " + source_gdb + "\\" + source_fds_name + "\\" + i["source_prefix"] + i["name"] + ". Check fields. Skipping it.", True, True)
               else:
                  go_ahead = True
               if go_ahead == True:
                  load_rows(source_gdb + "\\" + source_fds_name + "\\" + i["source_prefix"] + i["name"], target_gdb + "\\" + target_fds_name + "\\" + get_schema_prefix(target_fds_name) + i["name"])
                  #GET ROW COUNTS
                  source_row_count = get_count(source_gdb + "\\" + source_fds_name + "\\" + i["source_prefix"] + i["name"])
                  target_row_count = get_count(target_gdb + "\\" + target_fds_name + "\\" + get_schema_prefix(target_fds_name) + i["name"])
                  #IF TARGET GEODATABASE IS A HUB GEODATABASE, RECORD ACTION IN ITS A_XCHANGE_LOG TABLE
                  if target_db_type == "hub":
                     cur_log = arcpy.da.InsertCursor(target_gdb + "\\" + hub_logtable_name, ["DATE","NOTE"])
                     the_string = tell_the_time()
                     todays_date = the_string[4:6] + "/" + the_string[6:8] + "/" + the_string[0:4]
                     cur_log.insertRow([todays_date,"Refreshed rows of feature class " + target_fds_name + "\\" + get_schema_prefix(target_fds_name) + i["name"]])
                     del cur_log
                  make_note("Loaded rows of " + i["fds"] + "\\" + i["name"] + " to target geodatabase. Source Row Count: " + source_row_count + ". Target Row Count (after load): " + target_row_count + ".", True, True)
            #OTHERWISE, IT'S A STAND-ALONE FEATURE-CLASS
            else:
               j = get_index(target_fclasses_names, i["name"])
               go_ahead = False
               #IF ONLY UPDATING THE FEATURE CLASS IF CHANGES EXIST, DETECT CHANGES
               if i["detect_changes"] == True:
                  x = compare_objects(source_gdb + "\\" + i["source_prefix"] + i["name"], target_gdb + "\\" + target_fclasses_prefixed_names[j], i["sort_field"])
                  if x == "different":
                     make_note("Change detected for " + source_gdb + "\\" + i["source_prefix"] + i["name"] + ".", True, True)
                     go_ahead = True
                  elif x == "same":
                     make_note("Change NOT detected for " + source_gdb + "\\" + i["source_prefix"] + i["name"] + ".", True, True)
                  else:
                     make_note("Error... Couldn't conduct change-detection for " + source_gdb + "\\" + i["source_prefix"] + i["name"] + ". Check fields. Skipping it.", True, True)
               else:
                  go_ahead = True
               if go_ahead == True:
                  load_rows(source_gdb + "\\" + i["source_prefix"] + i["name"], target_gdb + "\\" + target_fclasses_prefixed_names[j])
                  #GET ROW COUNTS
                  source_row_count = get_count(source_gdb + "\\" + i["source_prefix"] + i["name"])
                  target_row_count = get_count(target_gdb + "\\" + target_fclasses_prefixed_names[j])
                  #IF TARGET GEODATABASE IS A HUB GEODATABASE, RECORD ACTION IN ITS A_XCHANGE_LOG TABLE
                  if target_db_type == "hub":
                     cur_log = arcpy.da.InsertCursor(target_gdb + "\\" + hub_logtable_name, ["DATE","NOTE"])
                     the_string = tell_the_time()
                     todays_date = the_string[4:6] + "/" + the_string[6:8] + "/" + the_string[0:4]
                     cur_log.insertRow([todays_date,"Refreshed rows of feature class " + target_fclasses_prefixed_names[j]])
                     del cur_log
                  make_note("Loaded rows of " + i["name"] + " to target geodatabase. Source Row Count: " + source_row_count + ". Target Row Count (after load): " + target_row_count + ".", True, True)
      #IF A TABLE...
      elif i["type"] == "table":
         #IF TABLE DOESN'T ALREADY EXIST IN TARGET GEODATABASE...
         if i["already_there"] == False:
            #COPY TABLE FROM SOURCE GEODATABASE TO TARGET GEODATABASE
            arcpy.Copy_management(source_gdb + "\\" + i["source_prefix"] + i["name"], target_gdb + "\\" + i["name"])
            #GET SOURCE ROW COUNT
            source_row_count = get_count(source_gdb + "\\" + i["source_prefix"] + i["name"])
            #NEED TO LOOP THROUGH TABLES TO GET SCHEMA PREFIX OF NEW TABLE IN TARGET, IN ORDER TO COUNT ROWS IN TARGET
            arcpy.env.workspace = target_gdb
            the_tables = arcpy.ListTables()
            j = 0
            found_it = False
            while j < len(the_tables) and found_it == False:
               if get_name(the_tables[j]).upper() == i["name"].upper():
                  the_prefix = get_schema_prefix(the_tables[j])
                  found_it = True
               else:
                  j += 1
            target_row_count = get_count(target_gdb + "\\" + the_prefix + i["name"])
            #IF TARGET GEODATABASE IS A HUB GEODATABASE, RECORD ACTION IN ITS A_XCHANGE_LOG TABLE
            if target_db_type == "hub":
               cur_log = arcpy.da.InsertCursor(target_gdb + "\\" + hub_logtable_name, ["DATE","NOTE"])
               the_string = tell_the_time()
               todays_date = the_string[4:6] + "/" + the_string[6:8] + "/" + the_string[0:4]
               cur_log.insertRow([todays_date,"Copied in new table " + the_prefix + i["name"]])
               del cur_log
            make_note("Copied table " + i["name"] + " to target geodatabase. Source Row Count: " + source_row_count + ". Target Row Count(after load): " + target_row_count + ".", True, True)
         #OTHERWISE, TABLE ALREADY EXISTS IN TARGET GEODATABASE
         else:
            j = get_index(target_tables_names, i["name"])
            go_ahead = False
            #IF ONLY UPDATING THE TABLE IF CHANGES EXIST, DETECT CHANGES
            if i["detect_changes"] == True:
               x = compare_objects(source_gdb + "\\" + i["source_prefix"] + i["name"], target_gdb + "\\" + target_tables_prefixed_names[j], i["sort_field"], True)
               if x == "different":
                  make_note("Change detected for " + source_gdb + "\\" + i["source_prefix"] + i["name"] + ".", True, True)
                  go_ahead = True
               elif x == "same":
                  make_note("Change NOT detected for " + source_gdb + "\\" + i["source_prefix"] + i["name"] + ".", True, True)
               else:
                  make_note("Error... Couldn't conduct change-detection for " + source_gdb + "\\" + i["source_prefix"] + i["name"] + ". Check fields. Skipping it.", True, True)
            else:
               go_ahead = True
            if go_ahead == True:
               load_rows(source_gdb + "\\" + i["source_prefix"] + i["name"], target_gdb + "\\" + target_tables_prefixed_names[j])
               #GET ROW COUNTS
               source_row_count = get_count(source_gdb + "\\" + i["source_prefix"] + i["name"])
               target_row_count = get_count(target_gdb + "\\" + target_tables_prefixed_names[j])
               #IF TARGET GEODATABASE IS A HUB GEODATABASE, RECORD ACTION IN ITS A_XCHANGE_LOG TABLE
               if target_db_type == "hub":
                  cur_log = arcpy.da.InsertCursor(target_gdb + "\\" + hub_logtable_name, ["DATE","NOTE"])
                  the_string = tell_the_time()
                  todays_date = the_string[4:6] + "/" + the_string[6:8] + "/" + the_string[0:4]
                  cur_log.insertRow([todays_date,"Refreshed rows of table " + target_tables_prefixed_names[j]])
                  del cur_log
               make_note("Loaded rows of " + i["name"] + " to target geodatabase. Source Row Count: " + source_row_count + ". Target Row Count (after load): " + target_row_count + ".", True, True)
      #IF A RASTER DATASET...
      elif i["type"] == "raster":
         #IF RASTER DATASET DOESN'T ALREADY EXIST IN TARGET GEODATABASE...
         if i["already_there"] == False:
            #COPY RASTER DATASET FROM SOURCE GEODATABASE TO TARGET GEODATABASE
            arcpy.Copy_management(source_gdb + "\\" + i["source_prefix"] + i["name"], target_gdb + "\\" + i["name"])
            #IF TARGET GEODATABASE IS A HUB GEODATABASE, RECORD ACTION IN ITS A_XCHANGE_LOG TABLE
            if target_db_type == "hub":
               cur_log = arcpy.da.InsertCursor(target_gdb + "\\" + hub_logtable_name, ["DATE","NOTE"])
               the_string = tell_the_time()
               todays_date = the_string[4:6] + "/" + the_string[6:8] + "/" + the_string[0:4]
               cur_log.insertRow([todays_date,"Copied in new raster-dataset " + i["name"]])
               del cur_log
            make_note("Copied raster-dataset " + i["name"] + " to target geodatabase.", True, True)
         #OTHERWISE, RASTER DATASET ALREADY EXISTS IN TARGET GEODATABASE
         else:
            j = get_index(target_rasters_names, i["name"])
            try:
               #DELETE THE RASTER DATASET IN TARGET GEODATABASE
               arcpy.Delete_management(target_gdb + "\\" + target_rasters_prefixed_names[j])
               #COPY RASTER DATASET FROM SOURCE GEODATABASE TO TARGET GEODATABASE
               arcpy.Copy_management(source_gdb + "\\" + i["source_prefix"] + i["name"], target_gdb + "\\" + i["name"])
               #IF TARGET GEODATABASE IS A HUB GEODATABASE, RECORD ACTION IN ITS A_XCHANGE_LOG TABLE
               if target_db_type == "hub":
                  cur_log = arcpy.da.InsertCursor(target_gdb + "\\" + hub_logtable_name, ["DATE","NOTE"])
                  the_string = tell_the_time()
                  todays_date = the_string[4:6] + "/" + the_string[6:8] + "/" + the_string[0:4]
                  cur_log.insertRow([todays_date,"Refreshed raster-dataset " + target_rasters_prefixed_names[j]])
                  del cur_log
               make_note("Re-loaded raster-dataset " + i["name"] + " to target geodatabase.", True, True)
            except:
               make_note("Couldn't re-load raster-dataset " + i["name"] + ". A lock might be blocking the operation. An exclusive lock is required (consult w/ a DBA for more info).", True, True)
      else:
         pass

   #LOG SCRIPT COMPLETION
   make_note("Script completed.", True, True)

   #EMAIL REPORT (IF APPLICABLE)
   if email_switch == True:
      print "EMAILING REPORT..."
      send_email("VT DataRail Tools - SendFreight - REPORT", email_content)

except:
   make_note("Script encountered error condition and terminated.", True, True)
   make_note("arcpy Messages:  " + arcpy.GetMessages())
   if email_switch == True:
      send_email("VT DataRail Tools - SendFreight - ERROR", email_content)


