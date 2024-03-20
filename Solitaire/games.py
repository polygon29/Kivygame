from functools import partial
from kivy.logger import Logger
from cards import Deck
from pile import Foundation, Tableau, Waste
from basegame import BaseGame


class Yukon(BaseGame):
    name = 'Yukon'
    help = """\
Foundations are built up in suit from Ace to King.

The tableau piles build down by alternate colour. Any group of cards can be moved as long as the base card of the group can build on the top card of the destination pile. If the pile is empty then the base card must be a King.

Cards can also be moved back from the foundations.
    """
    decks = 1
    num_tableau = 7
    num_waste = 0
    num_cols = 8
    num_rows = 4.7
    tableau_pos = 0
    foundation_pos = [(7,i) for i in range(4)]
    tableau_depth = [(0,1)] + [(i,5) for i in range(1,7)]

    def build(self):
        for i in range(self.num_tableau):
             self.add_pile(Tableau(self, i, self.tableau_pos, fan='down'))
        for i, s in enumerate(Deck.suits):
            self.add_pile(Foundation(self, *self.foundation_pos[i], suit=s))

 
    def start(self, pile, deck):
        if pile.type == 'tableau':
            for i in range(self.tableau_depth[pile.index][0]):
                pile.add_card(deck.next())
            for i in range(self.tableau_depth[pile.index][1]):
                pile.add_card(deck.next(True))


    def can_add(self, src, pile, group, num):
        if pile.type == 'foundation':
  
            return num == 1 and pile.by_rank(group.top_card(), base=Deck.ace, suit=pile.suit)
        elif pile.type == 'tableau':
     
            return pile.by_alt_color(group.bottom_card(), base=Deck.king, order=-1)
        
class Klondike(Yukon):
    name = 'Klondike'
    help = """\
Foundations are built up in suit from Ace to King.

The tableau piles build down by alternate colour. An empty space can only be filled by a sequence starting with a King.

Touch the deck at top left to deal onto the waste or to redeal the pack if empty. There is no limit to the number of redeals. Cards can also be moved back from the foundations.
    """
    num_waste = 2
    num_cols = 7
    num_rows = 4.25
    y_padding = 0.04
    tableau_pos = 1
    deal_by = 1
    foundation_pos = [(i+3,0) for i in range(4)]
    tableau_depth = [(i,1) for i in range(7)]

    # setup the initial game layout
    def build(self):
        super(Klondike, self).build()
        self.add_pile(Waste(self, 0, 0, show_count='base', on_touch=self.deal_next))
        self.add_pile(Waste(self, 1, 0, show_count='base'))

    # deal initial cards to given pile
    def start(self, pile, deck):
        super(Klondike, self).start(pile, deck)
        if pile.type == 'waste':
            if pile.index == 0:
                for _ in range(24-self.deal_by):
                    pile.add_card(deck.next())
            else:
                for _ in range(self.deal_by):
                    pile.add_card(deck.next(True))

    # callback to deal next 3 cards
    def deal_next(self):
        Logger.debug("Cards: deal")
        pile, waste = self.waste()
        if pile.size() > 0:
            self.move(pile, waste, min(self.deal_by, pile.size()), flip=True)
        else:
            num = waste.size()
            Logger.debug("Cards: pick up %d cards from waste" % num)
            self.move(waste, pile, num, flip=True, append=True)

    # auto-deal onto empty waste pile
    def on_moved(self, move):
         pile, waste = self.waste()
         if waste.size() == 0 and pile.size() > 0:
            self.move(pile, waste, min(self.deal_by, pile.size()), flip=True, append=True, callback=None)
