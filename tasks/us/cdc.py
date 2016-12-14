from luigi import (Task, IntParameter, Parameter, ListParameter, LocalTarget,
                   WrapperTask, BooleanParameter)

from tasks.util import (shell, classpath, CSV2TempTableTask, TempTableTask,
                        TableToCartoViaImportAPI)
from tasks.meta import current_session

from abc import ABCMeta
import os
import re
import requests


class WonderOptions:
    __metaclass__ = ABCMeta

    group_1 = Parameter(default='county')
    group_2 = Parameter(default='age_groups')
    group_3 = Parameter(default='gender')
    group_4 = Parameter(default='')
    group_5 = Parameter(default='')

    locations_by = Parameter(default='state')

    location = ListParameter()
    age_bins = Parameter(default='five_year')

    urbanization_year = Parameter(default='2013')
    urbanization = Parameter(default='all')

    age_group_bins = Parameter(default='five_year')
    age_groups = ListParameter(default=['all'])
    gender = ListParameter(default=['all'])
    hispanic_origin = ListParameter(default=['all'])
    race = ListParameter(default=['all'])

    year = ListParameter()

    weekday = ListParameter(default=['all'])
    autopsy = ListParameter(default=['all'])
    place_of_death = ListParameter(default=['all'])
    cause_of_death_chapter = Parameter(default='ucd_icd_10')
    cause_of_death = ListParameter(default=['all'])

    multiple_cause_of_death_chapter = Parameter(default='ucd_icd_10')
    multiple_cause_of_death = ListParameter(default=['all'])

    show_totals = BooleanParameter(default=True)
    show_zero_values = BooleanParameter(default=True)
    show_suppressed_values = BooleanParameter(default=True)


