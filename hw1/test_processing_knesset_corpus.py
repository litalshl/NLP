import unittest
from processing_knesset_corpus import Protocol, Sentence

class TestProtocolMethods(unittest.TestCase):

    # Verify that file names are parsed correctly to extract knesset number and protocol type
    def test_parse_file_name(self):
        p = Protocol("123vpt_25.docx")
        p.parse_file_name()
        self.assertEqual(p.knesset_number, 25)
        self.assertEqual(p.protocol_type, "committee")
        
        p2 = Protocol("456mpt_10.docx")
        p2.parse_file_name()
        self.assertEqual(p2.knesset_number, 10)
        self.assertEqual(p2.protocol_type, "plenary")

        p3 = Protocol("bad_filename.docx")
        with self.assertRaises(Exception):
            p3.parse_file_name()

    # Check that we can extract the protocol number from Hebrew text correctly
    def test_extract_protocol_number(self):
        p = Protocol("dummy.docx")
        text = "מספר ישיבה 15\nהמשך טקסט"
        number = p.extract_protocol_number(text)
        self.assertEqual(number, 15)

        text2 = "אין מספר ישיבה בפרוטוקול זה"
        number2 = p.extract_protocol_number(text2)
        self.assertEqual(number2, 1)

    # Extract the chairman's name from the protocol header text
    def test_extract_chairman(self):
        p = Protocol("dummy.docx")
        text = ('יו"ר הישיבה: ח"כ משה לוי\n'
                'המשך טקסט')
        chairman = p.extract_chairman(text)
        self.assertEqual(chairman, "משה לוי")

        text2 = "אין יו\"ר במקטע זה"
        chairman2 = p.extract_chairman(text2)
        self.assertEqual(chairman2, "")

    # Verify that speakers and their corresponding text are correctly extracted from the document
    def test_extract_speakers_and_text(self):
        p = Protocol("dummy.docx")
        from docx import Document
        document = Document()
        # Add paragraphs as needed to simulate docx structure for test
        
        speakers_text_map = p.extract_speakers_and_text(document)
        # Check if speakers and their text are correctly extracted
        self.assertIsInstance(speakers_text_map, dict)
        # Add more detailed asserts based on your sample docx

    # Make sure sentances are split properly at periods, exclamation marks, and question marks
    def test_split_into_sentences(self):
        p = Protocol("dummy.docx")
        text = "זהו משפט ראשון. פה המשפט השני! האם זה משפט שלישי?"
        sentences = p.split_into_sentences(text)
        self.assertIsNotNone(sentences)
        self.assertIn("זהו משפט ראשון.", sentences)
        self.assertIn("פה המשפט השני!", sentences)
        self.assertIn("האם זה משפט שלישי?", sentences)

    # Verify that invalid sentences get filtered out correctly (dashes, numbers, non-Hebrew text)
    def test_clean_sentences(self):
        p = Protocol("dummy.docx")
        inputs = [
            "זה משפט תקין.",
            "- - -",
            "123456",
            "Hello world",
            "משפט עם אנגלית English"
        ]
        cleaned = p.clean_sentences(inputs)
        self.assertIsNotNone(cleaned)
        self.assertIn("זה משפט תקין.", cleaned)
        self.assertNotIn("- - -", cleaned)
        self.assertNotIn("123456", cleaned)
        self.assertNotIn("Hello world", cleaned)
        self.assertNotIn("משפט עם אנגלית English", cleaned)

    # Check that tokenization breaks sentences into individual words and punctuation marks
    def test_tokenize(self):
        p = Protocol("dummy.docx")
        sentence = "שלום, איך אתה? אני בסדר."
        tokens = p.tokenize(sentence)
        expected_tokens = ["שלום", ",", "איך", "אתה", "?", "אני", "בסדר", "."]
        self.assertEqual(tokens, expected_tokens)

    # Test the full document processing pipeline end-to-end with a real sample file
    def test_full_process_document(self):
        p = Protocol("testmpt_20.docx")
        test_file = "tests/small_sample.docx"
        p.process_single_document(test_file)
        self.assertTrue(len(p.sentences) > 0)
        for sentence in p.sentences:
            self.assertGreaterEqual(len(sentence.sentence_text.split()), 4)

if __name__ == '__main__':
    unittest.main()
