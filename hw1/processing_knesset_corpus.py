import os
import re
import json
from docx import Document

class Sentence:
    def __init__(self, protocol_name, knesset_number, protocol_type,
                 protocol_number, protocol_chairman, speaker_name, sentence_text):
        self.protocol_name = protocol_name
        self.knesset_number = knesset_number
        self.protocol_type = protocol_type
        self.protocol_number = protocol_number
        self.protocol_chairman = protocol_chairman
        self.speaker_name = speaker_name
        self.sentence_text = sentence_text

    def to_dict(self):
        return {
            "protocol_name": self.protocol_name,
            "knesset_number": self.knesset_number,
            "protocol_type": self.protocol_type,
            "protocol_number": self.protocol_number,
            "protocol_chairman": self.protocol_chairman,
            "speaker_name": self.speaker_name,
            "sentence_text": self.sentence_text,
        }

class Protocol:
    def __init__(self, file_name):
        self.file_name = file_name
        self.knesset_number = None  # Integer
        self.protocol_type = None   # "committee" or "plenary"
        self.protocol_number = 1    # Default Integer
        self.protocol_chairman = ""
        self.sentences = []         # List of Sentence objects

    # Extract the Knesset number and protocol_type from file name
    def parse_file_name(self):
        try:
            base = os.path.basename(self.file_name)  

            # Match pattern: start with number, underscore, "ptv" or "ptm", underscore, then number
            match = re.match(r'(\d+)_pt([vm])_(\d+)', base)
            if match:
                self.knesset_number = int(match.group(1))  
                protocol_code = match.group(2)            
                if protocol_code == "v":
                    self.protocol_type = "committee"
                elif protocol_code == "m":
                    self.protocol_type = "plenary"
                else:
                    raise ValueError("Unknown protocol code")
            else:
                raise ValueError("Filename does not match expected pattern")
        except Exception as e:
            raise Exception(f"Error parsing filename '{self.file_name}': {e}")


    # Extract protocol number from beginning of text or default 1
    def extract_protocol_number(self, text):
        try:
            # Try to find the protocol number using key words 'מספר ישיבה' or 'מספר פרוטוקול'
            match = re.search(r'מספר\s+(?:ישיבה|פרוטוקול)?\s*(\d+)', text)
            if match:
                return int(match.group(1))
            else:
                # Try to find any number in the first line of the text
                first_line = text.strip().split('\n')[0]
                number_match = re.search(r'\d+', first_line)
                if number_match:
                    return int(number_match.group(0))
        except:
            pass
        return 1

    # Find chairman's name in text
    def extract_chairman(self, text):
        try:
            for line in text.split('\n'):
                # Skip lines that say אין יו"ר  
                if 'אין' in line:
                    continue
                
                # Look for lines that mention יו"ר 
                if 'יו"ר' in line:
                    # If there's a colon, take the part after it
                    if ':' in line:
                        name = line.split(':')[1].strip()
                    else:
                        # Otherwise, take everything after "יו"ר"
                        name = line.replace('יו"ר', '').strip()
                    
                    # Remove common titles (ח"כ, עו"ד, etc.) 
                    name = name.replace('ח"כ ', '').replace('עו"ד ', '').replace('ד"ר ', '')
                    
                    # Remove extra spaces and punctuation
                    name = name.strip(' ,.()')
                    
                    # If we got a name, return the first two words of it
                    if name:
                        words = name.split()
                        if len(words) >= 2:
                            return words[0] + ' ' + words[1]
                        else:
                            return words[0]
        except Exception:
            pass
        
        return ""

    # Extract speakers and their spoken text from the document
    # Returns a dictionary mapping speaker names to their complete spoken text
    def extract_speakers_and_text(self, document):
        speakers_text = {}  # Dictionary to store speaker name -> spoken text
        current_speaker = None  
        current_text = []  
        
        # Loop through all paragraphs in the document
        for par in document.paragraphs:
            text = par.text.strip()
            
            # Skip empty paragraphs
            if not text:
                continue
            
            # A speaker label ends with ":" and is short (assume less than 50 characters)
            if text.endswith(":") and len(text) < 50:
                # If we were already collecting text for a speaker, save what we collected
                if current_speaker and current_text:
                    combined_text = " ".join(current_text).strip()
                    clean_name = self._clean_speaker_name(current_speaker)
                    # Add the speaker's text to the dictionary
                    if clean_name not in speakers_text:
                        speakers_text[clean_name] = combined_text
                    else:
                        # If speaker already exists, append to their text
                        speakers_text[clean_name] += " " + combined_text
                    current_text = []
                
                # Start tracking a new speaker (remove the ":" from the end)
                current_speaker = text[:-1]
            else:
                # This paragraph is spoken text from the current speaker
                if current_speaker:
                    current_text.append(text)
        
        return speakers_text

    # Clean speaker's name
    def _clean_speaker_name(self, raw_name):
        # Remove everything after a comma or opening parenthesis
        if ',' in raw_name:
            name = raw_name.split(',')[0]
        elif '(' in raw_name:
            name = raw_name.split('(')[0]
        else:
            name = raw_name
        
        # Remove extra whitespace at the beginning and end
        name = name.strip()
        return name
    
    # Split speaker text into sentences based on punctuation
    def split_into_sentences(self, speaker_text):

        # Split on whitespace that comes after sentence-ending punctuation (., !, ?)
        sentence_endings = re.compile(r'[.!?]\s+')

        # Split text at those boundaries to produce candidate sentences
        sentences = sentence_endings.split(speaker_text)

        # Trim leading and trailing whitespace from each sentence
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    # Filter invalid sentences and keep only well-formed sentences
    def clean_sentences(self, sentences):
        valid_sentences = []
        for sent in sentences:
            # Skip very short fragments (too short to be a valid sentence)
            if len(sent) < 3:
                continue

            # Require at least two Hebrew characters to ensure this is Hebrew text
            hebrew_chars = re.findall(r'[\u0590-\u05FF]', sent)
            if len(hebrew_chars) < 2:
                continue

            # Skip sentences that contain Latin letters (likely non-Hebrew or noise)
            if re.search(r'[a-zA-Z]', sent):
                continue

            # Skip lines that are just dashes or whitespace (not meaningful content)
            if re.fullmatch(r'[-\s]+', sent):
                continue

            # If passed all filters, keep the sentence
            valid_sentences.append(sent)
        return valid_sentences

    # Tokenize sentences by removing punctuation and splitting words 
    def tokenize(self, sentence):
        tokens = []
        parts = sentence.split()
        for part in parts:
            # Find contiguous non-word characters at the start and end of the token part.
            # We separate them from the "core" word so punctuation becomes its own token.
            leading_match = re.match(r'^\W+', part)
            trailing_match = re.search(r'\W+$', part)

            # Number of leading punctuation characters, and index where trailing punctuation starts
            leading_len = len(leading_match.group(0)) if leading_match else 0
            trailing_start = trailing_match.start() if trailing_match else len(part)

            # If there is leading punctuation, add it as its own token
            if leading_len > 0:
                tokens.append(part[:leading_len])

            # Extract the core word between leading and trailing punctuation
            core_word = part[leading_len:trailing_start]
            if core_word:
                tokens.append(core_word)

            # If there is trailing punctuation, add it as its own token
            if trailing_start < len(part):
                tokens.append(part[trailing_start:])
        return tokens

    # Process a single document 
    def process_single_document(self, file_path):
        try:
            # Parse file name to set knesset_number and protocol_type first
            self.parse_file_name()

            # Load the document from the given path
            document = Document(file_path)

            # Join all paragraphs' text into one big string
            full_text = "\n".join([p.text for p in document.paragraphs])

            # Extract protocol number from the full text
            self.protocol_number = self.extract_protocol_number(full_text)

            # Extract chairman's name from the full text
            self.protocol_chairman = self.extract_chairman(full_text)

            # Extract speakers and their text from document paragraphs
            speakers_text_map = self.extract_speakers_and_text(document)

            # For each speaker and their full text
            for speaker, full_text in speakers_text_map.items():
                # Split the full text into sentences
                sentences = self.split_into_sentences(full_text)

                # Clean the sentences to keep only valid ones
                valid_sentences = self.clean_sentences(sentences)

                # For each valid sentence
                for sentence in valid_sentences:
                    # Tokenize sentence into words/tokens
                    tokens = self.tokenize(sentence)

                    # Only if sentence has 4 or more tokens, create a Sentence object
                    if len(tokens) >= 4:
                        sentence_obj = Sentence(
                            protocol_name=self.file_name,
                            knesset_number=self.knesset_number,
                            protocol_type=self.protocol_type,
                            protocol_number=self.protocol_number,
                            protocol_chairman=self.protocol_chairman,
                            speaker_name=speaker,
                            sentence_text=" ".join(tokens)
                        )
                        # Save the sentence object to the list
                        self.sentences.append(sentence_obj)

        except Exception as e:
            # In case of any error, print it but continue execution
            print(f"Error processing document {file_path}: {e}")


    # Save processed sentences to a JSONL file
    def save_to_jsonl(self, output_path):
        with open(output_path, "w", encoding="utf-8") as output_file:
            for sentence in self.sentences:
                json_line = json.dumps(sentence.to_dict(), ensure_ascii=False)
                output_file.write(json_line + "\n")

# Process all documents in input_dir and save all results combined to output_file
def main(input_dir, output_file):
    all_sentences = []
    # Loop over all files in the input directory
    for filename in os.listdir(input_dir):
        # Process only .docx files
        if filename.endswith(".docx"):
            # Create a Protocol instance for this file
            protocol = Protocol(filename)
            # Full path to the file
            file_path = os.path.join(input_dir, filename)

            # Process the document to extract sentences
            protocol.process_document(file_path)

            # Add all extracted sentences to the main list
            all_sentences.extend(protocol.sentences)

    # Open output file for writing JSON lines
    with open(output_file, "w", encoding="utf-8") as f:
        # Write each sentence as one JSON line
        for sentence in all_sentences:
            f.write(json.dumps(sentence.to_dict(), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python processing_knesset_corpus.py <input_folder> <output_jsonl_file>")
        sys.exit(1)
    input_folder = sys.argv[1]
    output_file = sys.argv[2]
    main(input_folder, output_file)
