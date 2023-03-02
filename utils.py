
import pandas as pd
import xml.etree.ElementTree as ET
import os
import numpy as np
import glob
from pyedflib import highlevel
import soundfile as sf

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
    

class get_mic_signals():

    def __init__(self, folder_path):
        self.folder_path = folder_path
    
    # make file path list in folder
    def get_file_path_list(self):
        file_list = os.listdir(self.folder_path)
        file_path_list = []
        for i in range(len(file_list)):
            file_path_list.append(self.folder_path + '/' + file_list[i])
        file_path_list.sort()
        return file_path_list
    
    # extract mic_signal from one edf file
    def extract_one_mic_signal(self, file_path):
        signals = highlevel.read_edf(file_path)[0][-2]
        return signals

    # extract and concate mic_signal from all edf files
    def extract_all_mic_signal(self):
        file_path_list = self.get_file_path_list()
        all_signals = np.array([])
        for i in range(len(file_path_list)):
            signals = self.extract_one_mic_signal(file_path_list[i])
            all_signals = np.concatenate([all_signals, signals])
        return all_signals


class make_wav_files():

    def __init__(self, data_path, df, sr):
        self.data_path = data_path
        self.df = df
        self.sr = sr

    def get_patient_id_list(self):
        lists = os.listdir(self.data_path)
        lists = [int(x) for x in lists]
        lists.sort()
        return lists

    def get_current_df(self, patient_id):
        df = self.df
        current_df = df[df['patient_id'] == patient_id]
        current_df = current_df.drop_duplicates(['stage_start_time', 'stage_end_time', 'stage_duration', 'stage_type'], keep='first').sort_values(by=['patient_id','stage_start_time']).reset_index(drop=True)
        return current_df
    
    def get_current_mic_signal(self, patient_id):
        data_path = self.data_path
        mic_signal = get_mic_signals(data_path + str(patient_id).zfill(8)).extract_all_mic_signal()
        return mic_signal

    # segment signal by stage
    def segment_one_signal_and_save(self, patient_id):
        print('Getting wav files of patient {}...'.format(patient_id))
        mic_signal = self.get_current_mic_signal(patient_id)
        print('Getting mic signal completed. Getting current df...')
        current_df = self.get_current_df(patient_id)
        print('Getting current df completed.')
        sr = self.sr
        wav_folder = self.data_path + 'wav/' + str(patient_id).zfill(8) + '/'

        if not os.path.exists(wav_folder):
            os.makedirs(wav_folder)

        signal_list = []
        wav_id_list = []
        for i in range(len(current_df)):
            start = int(current_df['stage_start_time'][i] * sr)
            end = int(current_df['stage_end_time'][i] * sr)
            signal_list.append(mic_signal[start:end])
            sleep_hour = int(current_df['stage_start_time'][i] // 3600) + 1
            sf.write(wav_folder + str(patient_id).zfill(8) + '_' + str(sleep_hour).zfill(2) + '_' + str(i).zfill(2) + '.wav', signal_list[i], sr)
            wav_id_list.append(str(patient_id) + '_' + str(sleep_hour).zfill(2) + '_' + str(i).zfill(2))
            print('Patient {} stage {} saved.'.format(patient_id, i))

        current_wav_df = pd.concat([current_df, pd.DataFrame(wav_id_list, columns=['wav_id'])], axis=1)
        print('Patient {} completed.'.format(patient_id))
        return current_wav_df

    # segment all signals and concat all df

    def segment_all_signals_and_save(self):
        patient_id_list = self.get_patient_id_list()
        wav_df = pd.DataFrame(columns = ['patient_id', 'stage_start_time', 'stage_end_time', 'stage_duration', 'stage_type', 'wav_id'])
        for i in range(len(patient_id_list)):
            current_wav_df = self.segment_one_signal_and_save(patient_id_list[i])
            print('remaining {} patients.'.format(len(patient_id_list) - i - 1))
            wav_df = pd.concat([wav_df, current_wav_df], ignore_index=True)
        print('All patients completed.')
        return wav_df
