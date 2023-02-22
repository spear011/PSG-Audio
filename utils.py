
import pandas as pd
import xml.etree.ElementTree as ET
import os
import numpy as np

class get_info:

    def get_ns():
        ns = {'study' : 'http://www.respironics.com/PatientStudy.xsd'}
        return ns

    def get_root(file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        return root

    def get_rml_files(folder_path):
        rml_files = [x for x in os.listdir(folder_path) if x.endswith('.rml')]
        return rml_files

    def get_acq_number(root, ns):
        acq = root.findall('study:Acquisition', ns)
        acq_number = [x.find('study:AcqNumber', ns).text for x in acq]
        return acq_number

    def get_segment_duration(root, ns):
        segment = root.find('study:Acquisition', ns).find('study:Sessions', ns).find('study:Session', ns).find('study:Segments', ns)
        duration = [x.find('study:Duration', ns).text for x in segment]
        return duration

    def get_stages(root, ns):
        stages = root.find('study:ScoringData', ns).find('study:StagingData', ns).find('study:UserStaging', ns).find('study:NeuroAdultAASMStaging', ns).findall('study:Stage', ns)
        all_sleep = [x.attrib for x in stages]

        # make End point of each sleep events
        for i in range(len(all_sleep)):
            if i < len(all_sleep) - 1 :
                all_sleep[i]['End'] = int(all_sleep[i + 1]['Start'])
            else:
                all_sleep[i]['End'] = int(all_sleep[i]['Start'])

        # wake = [x for x in all_sleep if x.get('Type') == 'Wake']
        # rem = [x for x in all_sleep if x.get('Type') == 'REM']

        # # 맨 마지막 wake는 레코딩 종료 시점 이므로 삭제
        # del wake[-1]
        del all_sleep[-1]
        return all_sleep

    def get_breathing_events(root, ns):
        events = root.find('study:ScoringData', ns).find('study:Events', ns).findall('study:Event', ns)
        respiratory = [x.attrib for x in events if x.attrib.get('Family') == 'Respiratory']

        # make End point of respiratory event
        for i in range(len(respiratory)):
            respiratory[i]['End'] = float(respiratory[i]['Start']) + float(respiratory[i]['Duration'])
        return respiratory

class rml_df_converter():

    def __init__(self, file_path):
        self.file_path = file_path
        self.root = get_info.get_root(self.file_path)
        self.ns = get_info.get_ns()
        

    def get_df(self):
        acq_number = get_info.get_acq_number(self.root, self.ns)
        sleep = get_info.get_stages(self.root, self.ns)

        # make dataframe
        df = pd.DataFrame.from_dict(sleep).astype({'Start' : 'float' , 'End' : 'float'}).sort_values(by='Start').reset_index(drop=True)
        df['stage_duration'] = df['End'] - df['Start']
        df['stage_duration'] = df['stage_duration'].astype('float')
        df.rename(columns = {'Start':'stage_start_time','End':'stage_end_time', 'Type' : 'stage_type'},inplace=True)
        # make patient_id
        df['patient_id'] = np.zeros(len(df))
        patient_id = {0 : acq_number}
        df['patient_id'] = df['patient_id'].replace(patient_id)
        return df
    
    def get_breathing_df(self):
        respiratory = get_info.get_breathing_events(self.root, self.ns)
        df = pd.DataFrame.from_dict(respiratory).astype({'Start' : 'float' , 'End' : 'float'}).sort_values(by='Start').reset_index(drop=True)
        df.rename(columns = {'Start':'event_start_time','End':'event_end_time', 'Duration' : 'event_duration', 'Type' : 'respiratory_type'},inplace=True)
        return df

    # matching breathing events time include in sleep stage time
    # If there is more than one event in a stage, duplicate sleep stage dataframe's row
    # If there is no matching event in a stage, add value 'NaN' in event_start_time, event_end_time, event_duration
    def get_matched_df(self):
        df = self.get_df()
        breathing_df = self.get_breathing_df()
        matched_df = pd.DataFrame(columns = ['patient_id', 'stage_start_time', 'stage_end_time', 'stage_duration', 'stage_type', 'event_start_time', 'event_end_time', 'event_duration', 'respiratory_type'])
        for i in range(len(df)):
            stage_start_time = df['stage_start_time'][i]
            stage_end_time = df['stage_end_time'][i]
            stage_duration = df['stage_duration'][i]
            stage_type = df['stage_type'][i]
            patient_id = df['patient_id'][i]
            event_start_time = []
            event_end_time = []
            event_duration = []
            respiratory_type = []
            for j in range(len(breathing_df)):
                if stage_start_time <= breathing_df['event_start_time'][j] and breathing_df['event_end_time'][j] <= stage_end_time:
                    event_start_time.append(breathing_df['event_start_time'][j])
                    event_end_time.append(breathing_df['event_end_time'][j])
                    event_duration.append(breathing_df['event_duration'][j])
                    respiratory_type.append(breathing_df['respiratory_type'][j])
            if len(event_start_time) == 0:
                matched_df = pd.concat([matched_df, pd.DataFrame({'patient_id' : patient_id, 'stage_start_time' : stage_start_time, 'stage_end_time' : stage_end_time, 'stage_duration' : stage_duration, 'stage_type' : stage_type, 'event_start_time' : 'NaN', 'event_end_time' : 'NaN', 'event_duration' : 'NaN', 'respiratory_type' : 'NaN'}, index=[0])], ignore_index=True)
            else:
                for k in range(len(event_start_time)):
                    matched_df = pd.concat([matched_df, pd.DataFrame({'patient_id' : patient_id, 'stage_start_time' : stage_start_time, 'stage_end_time' : stage_end_time, 'stage_duration' : stage_duration, 'stage_type' : stage_type, 'event_start_time' : event_start_time[k], 'event_end_time' : event_end_time[k], 'event_duration' : event_duration[k], 'respiratory_type' : respiratory_type[k]}, index=[0])], ignore_index=True)
        return matched_df

class rml_to_concat_df():

    def __init__(self, folder_path):
        self.folder_path = folder_path
        
    
    # make concat df of all rml files in path
    def get_concat_df(self):
        rml_files = get_info.get_rml_files(self.folder_path)
        concat_df = pd.DataFrame(columns = ['patient_id', 'stage_start_time', 'stage_end_time', 'stage_duration', 'stage_type', 'event_start_time', 'event_end_time', 'event_duration', 'respiratory_type'])
        for i in range(len(rml_files)):
            rml_file_path = self.folder_path + rml_files[i]
            print('Converting...{}'.format(rml_files[i]))
            rml_df = rml_df_converter(rml_file_path).get_matched_df()
            concat_df = pd.concat([concat_df, rml_df], ignore_index=True)
        return concat_df