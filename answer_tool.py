from collections import Counter
import spacy
from benepar.spacy_plugin import BeneparComponent
import numpy as np
import re
from collections import defaultdict

nlp = spacy.load('en_core_web_md')
nlp.add_pipe(BeneparComponent('benepar_en2'))
import neuralcoref
neuralcoref.add_to_pipe(nlp)

class QuestionPreprocessor():
    def __init__(self,stem_or_lemma='none',use_coref=False):
        self.stem_or_lemma = stem_or_lemma
        self.use_coref = use_coref

        if self.stem_or_lemma == 'lemma':
            self.lemmatizer = lambda token:token.lemma_
        else:
            self.lemmatizer = lambda token:token.lower_

    def classify_question(self,question):
        '''
        Constituency label: SBARQ, then the question is a wh-question.
        Constituency label: SQ, then the question is a binary-question.
        return question type: wh or binary or agnostic

        input: question: question(str)
        output: wh -> wh question
                binary -> binary question
                agnostic -> can not classify 
        '''
        question = list(nlp(question).sents)[0]
        type_label = question._.labels
        if type_label[0] == "SBARQ":
            return "wh"
        elif type_label[0] == "SQ":
            return "binary"
        else:
            return "agnostic"
    
    def resolve_coref(self,question):
        '''
        To solve the problem of coref

        input: question(str)
        output: question with no coref (str)
        '''
        question = nlp(question)
        return question._.coref_resolved
    
    def classify_answer(self,question):
        '''
        To decide the possible answer type in the form of NER. 
        This function will only be called in the case of wh-question

        input: question(str)
        output: question type(tuple) <-- [GPE,LOC,DATE,TIME,PERSON,QUANTITY,CARDINAL,MONEY,GUESS,DIRECT,ORG,PERCENT,agnostic]
        '''
        wh_tags = ['WP','WDT','WP$','WRB']
        question = list(nlp(question).sents)[0]
        token_tags = []
        for token in question:
            token_tags.append((token.lower_,token.tag_))

        question_tag = None
        for pair in token_tags:
            if pair[1] in wh_tags:
                question_tag = pair[0]
                break

        if question_tag == 'where':
            return 'GPE','LOC','FAC'
        elif question_tag == 'when':
            return 'DATE','TIME'
        elif question_tag in ['who','whose','whom']:
            return 'PERSON',

        if question_tag == 'how':
            for idx,pair in enumerate(token_tags):
                if pair[0] == 'how':
                    if idx < len(token_tags)-2:
                        next_token = token_tags[idx+1][0]
                        next_next_token = token_tags[idx+2][0]
                    else:
                        next_token = token_tags[idx+1][0]
                        next_next_token = ''

                    if next_token in ['deep','wide','far','high','fast','big','hot','tall','long','large','small','quick','thick']:
                        return 'QUANTITY',
                    elif next_token == 'old':
                        return 'DATE',
                    elif next_token in ['frequent','often','frequently']:
                        return 'CARDINAL','DATE'
                    elif next_token in ['many','much']:
                        if next_next_token in ['weeks','days','months','years']:
                            return 'DATE',
                        elif next_next_token in ['seconds','minutes','hours']:
                            return 'TIME',
                        elif next_next_token == 'times':
                            return 'CARDINAL','DATE'
                        elif next_next_token in ['does','did','do']:
                            return 'MONEY',
                        else:
                            return 'CARDINAL','QUANTITY'
                    else:
                        return 'GUESS',
            return 'agnostic',
        elif question_tag == 'what':
            for idx,pair in enumerate(token_tags):
                if pair[0] == 'what':
                    if idx < len(token_tags)-2:
                        next_token = token_tags[idx+1][0]
                        next_next_token = token_tags[idx+2][0]
                    else:
                        next_token = token_tags[idx+1][0]
                        next_next_token = ''
                    if next_token in ['was','is','were','are']:
                        return 'DIRECT',
                    elif next_token in ['year','date']:
                        return 'DATE',
                    elif next_token in ['entity','company','agency','institute','industry','organization','organisation']:
                        return 'ORG',
                    elif next_token in ['country','city','state','place','location']:
                        return 'GPE','LOC'
                    elif next_token in ['individual','individuals','person']:
                        return 'PERSON',
                    elif next_token == 'percentage':
                        return 'PERCENT',
                    elif next_token == 'amount':
                        return 'QUANTITY','MONEY','PERCENT','CARDINAL'
                    else:
                        return 'DIRECT',
            return 'GUESS',
        else:
            return 'DIRECT',
        return 'agnostic',

    # def get_synonyms(self,word):
    #     '''
    #     find the synonyms of input

    #     input: word(str)
    #     output: list of synonyms 
    #     '''
    #     synonyms = []
    #     for syn in wordnet.synsets(word):
    #         for lemma in syn.lemma_names():
    #             synonyms.append(" ".join(lemma.split('_')))
    #     return list(set(synonyms))
    
    def reformulate_question(self,question):
        '''
        Remove the stop words and stem or lemma or lower words
        We may use coref resolution or synonyms

        input: question (str)
        output: list of words
        '''
        if self.use_coref:
            question = self.resolve_coref(question)
        
        question = list(nlp(question).sents)[0]
        query = []
        for token in question:
            if token.is_stop:
                continue
            else:
                query.append(self.lemmatizer(token))
                # if self.use_syn:
                #     query.extend(self.get_synonyms(token.text))
                # else:
                #     if self.stem_or_lemma == 'stem':
                #         query.append(self.stemmer(token.text))
                #     else:
                #         query.append(self.stemmer(token))
        
        vector = Counter()
        for token in query:
            vector[token] += 1
        return vector

