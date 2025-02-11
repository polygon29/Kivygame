import ast
from kivy.core.window import Window
from kivy.properties import ListProperty, NumericProperty, ObjectProperty
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter
from kivy.logger import Logger

from cards import Card, Deck
from basegame import BaseGame
import games

# mixin class for group of cards
class CardsList(object):
    images = ListProperty([])
    split = False

    def cards(self): return len(self.images)

    def card_list(self): return [i.card for i in self.images]

    def top_card(self): return self.images[-1].card

    def bottom_card(self): return self.images[0].card


# on screen card image
class CardImage(Image, CardsList):
    alpha = NumericProperty(0)
    yoffset = NumericProperty(0)
    callback = ObjectProperty(None)
    card = ObjectProperty(None)
 
    def __init__(self, **kwargs):
        super(CardImage, self).__init__(**kwargs)
        self.images.append(self)

    def on_touch_down(self, touch):
        if self.callback and self.collide_point(*touch.pos):
            Logger.debug("Cards: CardImage on_touch_down")
            touch.grab(self)
            self.callback()
            return True

    def lock(self, state): pass

    def resize(self, xpos, ypos, size, xstep=0, ystep=0):
        Logger.debug("Cards: image resize %s at %d,%d" % (size, xpos, ypos))
        self.images[0].size = size
        self.pos = (xpos, ypos)
        return xpos+xstep, ypos-ystep

class CardScatter(Scatter, CardsList):
    callback = ObjectProperty(None)
    pile = ObjectProperty(None)
    selected = 0
    
    # add a new image to top of pile
    def add_image(self, img, step=False):
        if step:
            self.y -= self.pile.ystep
            self.width += self.pile.xstep
            self.height += self.pile.ystep
            for child in self.images: 
                child.y += self.pile.ystep
                child.yoffset += self.pile.ystep
        self.images.append(img)
        self.add_widget(img)

    # remove bottom image, but keep widget in same place
    def remove_image(self):
        if not self.images: return None
        img = self.images.pop(0)
        self.remove_widget(img)
        self.width -= self.pile.xstep
        self.height -= self.pile.ystep
        img.y -= img.yoffset
        img.yoffset = 0
        return img
 
    def resize(self, xpos, ypos, size, xstep=0, ystep=0):
        pos = (xpos, ypos)
        for i, img in enumerate(self.images):
            img.size = size
            if i > 0:
                pos = (pos[0]+xstep, pos[1]-ystep)
        self.pos = pos
        Logger.debug("Cards: scatter pos -> %d,%d" % pos)
        yoff = 0
        for img in reversed(self.images):
            #Logger.debug("Cards: scatter yoffset %d -> %d" % (ystep, yoff))
            img.y = yoff
            img.yoffset = yoff
            yoff += ystep
        return pos[0]+xstep, pos[1]-ystep

    # select one or more cards from the group
    def on_touch_down(self, touch):
        if not super(CardScatter, self).on_touch_down(touch): return False
        Logger.debug("Cards: CardScatter on_touch_down")

        if self is self.pile.top():
            self.auto_bring_to_front = True
            # which image was touched?
            self.selected = 0
            for child in list(reversed(self.images)):
                child.alpha = 1
                self.selected += 1
                if touch.pos[1] <= self.y+child.y+child.height: break 
            Logger.debug("Cards: selected %d out of %d cards" % (self.selected, self.cards()))

            if self.selected < self.cards():
                self.split = self.pile.split_top_widget(self.selected)

            if self.selected == 1 and touch.is_double_tap:
                Logger.debug("Cards: double tap")
                self.pile.on_release(auto=True)
                return False

        return True
 
    # release the selection, dragging to new location
    def on_touch_up(self, touch):
        if not super(CardScatter, self).on_touch_up(touch): return False
        if self.selected > 0:
            for child in self.images:
                child.alpha = 0
            if self.callback: self.callback()
            self.selected = 0
        return True

    # make the scatter not movable if covered
    def lock(self, state):
        self.auto_bring_to_front = not state
        self.do_translation_x = not state
        self.do_translation_y = not state

