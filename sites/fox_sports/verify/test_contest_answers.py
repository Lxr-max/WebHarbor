import pytest
from contract_engine import check_contest_answer


def contest(score=2):
    initial = {'super6_entries': {}, 'super6_questions': {}}
    after = {'super6_entries': {'[1]': {'user_id': 1, 'contest_id': 1, 'score': score},
                                '[2]': {'user_id': 2, 'contest_id': 1, 'score': 6}}}
    return initial, after, {'user_id': 1, 'contest_id': 1, 'strategy': 'any'}


@pytest.mark.parametrize('answer', [
    'My entry scored two of six and is four points behind the leader.',
    'My entry scored 2/6; the gap to the highest score is 4 points.',
])
def test_equivalent_leaderboard_comparison(answer):
    check_contest_answer(answer, *contest())


@pytest.mark.parametrize('answer', [
    'My entry scored 2/6; the highest score is 6.',
    'My entry scored 2/6 and is three points behind the leader.',
    'My entry scored 2/6 and is tied with the leader.',
])
def test_missing_or_wrong_comparison(answer):
    with pytest.raises(ValueError, match='leaderboard comparison'):
        check_contest_answer(answer, *contest())


def test_perfect_picks_tie_leader():
    check_contest_answer('My entry scored 6/6 and is tied with the leader.', *contest(6))


@pytest.mark.parametrize('spread', ['-3', '-3.0'])
def test_spread_format_and_unaccented_venue(spread):
    initial = {'super6_questions': {'[1]': {'order': 1, 'correct_pick': 'baltimore-ravens', 'game_slug': 'baltimore-dallas'}},
               'games': {'[1]': {'slug': 'baltimore-dallas', 'venue': 'Maracanã Stadium', 'spread': '-3.0'}},
               'teams': {'[1]': {'slug': 'baltimore-ravens', 'full_name': 'Baltimore Ravens'}}}
    after = {'super6_entries': {'[1]': {'user_id': 4, 'contest_id': 1, 'score': 3, 'picks': 'dallas-cowboys'}}}
    check_contest_answer(f"Dana's entry scored 3/6, with misses on 3 questions. Baltimore Ravens won at Maracana Stadium, with Baltimore {spread}.",
                         initial, after, {'user_id': 4, 'contest_id': 1, 'strategy': 'alternating'})
