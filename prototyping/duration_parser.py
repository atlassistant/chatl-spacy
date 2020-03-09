import operator
import functools
from datetime import timedelta
from lark import Lark, Transformer, Token
from pprint import pprint

grammar = r"""
YEAR: /a(ns?)?/i
MONTH: /m(ois)?/i
WEEK.1: /sem(aines?)?/i
DAY: /j(our(née)?s?)?/i
HOUR: /h(eures?)?/i
MINUTE: /(minutes?|mn)/i
SECOND.0: /s(econdes?)?/i
QUARTER: /quarts?/i
HALF: /demi/i
_ARTICLE: /d['e]/i
_CONJUCTION: /(et|\,)/i
ZERO: /z(e|é)ro/i
ONE: /un(e)/i
TWO: /(deux|couple)/i
THREE: /trois/i
FOUR: /quatre/i
FIVE: /cinq/i
SIX: /six/i
SEVEN: /sept/i
EIGHT: /huit/i
NINE: /neuf/i
TEN: /di(x|zaines?)/i
ELEVEN: /onze/i
TWELVE: /douz(e|aines?)/i
THIRTEEN: /treize/i
FOURTEEN: /quatorze/i
FIFTEEN: /quinz(e|aine)s?/i
SIXTEEN: /seize/i
TWENTY: /vingt(aine)?s?/i
THIRTY: /trent(e|aine)s?/i
FOURTY: /quarant(e|aine)s?/i
FIFTY: /cinquant(e|aine)s?/i
SIXTY: /soixant(e|aine)s?/i
HUNDRED: /cent(aine)?s?/i
THOUSAND: /mill(e|ier)s?/i
digit_letter: ZERO | ONE | TWO | THREE | FOUR | FIVE | SIX | SEVEN | EIGHT | NINE | TEN | ELEVEN | TWELVE | THIRTEEN | FOURTEEN | FIFTEEN | SIXTEEN | THIRTY | FOURTY | FIFTY | SIXTY
basis_letter:   TWENTY | HUNDRED | THOUSAND
number_digit: /\d+/
fraction: QUARTER | HALF
unit: YEAR | MONTH | WEEK | DAY | HOUR | MINUTE | SECOND
number_letter: (digit_letter? basis_letter)+ digit_letter? | digit_letter
number: number_digit | number_letter
interval_part: number unit
interval_and_number: interval_part number
fractional_interval: number fraction _ARTICLE? unit
full_interval: interval_part (_CONJUCTION? interval_part)*
interval_and_fraction: interval_part _CONJUCTION fraction
start: fractional_interval | interval_and_fraction | interval_and_number | full_interval
%import common.WS
%ignore WS
"""

class DurationTransformer(Transformer):
    def DurationTransformer(self):
        Transformer(self)
        self.last_unit = None
    def subunit(self,u):
        SUBUNIT={
            "HOUR":"MINUTE",
            "MINUTE":"SECOND",
        }
        return SUBUNIT[u] if u in SUBUNIT else None

    def unitToValue(self,u):
        UNIT_TO_VALUE={
            "YEAR":timedelta(days=365),
            "MONTH":timedelta(weeks=4),
            "WEEK":timedelta(weeks=1),
            "DAY":timedelta(days=1),
            "HOUR":timedelta(hours=1),
            "MINUTE":timedelta(minutes=1),
            "SECOND":timedelta(seconds=1),
        }
        return UNIT_TO_VALUE[u] if u in UNIT_TO_VALUE else None

    def fractionToValue(self,f):
        FRACTION_TO_VALUE={
            "QUARTER":0.25,
            "HALF":0.5,
        }
        return FRACTION_TO_VALUE[f] if f in FRACTION_TO_VALUE else None

    def numberLetterToValue(self, n):
        NUMBER_LETTER_TO_VALUE={
            "ZERO": 0,
            "ONE": 1,
            "TWO": 2,
            "THREE": 3,
            "FOUR": 4,
            "FIVE": 5,
            "SIX": 6,
            "SEVEN": 7,
            "EIGHT": 8,
            "NINE": 9,
            "TEN": 10,
            "ELEVEN": 11,
            "TWELVE": 12,
            "THIRTEEN": 13,
            "FOURTEEN": 14,
            "FIFTEEN": 15,
            "SIXTEEN": 16,
            "TWENTY": 20,
            "THIRTY": 30,
            "FOURTY": 40,
            "FIFTY": 50,
            "SIXTY": 60,
            "HUNDRED": 100,
            "THOUSAND": 1000,
        }
        return NUMBER_LETTER_TO_VALUE[n] if n in NUMBER_LETTER_TO_VALUE else None
    
    def number_digit(self,t):
        (v,) = t
        return  int(v.value)

    def digit_letter(self,t):
        (l,)=t
        return (False,self.numberLetterToValue(l.type))

    def basis_letter(self,t):
        (l,)=t
        return (True, self.numberLetterToValue(l.type))

    def fraction(self,t):
        (v,) = t
        return v.type
    def unit(self, t):
        (v,) = t
        self.last_unit = v.type
        return v.type

    def number_letter(self, t):
        total = 0
        current_number = 0
        for item in t:
            (is_base, value) = item
            if is_base:
                current_number = current_number * value if current_number != 0 else value
            else:
                total = total + current_number
                current_number = value
        return total + current_number

    def number(self, t):
        (v,) = t
        return v

    def interval_part(self,t):
        (v,u) = t
        delta = self.unitToValue(u)
        return delta * v
    def fractional_interval(self,t):
        (v,f,u) = t
        delta = self.unitToValue(u)
        fract = self.fractionToValue(f)
        return delta * fract * v
    def interval_and_integral_numeral(self,t):
        (v,i) = t
        u = self.subunit(self.last_unit)
        delta = self.unitToValue(u)
        return v + delta * i
    def interval_and_fraction(self,t):
        (v,f) = t
        delta = self.unitToValue(self.last_unit)
        fract = self.fractionToValue(f)
        return v + delta * fract
    def full_interval(self,t):
        delta = timedelta()
        for item in t:
            delta = delta + item
        return delta
    def start(self,t):
        (v,) = t
        return v

parser = Lark(grammar, parser="lalr", transformer=DurationTransformer())
#parser = Lark(grammar, parser="lalr")

tests = {
  "3 quart d'heure": timedelta(minutes=45.0),
  "1 demi minute": timedelta(seconds=30.0),
  "2 heures et 3 minutes": timedelta(hours=2, minutes=3),
  "2 ans et demi": timedelta(days=365*2.5),
  "1h30": timedelta(hours=1, minutes=30),
  "4 mois, 3 semaines, 2 jours, 1 heure": timedelta(weeks=7*4 + 3, days=2, hours=1),
  "2h4mn5s": timedelta(hours=2,minutes=4,seconds=5),
  "9 semaines et demi": timedelta(days=9*7 + 3.5),
  "vingt quatre heures" : timedelta(hours=24),
  "quatre vingt jours": timedelta(days=80)
}
for text, expected in tests.items():
  print(text, '=>', 'expected', expected, 'got', parser.parse(text))