class DownloadWonder(WonderOptions, Task):

    @property
    def jsessionid(self):
        resp = requests.post('https://wonder.cdc.gov/controller/datarequest/D77',
                             data={'stage': 'about',
                                   'saved_id': '',
                                   'action-I Agree': 'I Agree'})
        match = re.search(r'jsessionid=([0-F]+)', resp.text)

        return match.group(1)


    def run(self):
        self.output().makedirs()
        shell('''
              curl 'https://wonder.cdc.gov/controller/datarequest/D77;jsessionid={jsessionid}' -H 'Host: wonder.cdc.gov' -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:50.0) Gecko/20100101 Firefox/50.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'Referer: https://wonder.cdc.gov/controller/datarequest/D77;jsessionid={jsessionid}' -H 'Cookie: s_vi=[CS]v1|2C110F5E850309B6-40001182E0000165[CE]; _ga=GA1.2.1727535668.1478631102' -H 'DNT: 1' -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' --data 'saved_id=&dataset_code=D77&dataset_label=Multiple+Cause+of+Death%2C+1999-2015&dataset_vintage=2015&stage=request&O_javascript=on&M_1=D77.M1&M_2=D77.M2&M_3=D77.M3&O_aar=aar_none&B_1=D77.V9-level2&B_2=D77.V5&B_3=D77.V7&B_4=*None*&B_5=*None*&O_title=&O_oc-sect1-request=close&O_rate_per=100000&O_aar_pop=0000&VM_D77.M6_D77.V1_S=*All*&VM_D77.M6_D77.V7=*All*&VM_D77.M6_D77.V17=*All*&VM_D77.M6_D77.V8=*All*&VM_D77.M6_D77.V10=&O_location=D77.V9&finder-stage-D77.V9=codeset&O_V9_fmode=freg&V_D77.V9=&F_D77.V9={fips}&I_D77.V9={fips}+%28Florida%29%0D%0A&finder-stage-D77.V10=codeset&O_V10_fmode=freg&V_D77.V10=&F_D77.V10=*All*&I_D77.V10=*All*+%28The+United+States%29%0D%0A&finder-stage-D77.V27=codeset&O_V27_fmode=freg&V_D77.V27=&F_D77.V27=*All*&I_D77.V27=*All*+%28The+United+States%29%0D%0A&O_urban=D77.V19&V_D77.V19=*All*&V_D77.V11=*All*&O_age=D77.V51&V_D77.V5=*All*&V_D77.V51=*All*&V_D77.V52=*All*&V_D77.V6=00&V_D77.V7=*All*&V_D77.V17=*All*&V_D77.V8=*All*&finder-stage-D77.V1=codeset&O_V1_fmode=freg&V_D77.V1=&F_D77.V1={year}&I_D77.V1={year}+%28{year}%29%0D%0A&V_D77.V24=*All*&V_D77.V20=*All*&V_D77.V21=*All*&O_ucd=D77.V2&finder-stage-D77.V2=codeset&O_V2_fmode=freg&V_D77.V2=&F_D77.V2=*All*&I_D77.V2=*All*+%28All+Causes+of+Death%29%0D%0A&V_D77.V4=*All*&V_D77.V12=*All*&V_D77.V22=*All*&V_D77.V23=*All*&V_D77.V25=*All*&O_mcd=D77.V13&finder-stage-D77.V13=codeset&O_V13_fmode=fadv&V_D77.V13=&V_D77.V13_AND=&F_D77.V13=*All*&finder-stage-D77.V15=&O_V15_fmode=fadv&V_D77.V15=&V_D77.V15_AND=&L_D77.V15=*All*&finder-stage-D77.V16=&O_V16_fmode=fadv&V_D77.V16=&V_D77.V16_AND=&L_D77.V16=*All*&finder-stage-D77.V26=&O_V26_fmode=fadv&V_D77.V26=&V_D77.V26_AND=&L_D77.V26=*All*&O_change_action-Send-Export+Results=Export+Results&O_show_totals=true&O_show_zeros=true&O_show_suppressed=true&O_precision=1&O_timeout=600&action-Send=Send' > {output}
              '''.format(
                  jsessionid=self.jsessionid,
                  fips=self.location[0],
                  year=self.year[0],
                  output=self.output().path
              ))

    def output(self):
        '''
        The default output location is in the ``tmp`` folder, in a subfolder
        derived from the subclass's :meth:`~.util.classpath` and its
        :attr:`~.task_id`.
        '''
        return LocalTarget(os.path.join('tmp', classpath(self), self.task_id +
                                        '_{}_{}'.format(self.location[0], self.year[0])))


class ImportWonder(WonderOptions, CSV2TempTableTask):

    delimiter = '\t'

    def requires(self):
        kwargs = self.param_kwargs.copy()
        kwargs.pop('delimiter', None)
        kwargs.pop('has_header', None)
        kwargs.pop('force', None)
        kwargs.pop('encoding', None)
        return DownloadWonder(**kwargs)

    def read_method(self, fname):
        return 'head -n -61 "{input}"'.format(input=fname)

    def input_csv(self):
        return self.input().path


class ProjectionProjectDownloads(WrapperTask):

    def requires(self):
        for year in xrange(2011, 2016):
            for fips in ('01', '36', '08', '53', '12', '22',
                         '30', '49', '55', '17'):
                yield ImportWonder(year=[year], location=[fips])


class ProjectionProjectCombineWonder(TempTableTask):

    year = IntParameter()

    def requires(self):
        for fips in ('01', '36', '08', '53', '12', '22',
                     '30', '49', '55', '17'):
            yield ImportWonder(year=[self.year], location=[fips])

    def run(self):
        session = current_session()
        inputs = self.input()
        session.execute('CREATE TABLE {output} AS SELECT * FROM {input}'.format(
            output=self.output().table,
            input=inputs[0].table))
        for input_ in inputs:
            session.execute('INSERT INTO {output} SELECT * FROM {input}'.format(
                output=self.output().table,
                input=input_.table))

        session.commit()


