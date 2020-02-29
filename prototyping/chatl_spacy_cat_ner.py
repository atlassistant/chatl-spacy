from functools import reduce
from pprint import pprint
from cmd import Cmd
import operator
import random
from pychatl import parse
from pychatl.adapters.rasa import rasa
import spacy
from spacy.util import minibatch, compounding

def get_train_data():
    data = parse("""
%[lights_on]
    turn the @[room]'s lights on would you
    turn lights on in the @[room]
    lights on in @[room] please
    turn on the lights in @[room]
    turn the lights on in @[room]
    enlight me in @[room]

%[lights_off]
    turn the @[room]'s lights off would you
    turn lights off in the @[room]
    lights off in @[room] please
    lights off in @[room] and @[room]
    turn off the lights in @[room]
    turn the lights off in @[room]

%[start_vacuum_cleaner]
    start ~[vacuum_cleaner]
    would you like start ~[vacuum_cleaner] please

%[stop_vacuum_cleaner]
    stop ~[vacuum_cleaner]
    would you like stop ~[vacuum_cleaner] please

%[get_forecast]
    will it be sunny in @[location] at @[date#at]
    what's the weather like in @[location] on @[date#on]
    what's the weather like
    will it rain in @[location] @[date]
    will it rain @[date]
    what kind of weather should I expect at @[date#at] in @[location]
    what will be the weather on @[date#on] in @[location]
    tell me if it is going to rain @[date] in @[location]

~[vacuum_cleaner]
    vacuum cleaner
    vacuum
    vacuuming
    hoover
    hoovering
    aspirator

~[basement]
    cellar

@[room](extensible=false)
    living room
    kitchen
    bedroom
    ~[basement]

@[location]
    los angeles
    paris
    rio de janeiro
    tokyo
    london
    tel aviv
    new york
    saint-étienne du rouvray

@[date](type=datetime)
    tomorrow
    today
    this evening

@[date#at]
    the end of the day
    nine o'clock

@[date#on]
    tuesday
    monday

""")

    # Constructs all possible intent labels
    labels = { k.upper(): False for k in data['intents'].keys() }
    rasa_data = rasa(data) # Use rasa since it's easy to parse

    train_data = []

    for example in rasa_data['rasa_nlu_data']['common_examples']:
        label = example['intent'].upper()
        categories = labels.copy()
        categories[label] = True
        train_data.append(({ 
            'cats': categories,
            'entities': [(ent['start'], ent['end'], ent['entity'].upper()) for ent in example['entities']],
        }, example['text']))

    return labels.keys(), train_data

TEXT_CLASSIFIER_ITER = 20
NER_ITER = 20

def train_text_classifier(intents, data):
    nlp = spacy.blank('en')
    textcat = nlp.create_pipe(
        'textcat', config={'exclusive_classes': True, 'architecture': 'simple_cnn'},
    )
    nlp.add_pipe(textcat)

    for label in intents:
        textcat.add_label(label)
        print('Added intent', label)

    optimizer = nlp.begin_training()
    batch_sizes = compounding(4.0, 32.0, 1.001)

    print('Start training text classifier')

    for _ in range(TEXT_CLASSIFIER_ITER):
        losses = {}
        random.shuffle(data)
        batches = minibatch(data, size=batch_sizes)
        for batch in batches:
            annotations, texts = zip(*batch)
            nlp.update(texts, annotations, sgd=optimizer, drop=0.2, losses=losses)
    
    print('Done!')

    return nlp

def train_ner(intents, data):
    nlp_per_intent = { intent: spacy.blank('en') for intent in intents }

    for intent, nlp in nlp_per_intent.items():
        intent_data = [d for d in data if d[0]['cats'][intent]]
        ner = nlp.create_pipe("ner")
        nlp.add_pipe(ner)

        slots = set([ent_data[2] for d in intent_data for ent_data in d[0]['entities']])

        for slot in slots:
            ner.add_label(slot)

        optimizer = nlp.begin_training()
        batch_sizes = compounding(4.0, 32.0, 1.001)

        print('Start training ner for', intent)

        for _ in range(NER_ITER):
            losses = {}
            random.shuffle(intent_data)
            batches = minibatch(intent_data, size=batch_sizes)
            for batch in batches:
                annotations, texts = zip(*batch)
                nlp.update(texts, annotations, sgd=optimizer, drop=0.2, losses=losses)

        print('Done')

    return nlp_per_intent

if __name__ == '__main__':
    intents, train_data = get_train_data()

    intents_parser = train_text_classifier(intents, train_data)
    ner_per_intent = train_ner(intents, train_data)

    class Repl(Cmd):
        intro = 'Once trained, try the parser or type exit to quit.'
        prompt = '> '

        def default(self, msg):
            doc = intents_parser(msg)

            if not doc.cats:
                print('Unknown intent')

            intent = max(doc.cats, key=doc.cats.get)

            doc = ner_per_intent[intent](msg)
            slots = ["%s:%s" % (e.text, e.label_) for e in doc.ents]

            print(intent, '-', slots)

        def do_exit(self, _):
            return True

    Repl().cmdloop()