class Retriever():
    def __init__(self,stem_or_lemma='none',use_coref=False):
        self.stem_or_lemma = stem_or_lemma
        self.use_coref = use_coref
        self.paragraphs = []
        self.paragraph_info = {}
        self.idf = {}

        if self.stem_or_lemma == 'lemma':
            self.lemmatizer = lambda token:token.lemma_
        else:
            self.lemmatizer = lambda token:token.lower_

    def fit(self,paragraphs):
        self.paragraphs = paragraphs
        self.paragraph_info,self.idf = self.compute_idf(paragraphs)
    
    def resolve_coref(self,text):
        text = nlp(text)
        return text._.coref_resolved

    def get_sentences(self,paragraph):
        paragraph = nlp(paragraph)
        return [sent for sent in paragraph.sents]
    
    def get_tokens(self,sentence):
        return [self.lemmatizer(token).lower() for token in sentence if not token.is_stop]
    
    def get_ngrams(self,tokens,n):
        return [" ".join([tokens[index+i] for i in range(n)]) for index in range(len(tokens)-n+1)]

    def compute_tf(self,paragraph):
        term_freq = Counter()

        if self.use_coref:
            paragraph = self.resolve_coref(paragraph)
            sentences = self.get_sentences(paragraph)
        else:
            sentences = self.get_sentences(paragraph)

        token_num = 0
        for sent in sentences:
            for token in sent:
                if token.is_stop:
                    continue
                if not re.match(r"[a-zA-Z0-9\-\_\\/\'+]",token.text):
                    continue
                token_num += 1
                term_freq[self.lemmatizer(token)] += 1
                
        for token in term_freq.keys():
            term_freq[token] = term_freq[token]/token_num

        return term_freq,token_num
    
    def compute_idf(self,paragraphs):
        paragraph_info = {}
        for idx,paragraph in enumerate(paragraphs):
            term_freq,token_num = self.compute_tf(paragraph)
            paragraph_info[idx] = {}
            paragraph_info[idx]['tf'] = term_freq
            paragraph_info[idx]['total'] = token_num

        token_in_paragraph_freq = Counter()
        for idx in range(len(paragraphs)):
            for token in paragraph_info[idx]['tf'].keys():
                token_in_paragraph_freq[token] += 1
        
        idf = defaultdict(lambda: np.log(len(paragraphs)))
        for token in token_in_paragraph_freq.keys():
            idf[token] = np.log(len(paragraphs)/(token_in_paragraph_freq[token]+1))

        return paragraph_info,idf

    def find_relevant_paragraphs(self,query):
        scores = []
        for idx in range(len(self.paragraph_info)):
            score = self.compute_paragraph_sim(self.paragraph_info[idx],query)
            scores.append((idx,score))

        return sorted(scores,key=lambda pair:(pair[1],pair[0]), reverse=True)[:3]

    def compute_paragraph_sim(self,unit_paragraph_info,query,idf=None):
        if idf == None:
            idf = self.idf

        query_dist = 0
        paragraph_dist = 0
        denominator = 0

        for token in query.keys():
            if token in idf.keys():
                query_dist += np.power(query[token]*idf[token]/unit_paragraph_info['total'],2)
        query_dist = np.power(query_dist,0.5)

        for token in unit_paragraph_info['tf'].keys():
            paragraph_dist += np.power(unit_paragraph_info['tf'][token]*idf[token],2)
        paragraph_dist = np.power(paragraph_dist,0.5)

        for token in query.keys():
            if token in unit_paragraph_info['tf'].keys():
                query_tf = query[token]/unit_paragraph_info['total']
                paragraph_tf = unit_paragraph_info['tf'][token]
                denominator += query_tf*paragraph_tf*idf[token]*idf[token]

        sim = denominator / (query_dist+paragraph_dist)
        return sim
    
    def find_relevant_sentences(self,sentences,query):
        sentences = [sent.text for sent in sentences]
        sent_info, sent_idf = self.compute_idf(sentences)
        scores = []
        for idx in range(len(sent_info)):
            score = self.compute_paragraph_sim(sent_info[idx],query,sent_idf)
            scores.append((sentences[idx],score))

        return sorted(scores,key=lambda pair:(pair[1],pair[0]), reverse=True)[:10]

        # relevant_sentences = []
        # for sent in sentences:
        #     score = 0
        #     if len(self.get_tokens(sent)) > ngram + 1:
        #         score = 0.7*self.compute_sent_sim(sent,question,ngram) + 0.3*self.compute_sent_sim(sent,question,1)
        #     else:
        #         score = self.compute_sent_sim(sent,question,1) 
        #     relevant_sentences.append((sent.text,score))
        # return sorted(relevant_sentences,key=lambda pair:(pair[1],pair[0]), reverse=True)[:10]

    # def compute_sent_sim(self, sentence, question, n):
    #     sent_tokens = self.get_tokens(sentence)
    #     question_tokens = self.get_tokens(list(nlp(question).sents)[0])

    #     sent_ngrams = set(self.get_ngrams(sent_tokens,n))
    #     question_ngrams = set(self.get_ngrams(question_tokens,n))

    #     sim = len(sent_ngrams.intersection(question_ngrams)) / len(sent_ngrams.union(question_ngrams))
    #     return sim
    
    def find_NER(self,relevant_sentences):
        NER_pairs = []
        for sent,_ in relevant_sentences:
            sent = list(nlp(sent).sents)[0]
            for token in sent.ents:
                NER_pairs.append((token.text,token.label_))
        return NER_pairs
