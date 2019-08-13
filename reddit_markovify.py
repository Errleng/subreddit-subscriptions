import html

import markovify


class SubredditSimulatorText(markovify.Text):
    def test_sentence_input(self, sentence):
        return True

    def _prepare_text(self, text):
        text = html.unescape(text)
        text = text.strip()
        if not text.endswith((".", "?", "!")):
            text += "."

        return text

    def sentence_split(self, text):
        # split everything up by newlines, prepare them, and join back together
        lines = text.splitlines()
        text = " ".join([self._prepare_text(line)
                         for line in lines if line.strip()])

        return markovify.split_into_sentences(text)
