from functools import reduce
from pprint import pprint
from cmd import Cmd
import operator
import random
from pychatl import parse
from pychatl.adapters.rasa import rasa
import spacy
from spacy.util import minibatch, compounding

def get_data():
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
    will it rain in @[location] @[date]
    can we expect a sunny day @[date] in @[location]
    should I take an umbrella in @[location] @[date]
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
    return data


def train(data):
    # Constructs all possible intent labels
    intent_labels = { k.upper(): False for k in data['intents'].keys() }

    rasa_data = rasa(data) # Use rasa since it's easy to parse

    train_data = []
    slot_labels = {}
    
    for example in rasa_data['rasa_nlu_data']['common_examples']:
        label = example['intent'].upper()
        categories = intent_labels.copy()
        categories[label] = True
        for slot_label in [ent['entity'].upper() for ent in example['entities'] ]:
            slot_labels[slot_label] = True

        train_data.append(({
            'entities': [(ent['start'], ent['end'], ent['entity'].upper()) for ent in example['entities']],
            'cats': categories,
        }, example['text']))
    
    nlp = spacy.blank('en')

    textcat = nlp.create_pipe(
        'textcat', config={'exclusive_classes': True, 'architecture': 'simple_cnn'},

    )    
    for label in intent_labels:
        textcat.add_label(label)
        print('Added intent', label)

    nlp.add_pipe(textcat)

    ner = nlp.create_pipe("ner")
    for slot_label in slot_labels.keys():
        ner.add_label(slot_label)
    
    nlp.add_pipe(ner)
    
    optimizer = nlp.begin_training()
    batch_sizes = compounding(4.0, 32.0, 1.001)

    print('Start training')
    TEXT_CLASSIFIER_ITER = 20  

    for _ in range(TEXT_CLASSIFIER_ITER):
        losses = {}
        random.shuffle(train_data)
        batches = minibatch(train_data, size=batch_sizes)
        for batch in batches:
            annotations, texts = zip(*batch)
            nlp.update(texts, annotations, sgd=optimizer, drop=0.2, losses=losses)

    print('Done')
    return nlp

if __name__ == '__main__':
    data = get_data()

    nlp = train(data)

    class Repl(Cmd):
        intro = 'Once trained, try the parser or type exit to quit.'
        prompt = '> '

        def default(self, msg):
            doc = nlp(msg)

            print(doc.cats)
            intent = max(doc.cats, key=doc.cats.get)
            slots = ["%s:%s" % (e.text, e.label_) for e in doc.ents]
            print("founded intent:", intent, '-', slots)

        def do_exit(self, _):
            return True

    Repl().cmdloop()
