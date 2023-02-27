class get_mic_signals():

    def __init__(self, data_path):
        self.data_path = data_path

    def get_edf_numbers(self):
        edf_numbers = [file for file in os.listdir(self.data_path)]
        edf_numbers.sort()
        return edf_numbers

    def get_edf_folder_path(self, edf_number):
        edf_folder_path = os.path.join(self.data_path, edf_number)
        return edf_folder_path

    # make a function to extract edf file pathes from edf folders
    def get_edf_file_pathes(folder_path):
        edf_file_pathes = glob.glob(folder_path + '/*.edf')
        return edf_file_pathes
    
    def extract_one_mic_signal(file_name):
        signals, signal_headers, header = highlevel.read_edf(file_name)
        mic_signal = signals[-2]
        return mic_signal

    # extract mic_signal from all edf files
    def extract_all_mic_signals(file_lists):
        mic_signals = np.concatenate([extract_one_mic_signal(file_name) for file_name in file_lists])
        return mic_signals