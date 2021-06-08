python 3.7.0 64-bit
#py -3 -m pip install numpy==1.19.3
#py -3 -m pip install spacy==2.1.0
#py -3 -m pip install neuralcoref==4.0
#py -3 -m spacy download en_core_web_sm
#py -3 -m spacy download en_core_web_lg

import sys
import spacy
import neuralcoref
import re
import random

def get_aux_bin(sent): #7 max for a1  #4 max for a2 
  if sent.text.count(",") > 1: 
    return None 
  if sent.text.count('"') > 0: 
    return None 
  subj_found = False 
  subject = "" 
  verb_found = False 
  question = None
  for idx, token in enumerate(sent): 
    #print(token, token.dep_, token.pos_, token.tag_)
    #locate verb index
    if token.dep_ == "ROOT": 
      verb_found = True 
    #locate subj index 
  if verb_found: 
    for idx, token in enumerate(sent): 
      if token.dep_ == "nsubj": 
        #subj_pos = token.pos_ 
        subj_found = True 
        subj_index = idx 
        if token.pos_ != "PROPN": 
          subject = str(sent[subj_index]).lower()
        else: 
          subject = str(sent[subj_index])
        #only collects was/is questions 
      if subj_found and token.pos_ == "VERB" and (token.tag_ == "VBD" or token.tag_ == "VBZ"): 
        if token.dep_ == "auxpass":   
          question = str(token).capitalize() + " " + subject + " " + str(sent[idx+1:])
          if question[-1] == '\n': 
            question.rstrip('\n')
          question = question[:-1].strip(".") + "?"
        if str(token) == "was" or str(token) == "is" or str(token) == "were": 
          question = str(token).capitalize() + " " + subject + " " + str(sent[idx+1:])
          if question[-1] == '\n': 
            question.rstrip('\n')
          question = question[:-1].strip(".") + "?"
  return question


def get_vb_bin(sent): #not done yet 
  if sent.text.count(",") > 1: 
    return None 
  if sent.text.count('"') > 0: 
    return None 
  subj_found = False 
  subj_type = None 
  subject = "" 
  verb_found = False 
  question = None 
  for idx, token in enumerate(sent): 
    if token.dep_ == "ROOT": 
      verb_index = idx
      verb_found = True 

    if verb_found: 
      if token.dep_ == "nsubj" and token.tag_[:2] == "NN": 
        subj_found = True 
        subj_index = idx 
        subj_tag = token.tag_
        if token.pos_ != "PROPN": 
          subject = str(sent[subj_index]).lower()
        else: 
          subject = str(sent[subj_index])
        # VBZ --> Does, VBP --> Do, VBD --> Did
      for idx, token in enumerate(sent):
        if subj_found and token.pos_ == 'VERB' and token.dep_ != "auxpass": 
          if token.tag_ == "VBZ" and subj_tag == "NNP": 
            question = "Does" + " " + subject + " " + str(token.lemma_) + " " + str(sent[verb_index+1:])
            if question[-1] == '\n': 
              question.rstrip('\n')
            question = question[:-1].strip(".") + "?"

          if token.tag_ == "VBP" and subj_tag == "NNPS": 
            question = "Do" + " " + subject + " " + str(token.lemma_) + " " + str(sent[verb_index+1:])
            if question[-1] == '\n': 
              question.rstrip('\n')
            question = question[:-1].strip(".") + "?"
          
          if token.tag_ == "VBD" and (subj_tag == "NNP" or subj_tag == "NNPS"): 
            question = "Did" + " " + subject + " " + str(token.lemma_)+ " " + str(sent[verb_index+1:])
            if question[-1] == '\n': 
              question.rstrip('\n')
            question = question[:-1].strip(".") + "?"
  return question
