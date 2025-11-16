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
        self.protocol_type = None   # "Committee" or "Plenary"
        self.protocol_number = 1    # Default Integer
        self.protocol_chairman = ""
        self.sentences = []         # List of Sentence objects

    # Extract the Knesset number and protocol_type from file name
    def parse_file_name(self):
        try:
            base = os.path.basename(self.file_name)
            # Accept filenames like '123vpt_25.docx' or 'something_mpt_10.docx'
            match = re.search(r'(vpt|mpt)_(\d+)', base)
            if match:
                protocol_code = match.group(1)
                knesset_str = match.group(2)
                self.knesset_number = int(knesset_str)
                if protocol_code == "vpt":
                    self.protocol_type = "committee"
                elif protocol_code == "mpt":
                    self.protocol_type = "plenary"
                else:
                    raise ValueError("Unknown protocol code")
            else:
                raise ValueError("Filename pattern not matched")
        except Exception as e:
            raise Exception(f"Failed parsing filename '{self.file_name}': {e}")

    # Extract protocol number from beginning of text or default 1
    def extract_protocol_number(self, text):
        try:
            match = re.search(r'מספר\s+(?:ישיבה|פרוטוקול)?\s*(\d+)', text)
            if match:
                return int(match.group(1))
            else:
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
                # skip negative expressions like 'אין יו"ר' which mean 'no chairman'
                if re.search(r'\bאין\b', line):
                    continue
                if 'יו"ר' in line or 'יו״ר' in line or 'יו"ר' in line:
                    # Split on colon if present, otherwise capture following text
                    parts = re.split(r'[:]', line)
                    if len(parts) > 1:
                        possible_name = parts[1].strip()
                    else:
                        m = re.search(r'יו["״]?ר\s+(.+)', line)
                        possible_name = m.group(1).strip() if m else ''

                    # Remove common honorifics (e.g., ח"כ, ח״כ, עו"ד, ד"ר) and punctuation
                    possible_name = re.sub(r'^(?:ח["״]?כ|עו["״]?ד|ד["״]?ר|מר|גב)\s+', '', possible_name)
                    possible_name = possible_name.strip(' ,()')
                    name_parts = possible_name.split()
                    if len(name_parts) >= 2:
                        return ' '.join(name_parts[:2])
                    elif len(name_parts) == 1:
                        return name_parts[0]
        except Exception:
            pass
        return ""

    # Extract speakers and their spoken text, and clean speaker names
    def extract_speakers_and_text(self, document):
        speakers_text = {}
        current_speaker = None
        current_text = []
        for par in document.paragraphs:
            text = par.text.strip()
            if not text:
                continue
            if text.endswith(":") and len(text) < 50:
                if current_speaker and current_text:
                    combined_text = " ".join(current_text).strip()
                    clean_name = self._clean_speaker_name(current_speaker)
                    if clean_name not in speakers_text:
                        speakers_text[clean_name] = combined_text
                    else:
                        speakers_text[clean_name] += " " + combined_text
                    current_text = []
                current_speaker = text[:-1]
            else:
                if current_speaker:
                    current_text.append(text)
        if current_speaker and current_text:
            combined_text = " ".join(current_text).strip()
            clean_name = self._clean_speaker_name(current_speaker)
            if clean_name not in speakers_text:
                speakers_text[clean_name] = combined_text
            else:
                speakers_text[clean_name] += " " + combined_text
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
            self.parse_file_name()
            document = Document(file_path)
            full_text = "\n".join([p.text for p in document.paragraphs])
            self.protocol_number = self.extract_protocol_number(full_text)
            self.protocol_chairman = self.extract_chairman(full_text)
            speakers_text_map = self.extract_speakers_and_text(document)
            for speaker, full_text in speakers_text_map.items():
                sentences = self.split_into_sentences(full_text)
                valid_sentences = self.clean_sentences(sentences)
                for sentence in valid_sentences:
                    tokens = self.tokenize(sentence)
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
                        self.sentences.append(sentence_obj)
        except Exception as e:
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
    for filename in os.listdir(input_dir):
        if filename.endswith(".docx"):
            protocol = Protocol(filename)
            file_path = os.path.join(input_dir, filename)
            protocol.process_document(file_path)
            all_sentences.extend(protocol.sentences)
    # Save all sentences from all protocols 
    with open(output_file, "w", encoding="utf-8") as f:
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
