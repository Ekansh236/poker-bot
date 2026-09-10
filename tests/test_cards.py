from poker_engine.cards import Card, Deck, Rank, Suit


def test_deck_has_52_unique_cards():
    deck = Deck()
    assert len(deck.cards) == 52
    assert len(set(deck.cards)) == 52


def test_deck_covers_every_rank_and_suit_combo():
    deck = Deck()
    expected = {(rank, suit) for suit in Suit for rank in Rank}
    actual = {(card.rank, card.suit) for card in deck.cards}
    assert actual == expected


def test_deal_card_removes_from_deck():
    deck = Deck()
    initial_count = len(deck.cards)
    card = deck.deal_card()
    assert card is not None
    assert len(deck.cards) == initial_count - 1
    assert card not in deck.cards


def test_deal_card_on_empty_deck_returns_none():
    deck = Deck()
    deck.cards = []
    assert deck.deal_card() is None


def test_shuffle_randomizes_order():
    deck1 = Deck()
    deck2 = Deck()
    # Extremely unlikely to shuffle into the same order as an unshuffled deck.
    deck2.shuffle()
    assert deck1.cards != deck2.cards


def test_card_equality_and_hash():
    a = Card(Rank.ACE, Suit.SPADES)
    b = Card(Rank.ACE, Suit.SPADES)
    c = Card(Rank.KING, Suit.SPADES)
    assert a == b
    assert a != c
    assert hash(a) == hash(b)


def test_rank_is_comparable():
    assert Rank.ACE > Rank.KING
    assert Rank.TWO < Rank.THREE
