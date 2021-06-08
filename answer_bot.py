# from QA_tools import QuestionPreprocessor,Retriever
from random import choice

class QuestionAnsweringBot():
    def __init__(self,preprocessor,retriever):
        self.preprocessor = preprocessor
        self.retriever = retriever
    

    def get_relevant_sentences(self,paragraphs,query):
        relevant_paragraphs = self.retriever.find_relevant_paragraphs(query)

        sentences = []
        for para_idx,_ in relevant_paragraphs:
            paragraph = paragraphs[para_idx]
            sentences.extend(self.retriever.get_sentences(paragraph))
        relevant_sentences = self.retriever.find_relevant_sentences(sentences,query)
        return relevant_sentences
    
    def answer(self,question):
        query = self.preprocessor.reformulate_question(question)
        question_type = self.preprocessor.classify_question(question)
        answer_type = self.preprocessor.classify_answer(question)
        relevant_senteces = self.get_relevant_sentences(self.retriever.paragraphs,query)
        # print(relevant_senteces)
        NER_pairs = self.retriever.find_NER(relevant_senteces)
        NER_pairs = [NER_pair for NER_pair in NER_pairs if NER_pair[0].lower() not in question.lower()]

        if question_type == "binary":
            return "Yes"
        elif question_type == "agnostic":
            return "NO IDEA"
        else:
            if "agnostic" in answer_type:
                return "NO IDEA"
            elif "GUESS" in answer_type:
                return choice(NER_pairs)[0]
            elif "DIRECT" in answer_type:
                return relevant_senteces[0][0]
            else:
                for NER_pair in NER_pairs:
                    if NER_pair[1] in answer_type:
                        return NER_pair[0]
        return "NO IDEA"
