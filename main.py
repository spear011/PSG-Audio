from utils import *
import glob
import xml.etree.ElementTree as ET


# Path: projects\rem\main.py

def main():
    # get xml file list
    xml_file_list = glob.glob(r'C:\Users\user\Desktop\*.xml')

    # create main df
    main_df = pd.DataFrame()
    main_df_breathing = pd.DataFrame()

    for xml_file in xml_file_list:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # get dataframe
        df = rml_df_converter(root, ns).get_df()
        df_breathing = rml_df_converter(root, ns).get_breathing_df()

        # append dataframe
        main_df = main_df.append(df)
        main_df_breathing = main_df_breathing.append(df_breathing)