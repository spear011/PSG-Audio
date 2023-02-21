

ns = {'study' : 'http://www.respironics.com/PatientStudy.xsd'}

class get_info:

    def __init__(self, root, ns):
        self.root = root
        self.ns = ns

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