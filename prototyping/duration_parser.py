import operator
import functools
from datetime import timedelta
from lark import Lark, Transformer, Token
from pprint import pprint

grammar = r"""
integral_numeral: /\d+/
year_unit: /a(ns?)?/i
month_unit: /m(ois)?/i
week_unit: /semaines?/i
day_unit: /j(ours?)?/i
hour_unit: /h(eures?)?/i
minute_unit: /(minutes?|mn)/i
seconde_unit: /secondes?/i
quarter: /quarts?/i
half: /demi/i
_ARTICLE: /d['e]/i
_CONJUCTION: /(et|\,)/i
fraction: quarter | half
unit: year_unit | month_unit | week_unit | day_unit | hour_unit | minute_unit | seconde_unit
fractional_interval: integral_numeral fraction _ARTICLE? unit
full_interval_part: integral_numeral unit
full_interval: full_interval_part (_CONJUCTION? (full_interval_part | fraction))*
start: fractional_interval | full_interval
%import common.WS
%ignore WS
"""
class DurationTransformer(Transformer):
    def DurationTransformer(self):
        Transformer(self)
        self.last_unit = None
    def integral_numeral(self,t):
        (v,) = t
        return  int(v)
    def year_unit(self,t):
        return timedelta(days=365)
    def month_unit(self,t):
        return timedelta(weeks=4)
    def week_unit(self,t):
        return timedelta(weeks=1)
    def day_unit(self,t):
        return timedelta(days=1)
    def hour_unit(self,t):
        return timedelta(hours=1)
    def minute_unit(self, t):
        return timedelta(minutes=1)
    def seconde_unit(self,t):
        return timedelta(seconds=1)
    def quarter(self,t):
        return 0.25
    def half(self,t):
        return 0.5
    def fraction(self,t):
        (v,) = t
        return (v,"F")
    def unit(self, t):
        (v,) = t
        self.last_unit = v
        return v
    def fractional_interval(self, t):
        (v,(f,_),u) = t        
        return (v*u*f,"I")
    def full_interval_part(self, t):
        (v,u) = t    
        return (v*u,"I")
    def full_interval(self, t):
        sum =timedelta()
        for item in t:
            (v,t)=item
            if t == "I":
                sum = sum + v
            elif t == "F":
                sum = sum + self.last_unit * v
        return sum
    def start(self, t):
        (v,) = t
        return v

parser = Lark(grammar, parser="lalr", transformer=DurationTransformer())

tests = {
  "3 quart d'heure": timedelta(minutes=45.0),
  "1 demi minute": timedelta(seconds=30.0),
  "2 heures et 2 minutes": timedelta(hours=2, minutes=2),
  "2 ans et demi": timedelta(days=365*2.5),
  "3 semaines, 2 jours et demi": timedelta(weeks=3, days=2.5),
  "4 mois, 3 semaines, 2 jours, 1 heure": timedelta(weeks=7, days=2, hours=1),
}
for text, expected in tests.items():
  print(text, '=>', 'expected', expected, 'got', parser.parse(text))