class ProjectionProjectTransposeWonder(TempTableTask):

    year = IntParameter()

    def requires(self):
        return ProjectionProjectCombineWonder(year=self.year)

    def run(self):
        session = current_session()
        session.execute('''
CREATE TABLE {output} AS
SELECT "County Code" As geoid,
  sum(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) As total_pop,
  sum(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female') As women_all_death,
  sum(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male') As men_all_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '1') As men_1_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '100+') As men_100__death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '10-14') As men_10_14_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '1-4') As men_1_4_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '15-19') As men_15_19_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '20-24') As men_20_24_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '25-29') As men_25_29_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '30-34') As men_30_34_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '35-39') As men_35_39_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '40-44') As men_40_44_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '45-49') As men_45_49_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '50-54') As men_50_54_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '55-59') As men_55_59_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '5-9') As men_5_9_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '60-64') As men_60_64_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '65-69') As men_65_69_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '70-74') As men_70_74_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '75-79') As men_75_79_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '80-84') As men_80_84_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '85-89') As men_85_89_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '90-94') As men_90_94_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '95-99') As men_95_99_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '1') As women_1_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '100+') As women_100__death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '10-14') As women_10_14_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '1-4') As women_1_4_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '15-19') As women_15_19_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '20-24') As women_20_24_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '25-29') As women_25_29_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '30-34') As women_30_34_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '35-39') As women_35_39_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '40-44') As women_40_44_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '45-49') As women_45_49_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '50-54') As women_50_54_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '55-59') As women_55_59_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '5-9') As women_5_9_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '60-64') As women_60_64_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '65-69') As women_65_69_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '70-74') As women_70_74_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '75-79') As women_75_79_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '80-84') As women_80_84_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '85-89') As women_85_89_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '90-94') As women_90_94_death,
  max(NullIf(NullIf("Deaths", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '95-99') As women_95_99_death,

  sum(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female') As women_all_pop,
  sum(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male') As men_all_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '1') As men_1_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '100+') As men_100__pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '10-14') As men_10_14_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '1-4') As men_1_4_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '15-19') As men_15_19_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '20-24') As men_20_24_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '25-29') As men_25_29_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '30-34') As men_30_34_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '35-39') As men_35_39_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '40-44') As men_40_44_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '45-49') As men_45_49_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '50-54') As men_50_54_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '55-59') As men_55_59_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '5-9') As men_5_9_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '60-64') As men_60_64_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '65-69') As men_65_69_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '70-74') As men_70_74_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '75-79') As men_75_79_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '80-84') As men_80_84_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '85-89') As men_85_89_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '90-94') As men_90_94_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Male' AND "Five-Year Age Groups Code" = '95-99') As men_95_99_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '1') As women_1_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '100+') As women_100__pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '10-14') As women_10_14_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '1-4') As women_1_4_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '15-19') As women_15_19_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '20-24') As women_20_24_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '25-29') As women_25_29_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '30-34') As women_30_34_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '35-39') As women_35_39_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '40-44') As women_40_44_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '45-49') As women_45_49_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '50-54') As women_50_54_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '55-59') As women_55_59_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '5-9') As women_5_9_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '60-64') As women_60_64_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '65-69') As women_65_69_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '70-74') As women_70_74_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '75-79') As women_75_79_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '80-84') As women_80_84_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '85-89') As women_85_89_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '90-94') As women_90_94_pop,
  max(NullIf(NullIf("Population", 'Suppressed'), 'Not Applicable')::INT) FILTER (WHERE "Gender" = 'Female' AND "Five-Year Age Groups Code" = '95-99') As women_95_99_pop

  FROM {input}
  GROUP BY "County Code" '''.format(output=self.output().table,
                                    input=self.input().table))
        session.commit()


class ProjectionProjectTransposeWonderAll(WrapperTask):

    def requires(self):
        for year in xrange(2011, 2016):
            yield ProjectionProjectTransposeWonder(year=year)


class UploadProjectionProjectTranspose(WrapperTask):

    # TODO flawed task requires the above already be run

    def requires(self):
        for year in xrange(2010, 2011):
            output = ProjectionProjectTransposeWonder(year=year).output()
            yield TableToCartoViaImportAPI(
                schema='"' + output.schema + '"',
                table=output.tablename
            )