def get_who(sent): #also gets what
  verb_found = False
  subj_found = False
  type_found = False
  #locate verb index
  for idx, token in enumerate(sent):
    if token.dep_ == "ROOT": 
      verb_found = True
  #locate subj index
  for idx, token in enumerate(sent):
    if token.dep_ == "nsubj":
      subj_index = idx
      subj_found = True
      if token.ent_type_ == "ORG":
        question_type = "What"
        type_found = True
      if token.ent_type_ == "PERSON":
        question_type = "Who"
        type_found = True
  
  if verb_found and subj_found and type_found:
    question = question_type + " " + str(sent[subj_index+1]) + " " + str(sent[subj_index+2:])
    if question[-1] == "\n":
      question.rstrip("\n")
    question = question[:-1] + "?"

    #post-process
    for i in range(5):
      if question[-2].isalpha() == False and question[-2].isnumeric() == False:
        question = question[:-2] + "?"
      else:
        break

    if "  " in question or '"' in question:
      return None
    if len(question.split()) < 5:
      return None

    return question

def get_where(sent): 
  #for simplicity
  if sent.text.count(",") > 1:
    return None
  if sent.text.count('"') > 0:
    return None
  prepositions = ["at", "on", "in", "off",  "to", "by", "above", "near", "from", "below"]

  verb_found = False
  subj_found = False
  verb_tense = None
  where_found = False

  for idx, token in enumerate(sent):
    if token.ent_type_ == "GPE" or token.ent_type_ == "LOC":
      if idx > 0 and sent[idx-1].text in prepositions:
        where_found = True
        ans_start_index = idx
        ans_end_index = idx + 1
        for i in range(1,3):
          if sent[idx+i].ent_type_ == token.ent_type_:
            ans_end_index = ans_end_index + 1
          else:
            break

  for idx, token in enumerate(sent):
    if token.dep_ == "nsubj":
      if token.tag_ == "NN" or token.tag_ == "NNP" or token.tag_ == "NNPS" or token.tag_ == "NNS":
        subj_index = idx
        subj_found = True
    if token.dep_ == "ROOT":
      verb_found = True
      verb_index = idx
      #VBD VBG VBN VBP VBZ
      verb_tense = token.tag_

  if verb_found == True and subj_found == True and where_found == True and verb_tense != None:
    #change verb form
    verb = str(sent[verb_index])
    base_verb = str(sent[verb_index].lemma_)
    #remove gerunds for simplicity
    if base_verb[-3:] == "ing" or base_verb[-2:] == "ed":
      return None

    question = str(sent[subj_index:subj_index + 1]).strip() + " " + str(sent[subj_index + 1:ans_start_index - 1]).strip() + " " + str(sent[ans_end_index:]).strip()
    question = question.replace(verb, base_verb)

    if verb_tense == "VBN":
      question = "Where did" + " " + question + "?"

    if verb_tense == "VBD" :
      question = "Where did" + " " + question + "?"

    if verb_tense == "VBP":
      question = "Where do" + " " + question + "?"

    if verb_tense == "VBZ":
      question = "Where does" + " " + question + "?"
      
    #post-process
    for i in range(5):
      if question[-2].isalpha() == False and question[-2].isnumeric() == False:
        question = question[:-2] + "?"
      else:
        break

    if "  " in question or '"' in question:
      return None
    if len(question.split()) < 5:
      return None

    return question

