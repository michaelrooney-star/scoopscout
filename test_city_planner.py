import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
import city_planner as cp
import google_calendar as gc


def dt(hour, minute=0):
    return datetime(2026,10,13,hour,minute,tzinfo=cp.SF)


class CityPlannerTests(unittest.TestCase):
    def test_merge_overlaps_and_clip(self):
        result=cp.gaps([(dt(11),dt(13)),(dt(12),dt(14)),(dt(15),dt(16))],dt(12),dt(17))
        self.assertEqual(result,[(dt(14),dt(15)),(dt(16),dt(17))])

    def test_all_day_busy(self):
        self.assertEqual(cp.gaps([(dt(0),dt(23))],dt(12),dt(20)),[])

    def test_location_rejects_other_cities(self):
        with self.assertRaises(ValueError): cp.validate_location({'lat':40.7,'lon':-74})

    def test_closed_shop_excluded(self):
        from agent import CATALOG
        p=next(x for x in CATALOG['places'] if x['id']=='birite')
        self.assertFalse(cp.fits_hours(p,dt(11)))
        self.assertTrue(cp.fits_hours(p,dt(12)))
        self.assertFalse(cp.fits_hours(p,dt(20,55)))

    def test_sf_time_conversion(self):
        self.assertEqual(cp.parse_time('2026-10-13T19:00:00Z'),dt(12))

    def test_future_gap_no_private_data_in_prompt(self):
        data={'location':{'lat':37.7616,'lon':-122.4258},'start':dt(12).isoformat(),'end':dt(14).isoformat(),'query':'Chocolate'}
        with patch('agent.model_json',side_effect=RuntimeError('offline')) as model:
            result=cp.plan_day(data,[(dt(12),dt(12,30)),(dt(13),dt(14))],now=dt(11))
            self.assertTrue(result['places'])
            for p in result['places']:
                self.assertGreaterEqual(cp.parse_time(p['departure']),dt(12,30))
                self.assertLessEqual(cp.parse_time(p['return_at'])+cp.timedelta(minutes=5),dt(13))
            prompt=str(model.call_args)
            self.assertNotIn('37.7616',prompt)
            self.assertNotIn('2026-10-13',prompt)
            self.assertIn('Model unavailable',result['ranking'])

    def test_no_free_gap_no_model_call(self):
        data={'location':{'lat':37.7616,'lon':-122.4258},'start':dt(12).isoformat(),'end':dt(14).isoformat()}
        with patch('agent.model_json') as model:
            result=cp.plan_day(data,[(dt(12),dt(14))],now=dt(11))
            self.assertEqual(result['places'],[])
            model.assert_not_called()

    def test_calendar_api_error_is_not_free_time(self):
        service=MagicMock()
        service.freebusy().query().execute.return_value={'calendars':{'primary':{'errors':[{'reason':'notFound'}]}}}
        with patch.object(gc,'credentials',object()),patch.object(gc,'build',return_value=service):
            with self.assertRaises(ValueError):gc.busy(dt(12),dt(14))

    def test_oauth_state_required(self):
        with self.assertRaises(ValueError):gc.finish('state=not-valid&code=ignored')


if __name__=='__main__':unittest.main()
