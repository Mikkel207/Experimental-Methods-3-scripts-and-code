import psychopy
psychopy.useVersion('2023.1.3')

# we import the relevant libaries and modules
from psychopy import visual, core, event, gui
import random
import csv
import ast
import os
import glob
import datetime
import tempfile
from PIL import Image, ImageFilter
import numpy as np
import sys

try:
    import serial
except ImportError:
    serial = None

# EEG trigger codes
EEG_TRIGGER_START = 30
EEG_TRIGGER_CODES = [(101, 201), (102, 202), (103, 203), (104, 204), (105, 205), (106, 206)]
EEG_TRIGGER_RESPONSE = 40
EEG_TRIGGER_CLEAR = 0
DEFAULT_EEG_SERIAL_BAUD = 115200

# we set up the dialog box to get participant info
class ParticipantInfo:
    def __init__(self):
        dlg = gui.Dlg(title="Please enter a four-digit Participant ID")
        dlg.addField('Participant ID:')
        ok_data = dlg.show()
        if not dlg.OK or not ok_data[0]:
            core.quit()
        self.participant_id = ok_data[0]


class MainExperiment:
    def __init__(self, num_trials_pr_diff = 2, num_blocks = 1, num_warmup_trials = 2, num_test_trials = 2): # For rigtig eksperiment: 6 trials pr. diff., 8 blocks, 2 warmup trials, 10 test trials
        self.participant_info = ParticipantInfo()
        self.window = visual.Window(fullscr=True, color='black')
        self.instructions = visual.TextStim(self.window, text='',color='white', wrapWidth=1.5)
        self.results = []
        self.test_results = []
        self.num_trials_pr_diff = num_trials_pr_diff
        self.num_blocks = num_blocks
        self.num_warmup_trials = num_warmup_trials
        self.num_test_trials = num_test_trials

        self.serial_port = os.environ.get('EEG_SERIAL_PORT', None)

        self.init_eeg_port()

        # Sæt hele stien til stimuli ind her:
        self.stimuli_fine = self.load_stimuli('/Users/bertramgraverblohm/Desktop/Kurser/EM3/Projekt/ordlister/similarity/fine_trials_no_overlap.tsv', 'fine')
        self.stimuli_coarse = self.load_stimuli('/Users/bertramgraverblohm/Desktop/Kurser/EM3/Projekt/ordlister/similarity/coarse_trials_no_overlap.tsv', 'coarse')
        self.stimuli_medium = self.load_stimuli('/Users/bertramgraverblohm/Desktop/Kurser/EM3/Projekt/ordlister/similarity/medium_trials_no_overlap.tsv', 'medium')
        self.warmup_trials = self.load_stimuli('/Users/bertramgraverblohm/Desktop/Kurser/EM3/Projekt/ordlister/similarity/warmup_trials.tsv', 'warmup')

        random.shuffle(self.stimuli_fine)
        random.shuffle(self.stimuli_medium)
        random.shuffle(self.stimuli_coarse)
        random.shuffle(self.warmup_trials)

    def load_stimuli(self, stimuli_path, difficulty): #we load the stimuli from a tsv file and parse the core_group column to get a list of words
        stimuli_list = []
        delimiter = '\t' if stimuli_path.lower().endswith('.tsv') else ','
        with open(stimuli_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                if not row:
                    continue
                # parse listen fra string → liste
                words = ast.literal_eval(row['core_group'])

                stimuli_list.append({
                    'words': words,
                    'outlier': row['outlier'],
                    'outlier_position': int(row['outlier_position']),
                    'correct_response': int(row['outlier_position']) + 1,
                    'difficulty': difficulty
                })
        return stimuli_list

    def init_eeg_port(self): # Kør forsøg med EEG-hvis den findes, både parallelt eller serielt. Ellers, kørt forsøg uden EEG-triggers
        self.port = None
        self.port_found = False
        self.port_type = 'none'
        self.serial_port = None

        if serial is None:
            print("pyserial ikke installeret: EEG-port ikke fundet (kører i test-mode)")
            return

        try:
            self.serial_port = serial.Serial('/dev/tty.usbserial-DN2Q03LO', 115200)
            self.port_type = 'serial'
            self.port_found = True
            print("EEG-port initialiseret på serial port /dev/tty.usbserial-DN2Q03LO")

        except Exception as e:
            self.serial_port = None
            self.port_type = 'none'
            self.port_found = False
            print(f"Kunne ikke åbne seriel port: {e}")

        # Prøver i stedet at definere e
    def send_trigger(self, code, duration=0.01):
        if self.port_type != 'none':
            self.serial_port.write(code.to_bytes(1, 'big'))
            core.wait(duration)
            print('trigger sent {}'.format(code))
        else:
            return

    def run_trial(self, trial_stimulus, block_num = None, trial_num = None, save = True, feedback = False):
        # sørg for, at outlier altid havner som ord 4-6 (1-indekseret)
        outlier_word = trial_stimulus['outlier']
        remaining_words = trial_stimulus['words'].copy()
        if outlier_word in remaining_words:
            remaining_words.remove(outlier_word)
        outlier_index = random.choice([3, 4, 5])
        wordlist = remaining_words
        wordlist.insert(outlier_index, outlier_word)
        correct_response = outlier_index + 1

        # Positioner på y-aksen
        y_positions = [0.75, 0.45, 0.15, -0.15, -0.45, -0.75]

        word_stims = []
        number_stims = []

        for i, word in enumerate(wordlist):
            # ord
            word_stim = visual.TextStim(
                self.window,
                text=word,
                pos=(0, y_positions[i]),
                color='white'
            )
            word_stims.append(word_stim)

            # tal (grønne)
            number_stim = visual.TextStim(
                self.window,
                text=str(i+1),
                pos=(0.5, y_positions[i]),
                color='green'
            )
            number_stims.append(number_stim)

        event.clearEvents(eventType='keyboard')

        # tegn ord én ad gangen, men behold tidligere tegnede ord på skærmen
        drawn_stims = []
        for i in range(len(word_stims)):
            core.wait(1.25)
            drawn_stims.extend([number_stims[i], word_stims[i]])
            for stim in drawn_stims:
                stim.draw()

            trigger_code = EEG_TRIGGER_CODES[i][1] if i == outlier_index else EEG_TRIGGER_CODES[i][0] # Tag outlier-kode hvis det er outlier-ordet og neutral-kode ellers
            if self.port_type == "none":
                print(f"Trigger-koden skulle være: {trigger_code}") # Printer trigger-koden i pilottests.
            self.window.callOnFlip(self.send_trigger, trigger_code)
            self.window.flip()

        # response collection
        timer = core.Clock()
        keys = event.waitKeys(keyList=['4','5','6','escape'], timeStamped=timer)
        if not keys:
            response = -1
            rt = None
            correct = False
        else:
            key, rt = keys[0]
            if key == 'escape':
                self.window.close()
                core.quit()
            response = int(key)
            self.send_trigger(EEG_TRIGGER_RESPONSE)
            correct = response == correct_response

        if feedback:
            # feedback: marker outlier grønt og forkert valgt svar rødt
            word_stims[outlier_index].color = 'green'
            if response - 1 != outlier_index:
                word_stims[response - 1].color = 'red'
            for i in range(len(word_stims)):
                number_stims[i].draw()
                word_stims[i].draw()
            self.window.flip()
            core.wait(1.5)

        if save == True:
            self.results.append({
                'participant_id': self.participant_info.participant_id,
                'block': block_num,
                'trial': trial_num,
                'difficulty': trial_stimulus['difficulty'],
                'stimulus': " | ".join(wordlist),
                'outlier': trial_stimulus['outlier'],
                'outlier_position': outlier_index + 1, # +1 p.g.a 0-indeksering.
                'response': response,
                'correct_response': correct_response,
                'correct': int(correct), # dvs 1 for correct, 0 for incorrect
                'rt': rt
            })

    def get_trials(self,stimuli_list,n): #vi popper stimuli ud af listen, så vi ikke gentager stimulus i forsøget
        if len(stimuli_list) < n:
            raise ValueError("Not enough stimuli!")
        return [stimuli_list.pop() for _ in range(n)]

    def create_block(self):
        fine_trials = self.get_trials(self.stimuli_fine, self.num_trials_pr_diff)
        medium_trials = self.get_trials(self.stimuli_medium, self.num_trials_pr_diff)
        coarse_trials = self.get_trials(self.stimuli_coarse, self.num_trials_pr_diff)

        main_trials = fine_trials + medium_trials + coarse_trials
        random.shuffle(main_trials)

        warmup_trials = self.get_trials(self.warmup_trials, self.num_warmup_trials)

        return warmup_trials + main_trials
    
    def create_test_block(self):
        trials = self.get_trials(self.warmup_trials, self.num_test_trials)
        random.shuffle(trials)
        return trials
     
    def show_fixation(self, duration=0.5):
        fixation = visual.TextStim(self.window, text='+', color='white')
        fixation.draw()
        self.window.flip()
        core.wait(duration)
    
    def run_test_block(self): #skal måkse lige gøres bedre. 10 trials kun?
        test_block = self.create_test_block()
        for trial_stimulus in test_block:
            self.show_fixation()
            self.run_trial(trial_stimulus, save = False, feedback = True) #test trials med feedback

    def run_block(self, block_num):
        block = self.create_block()
        for trial_stimulus in block[:2]:
            self.show_fixation()
            self.run_trial(trial_stimulus, save = False, feedback = False) #warmup trials uden feedback
        for i, trial_stimulus in enumerate(block[2:]):
            self.show_fixation()
            self.run_trial(trial_stimulus, block_num=block_num, trial_num= i+1, save = True) #main trials, så vi gemmer data fra dem
        
    # we set up a function that shows instructions in the experiment
    def show_instructions(self, text):
        self.instructions.text = text
        self.instructions.draw()
        self.window.flip()
        event.waitKeys(keyList=['space'])

    def save_data(self):
        filename = f'participant_{self.participant_info.participant_id}.csv'

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'participant_id', 'block', 'trial', 'difficulty', 'stimulus', 'outlier', 'outlier_position', 'response', 
                'correct_response', 'correct', 'rt'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)
        print(f"Data saved to {filename}")
            

    def run_experiment(self):
        #startskærm
        self.show_instructions("Velkommen og tak for at deltage i vores forsøg! \n\n" \
        "I dette forsøg vil du blive præsenteret for en række af seks ord. Fem af dem er i samme kategori. Et er ikke. Din opgave er at finde ordet udenfor kategori. \n\n" \
        "De seks ord vil i rækkefølge vises på skærmen, hvor de tre første der vises ALTID er i samme kategori. Af de sidste tre ord er EN af dem udenfor kategori \n\n" \
        "Du svarer ved at trykke 4, 5 eller 6 alt efter hvilket ord du tror er udenfor kategori. Tryk på space for at gå videre.")
        
        #test blok
        self.show_instructions("Vi starter med en øvelsesrunde, så du kan lære forsøget at kende. \n\n" \
        "Tryk 4, 5 eller 6 når alle ord er præsenteret, for at svare. \n\n" \
        "Nogle ordlister er nemmere end andre. Det er helt ok at være usikker på dit svar :) \n\n" \
        "Det rigtige svar vil blive vist som grønt efter du har svaret. \n\n" \
        "Tryk på space for at starte.") 
        self.run_test_block()

        #før rigtig blokke
        self.show_instructions("Nu begynder det rigtige forsøg. Det er ens med øvelsesrunderne, udover at du IKKE får feedback på hvilket svar der er rigtigt. \n\n" \
        "Nogle ordlister er nemmere end andre, og det er ok at være i tvivl om dit svar. Giv så godt et svar som du kan. \n\n"
        "Tryk på space for at starte.")

        #rigtige blokke
        for block_number in range(self.num_blocks):
            self.run_block(block_number)

            #pause mellem blokke
            if block_number < self.num_blocks - 1:
                self.show_instructions("Pause mellem blokke. Tryk på space for at fortsætte.")
            
        #afslutningsskærm
        self.show_instructions("Tak for at deltage! Tryk på space for at afslutte.")
        self.save_data()
        self.window.close()
        core.quit()

if __name__ == "__main__":
    experiment = MainExperiment()
    experiment.run_experiment()