def get_when(sent):
  #specific rules to simplify questions
  if sent.text.count(",") > 1:
    return None
  if sent.text.count('"') > 0:
    return None
  prepositions = ["at", "on", "in", "over", "during", "by", "near", "from", "after", "before", "for"]

  verb_found = False
  subj_found = False
  verb_tense = None
  when_found = False
  #get our time
  for idx, token in enumerate(sent):
    if token.ent_type_ == "DATE" or token.ent_type_ == "TIME":
      if idx > 0 and sent[idx-1].text in prepositions:
        when_found = True
        ans_start_index = idx
        ans_end_index = idx + 1
        for i in range(1,6):
          if sent[idx+i].ent_type_ == token.ent_type_:
            ans_end_index = ans_end_index + 1
          else:
            break

  for idx, token in enumerate(sent):
    if token.dep_ == "nsubj":
      if token.tag_ == "NN" or token.tag_ == "NNP" or token.tag_ == "NNPS" or token.tag_ == "NNS":
        subj_index = idx
        subj_found = True
    if token.dep_ == "ROOT":
      verb_found = True
      verb_index = idx
      #VBD VBG VBN VBP VBZ
      verb_tense = token.tag_

  if verb_found == True and subj_found == True and when_found == True and verb_tense != None:
    #transform verb tense
    verb = str(sent[verb_index])
    base_verb = str(sent[verb_index].lemma_)
    #get rid of gerunds
    if base_verb[-3:] == "ing" or base_verb[-2:] == "ed":
      return None

    question = str(sent[subj_index:subj_index + 1]).strip() + " " + str(sent[subj_index + 1:ans_start_index - 1]).strip() + " " + str(sent[ans_end_index:]).strip()
    question = question.replace(verb, base_verb)

    if verb_tense == "VBN":
      question = "When did" + " " + question + "?"

    if verb_tense == "VBD":
      question = "When did" + " " + question + "?"

    if verb_tense == "VBP":
      question = "When do" + " " + question + "?"

    if verb_tense == "VBZ":
      question = "When does" + " " + question + "?"

    #post-process
    for i in range(5):
      if question[-2].isalpha() == False and question[-2].isnumeric() == False:
        question = question[:-2] + "?"
      else:
        break
    
    if "  " in question or '"' in question:
      return None
    if len(question.split()) < 5:
      return None

    return question

#MAIN FUNCTION
def generate_questions(doc):
  question_list = []
  #banned characters to avoid difficult sentences
  banned_list = ["(", ")", ":", "[", "]", "/", "{", "}", "...", "'", "\n"]
  #parse/tokenize document
  for sent in doc.sents:
    banned_sent = False
    token_list = [token.text for token in sent]
    #check length
    if len(sent) > 20 or len(sent) < 5:
      pass
    #check if sent is an actual sentence with a period
    if "." not in token_list: 
      pass
    if '"' in token_list:
      pass
    #check if sentence should be banned
    for banned in banned_list:
      if banned in token_list:
        banned_sent = True
    if banned_sent == True:
      pass
    #if some other rule
    else:    
      temp_qs = []
      temp_qs.append(get_aux_bin(sent))
      temp_qs.append(get_vb_bin(sent))
      temp_qs.append(get_who(sent))
      temp_qs.append(get_where(sent))
      temp_qs.append(get_when(sent))

      for q in temp_qs:
        if q != None:
          question_list.append(q)

  return question_list

def print_questions(question_list, n_questions):
  if len(question_list) < n_questions:
    print("Error: Not enough questions generated from text.")
  else:
    question_counter = 0
    while question_counter < n_questions:
      random_index = random.randint(0, len(question_list)-1)
      random_question = question_list.pop(random_index)
      print(random_question)
      question_counter += 1

def main():
  print("Starting...")

  if len(sys.argv) != 3:
    print("**USAGE ERROR*** ./ask article.txt nquestions")
    sys.exit(1)
  
  article_text = sys.argv[1]
  n_questions = sys.argv[2]
  n_questions = int(n_questions)

  with open(article_text, 'r', encoding = 'utf8') as f:
    text = f.read()
  newtext = text.split('\n\n') #list of sections
  nlp = spacy.load('en_core_web_sm')
  neuralcoref.add_to_pipe(nlp, greedyness = 0.3, max_dist = 50)

  final_question_list = []
  final_question_list_non_coref = []

  for section in newtext: 

    doc = nlp(section)
    coref_doc = doc._.coref_resolved
    coref_doc = nlp(coref_doc)

    question_list = generate_questions(coref_doc)

    for question in question_list:
      final_question_list.append(question)
  
  print("_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _\n")
  print_questions(final_question_list, n_questions)
  print("\n")


if __name__ == "__main__":
  main()