class Pile():
    type = ''
    index = 0

    def __init__(self, game, col, row, suit='', fan='', show_count='', on_touch=None):
        self.col, self.row = col, row
        self.suit = suit
        self.fan = fan
        self.show_count = show_count
        game.position_pile(self)
        Logger.debug("Cards: new pile type=%s pos=%d %d fan=%s %d %d counter=%s" % 
                    (self.type, col, row, fan, self.xstep, self.ystep, show_count))
        self.game = game
        self.layout = game.layout
        self.widgets = []
        self.counter = None
        self.add_base(Card.base_image(suit), on_touch)
        self.clear(1)

    # accessors
    def base(self): return self.widgets[0]

    def size(self): return len(self.widgets)-1

    def top(self): return self.widgets[-1]

    def bottom(self): return self.widgets[1]

    def next(self): return self.widgets[-2]

    def pid(self): return (self.type, self.index)

    def __str__(self): return "%s%d" % self.pid()

    # position of tiop of pile
    def top_pos(self, offset=0):
        x, y = self.x, self.y
        for w in self.widgets[1:]:
            ncards = w.cards()
            x += ncards*self.xstep
            y -= ncards*self.ystep
        return x-offset*self.xstep, y+offset*self.ystep

    # build rules
    def by_rank(self, card, base=None, order=1, suit=None, wrap=False):
        if suit is not None and card.suit != suit:
            return False
        else:
            if self.size() ==0:
                return base is None or card.rank == base
            else:
                top = self.top().top_card()
                return card.rank == top.next_rank(order,wrap)

    def by_alt_color(self, card, base=None, order=1, wrap=False):
        if self.size() == 0:
            return base is None or card.rank == base
        else:    
            top = self.top().top_card()
            return card.color() != top.color() and card.rank == top.next_rank(order,wrap)

    def counter_pos(self):
        if self.show_count == 'right':
            return self.x+self.csize[0], self.y+(self.csize[1]-Counter.ysize)/2
        elif self.show_count == 'left':
            return self.x-Counter.xsize, self.y+(self.csize[1]-Counter.ysize)/2
        else:
            return self.x+(self.csize[0]-Counter.xsize)/2, self.y-Counter.ysize

    # bottom of pile
    def add_base(self, image, on_touch):
        self.widgets.append(CardImage(source=image, size=self.csize, pos=(self.x,self.y)))
        if on_touch:
            self.base().callback = on_touch
        self.layout.add_widget(self.base())
        if self.show_count:
            self.counter = Counter(pos=self.counter_pos())
            self.layout.add_widget(self.counter)
 
    # redraw after screen resize
    def redraw(self):
        xpos, ypos = self.x, self.y
        Logger.debug("Cards: redraw pile %s at %d,%d" % (self, xpos, ypos))
        # resize base of pile
        self.widgets[0].resize(xpos, ypos, self.csize)
        if self.counter:
            self.counter.pos = self.counter_pos()
        # resize cards
        for w in self.widgets[1:]:
            xpos, ypos = w.resize(xpos, ypos, self.csize, self.xstep, self.ystep)
        self.layout._trigger_layout()

    # empty the pile
    def clear(self, base):
        for w in self.widgets[base:]:
            self.layout.remove_widget(w)            
        del self.widgets[base:]
        if self.counter: 
            if base == 0: self.layout.remove_widget(self.counter)
            self.counter.count = 0

    # add list of cards
    def add_cards(self, cards, faceup=None):
        for c in cards:
            if faceup != None: c.faceup = faceup
            self.add_card(c)
        return len(cards)

    # add card onto top 
    def add_card(self, card):
        #Logger.debug("cards: add %s to %s %d" % (card, self.type, self.index))
        top = self.top()
        img = CardImage(card=card, source=card.image(), size=self.csize)
        if (card.faceup and self.type != 'waste' and
                top.top_card() and top.top_card().faceup and 
                self.game.can_join(self, card) ):
            #Logger.debug("cards: add to existing scatter")
            top.add_image(img, step=True)
        else:
            if card.faceup:
                top = CardScatter(size=self.csize, pos=self.top_pos(), 
                        callback=self.on_release, pile=self)
                top.add_image(img)
            else:
                img.pos = self.top_pos()
                top = img
            # lock underneath widgets so we can't move em
            for under in self.widgets: under.lock(True)
            self.layout.add_widget(top)
            self.widgets.append(top)
        if self.counter: self.counter.count += 1
    def remove_cards(self):
        if self.size() == 0: return []
        w = self.widgets.pop()
        self.layout.remove_widget(w)
        if self.counter: self.counter.count -= w.cards()
        return w.card_list()
    
    def take_cards(self, expose=False, flip=False):
        cards = self.remove_cards()
        if flip:
            for c in cards: c.faceup = not(c.faceup)
        if expose and self.size() > 0:
            card2 = self.remove_cards()
            self.add_cards(card2, faceup=True)
        return cards
    
    def move_cards_to(self, dest, expose=False, cover=False, flip=False):
        cards = self.take_cards(expose, flip)
        if cover and dest.size() > 0:
            # undo expose
            card2 = dest.remove_cards()
            dest.add_cards(card2, faceup=False)
        return dest.add_cards(cards)
    def move_num_cards_to(self, dest, total, expose=False, cover=False, flip=False):
        moved = 0
        while moved < total:
            num = self.top().cards()
            if moved + num <= total:
                moved += self.move_cards_to(dest, expose, cover, flip)
            else:
                ok = self.split_top_widget(total-moved)
                if not ok: return

    # split the scatter on top into two as we've partally grabbed it
    # note: assumes fan='down'
    def split_top_widget(self, selected):
        top = self.top()
        if top.cards() <= selected:
            Logger.warning("Cards: can't split %d out of %d" % (selected, top.cards()))
            return False
        self.layout.remove_widget(top)
        ypos = top.y + top.cards()*self.ystep
        size = (self.csize[0], self.csize[1]-self.ystep)
        under = CardScatter(size=size, pos=(top.x, ypos), callback=top.callback, pile=self)
        for _ in range(top.cards()-selected):
            under.add_image(top.remove_image(), step=True)
        self.widgets.insert(-1, under)
        self.layout.add_widget(under)
        self.layout.add_widget(top)
        return True

    # move the top card(s) back to starting position
    def move_cards_back(self):
        w = self.top()
        if w.split:
            Logger.debug("Cards: rejoin split pile - cards=%d" % w.cards())
            self.move_cards_to(self)
        else:
            w.pos = self.top_pos(1)

    # writes cards on stack to config file
    def save(self, config):
        data = []
        for group in self.widgets[1:]:
            data += [card.export() for card in group.card_list()]
        config.set('piles', str(self), data)

    # read back the data
    def load(self, config):
        name = str(self)
        self.clear(1)
        if config.has_option('piles', name):
            cards = ast.literal_eval(config.get('piles', name))
            for card in cards:
                self.add_card(Card(*card))
            if self.counter: 
                self.counter.count = len(cards)


# types of pile
class Foundation(Pile):
    type = 'foundation'

class Tableau(Pile):
    type = 'tableau'

class Waste(Pile):
    type = 'waste'


# label with no. of cards in pile
class Counter(Label):
    count = NumericProperty(0)
    xsize = Window.width*0.03
    ysize = Window.height*0.03