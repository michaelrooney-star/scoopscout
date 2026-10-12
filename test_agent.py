import unittest
from unittest.mock import patch
import agent


class AgentTests(unittest.TestCase):
    def test_round_trip_budget(self):
        with patch('agent.model_json', side_effect=[
            {'tool': 'find_places', 'max_walk_minutes': 20},
            {'ids': ['ghirardelli-palace']}
        ]):
            result = agent.plan_break('Chocolate', 30)
            self.assertEqual(result['limit'], 10)
            self.assertEqual(result['places'][0]['outing_minutes'], 20)
            self.assertEqual(result['places'][0]['spare_minutes'], 10)
            self.assertEqual(result['alternatives'][0]['needed_minutes'], 40)
            self.assertNotIn('outing_minutes', agent.CATALOG['places'][0])

    def test_break_too_short(self):
        with patch('agent.model_json', return_value={'tool': 'find_places', 'max_walk_minutes': 20}):
            result = agent.plan_break('Chocolate', 10)
            self.assertEqual(result['places'], [])
            self.assertEqual(result['alternatives'][0]['needed_minutes'], 20)

    def test_limit_excludes_farther_shop(self):
        self.assertEqual([p['id'] for p in agent.find_places(10)], ['ghirardelli-palace'])

    def test_no_match_does_not_invent_shop(self):
        with patch('agent.model_json', return_value={'tool': 'find_places', 'max_walk_minutes': 1}):
            self.assertIn('No verified listings', agent.recommend('One minute away'))

    def test_unverified_ids_rejected(self):
        with patch('agent.model_json', side_effect=[
            {'tool': 'find_places', 'max_walk_minutes': 10}, {'ids': ['invented-shop']}
        ]):
            with self.assertRaises(ValueError):
                agent.recommend('Chocolate')

    def test_rank_and_directions(self):
        with patch('agent.model_json', side_effect=[
            {'tool': 'find_places', 'max_walk_minutes': 20},
            {'ids': ['humphry-ferry', 'ghirardelli-palace']}
        ]):
            result = agent.recommend('Waterfront')
            self.assertLess(result.index('1. Humphry'), result.index('2. Ghirardelli'))
            self.assertIn('travelmode=walking', result)
            self.assertIn('https://humphryslocombe.com/pages/scoop-shops', result)


if __name__ == '__main__':
    unittest.main()
