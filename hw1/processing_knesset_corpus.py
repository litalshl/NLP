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
        
        pass

    # Extract protocol number from beginning of text or default 1
    def extract_protocol_number(self, text):
        
        pass

    # Find chairman's name in text
    def extract_chairman(self, text):
        pass

    # Extract speakers and their spoken text, and clean speaker names
    def extract_speakers_and_text(self, document):
        pass

    # Split speaker text into sentences 
    def split_into_sentences(self, speaker_text):
        pass

    # Filter invalid sentences and keep only well-formed sentences
    def clean_sentences(self, sentences):
        pass

    # Tokenize sentences according to the defined rules 
    def tokenize(self, sentence):
        pass

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
        with open(output_path, "w", encoding="utf-8") as out_file:
            for sentence in self.sentences:
                json_line = json.dumps(sentence.to_dict(), ensure_ascii=False)
                out_file.write(json_line + "\n")

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
