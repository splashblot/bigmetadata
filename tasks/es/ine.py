#http://www.ine.es/pcaxisdl/t20/e245/p07/a2015/l0/0001.px

import csv
import os


from collections import OrderedDict
from luigi import Task, LocalTarget
from tasks.meta import BMDColumn, BMDColumnToColumn, BMDTag
from tasks.util import (LoadPostgresFromURL, classpath, pg_cursor, shell,
                        CartoDBTarget, get_logger, underscore_slugify, TableTask,
                        session_scope, ColumnTarget, ColumnsTask, TagsTask,
                        classpath, DefaultPostgresTarget)


class Tags(TagsTask):

    def tags(self):
        return [
            BMDTag(id='demographics',
                   name='Demographics of Spain',
                   description='Demographics of Spain from the INE Census')
        ]


class DownloadGeometry(Task):

    URL = 'http://www.ine.es/censos2011_datos/cartografia_censo2011_nacional.zip'

    def run(self):
        self.output().makedirs()
        shell('wget {url} -O {output}'.format(url=self.URL,
                                              output=self.output().path))

    def output(self):
        return LocalTarget(os.path.join('tmp', classpath(self),
                                        'cartografia_censo2011_nacional.zip'))


class RawGeometry(Task):

    def requires(self):
        return DownloadGeometry()

    @property
    def schema(self):
        return classpath(self)

    @property
    def tablename(self):
        return 'raw_geometry'

    def run(self):
        with session_scope() as session:
            session.execute('CREATE SCHEMA IF NOT EXISTS "{schema}"'.format(
                schema=classpath(self)))

        cmd = 'unzip -o "{input}" -d "$(dirname {input})/$(basename {input} .zip)"'.format(
            input=self.input().path)
        shell(cmd)
        cmd = 'PG_USE_COPY=yes PGCLIENTENCODING=latin1 ' \
                'ogr2ogr -f PostgreSQL PG:dbname=$PGDATABASE ' \
                '-t_srs "EPSG:4326" -nlt MultiPolygon -nln {table} ' \
                '-lco OVERWRITE=yes ' \
                '-lco SCHEMA={schema} -lco PRECISION=no ' \
                '$(dirname {input})/$(basename {input} .zip)/*.shp '.format(
                    schema=self.schema,
                    table=self.tablename,
                    input=self.input().path)
        shell(cmd)
        self.output().touch()

    def output(self):
        return DefaultPostgresTarget(table='"{schema}".{table}'.format(
            schema=self.schema,
            table=self.tablename
        ))


class GeometryColumns(ColumnsTask):

    def columns(self):
        geom = BMDColumn(
            id='cusec_geom',
            name=u'Secci\xf3n Censal',
            type="Geometry",
            weight=10,
            description='The finest division of the Spanish Census.'
        )
        geoid = BMDColumn(
            id='cusec_geoid',
            name=u"Secci\xf3n Censal",
            type="Text",
            targets={
                geom: 'geom_ref'
            }
        )
        return OrderedDict([
            ("cusec_id", geoid),
            ("cusec_geom", geom),
        ])


class Geometry(TableTask):

    def requires(self):
        return {
            'meta': GeometryColumns(),
            'data': RawGeometry()
        }

    def columns(self):
        return self.input()['meta']

    def timespan(self):
        return '2011'

    def bounds(self):
        if not self.input()['data'].exists():
            return
        with session_scope() as session:
            with session.no_autoflush:
                return session.execute(
                    'SELECT ST_EXTENT(wkb_geometry) FROM '
                    '{input}'.format(input=self.input()['data'].table)
                ).first()[0]

    def runsession(self, session):
        session.execute('INSERT INTO {output} '
                        'SELECT cusec as cusec_id, '
                        '       wkb_geometry as cusec_geom '
                        'FROM {input} '.format(
                            output=self.output().get(session).id,
                            input=self.input()['data'].table))


class Download(Task):

    URL = 'http://www.ine.es/pcaxisdl/t20/e245/p07/a2015/l0/0001.px'

    def run(self):
        self.output().makedirs()
        cmd = 'wget "{url}" -O "{output}"'.format(url=self.URL,
                                              output=self.output().path)
        shell(cmd)

    def output(self):
        return LocalTarget(os.path.join('tmp', classpath(self), '0001.px'))


class Parse(Task):
    '''
    convert px file to csv
    '''

    def requires(self):
        return Download()

    def run(self):
        output = self.output()
        dimensions = []
        self.output().makedirs()
        with self.output().open('w') as outfile:
            section = None
            with self.input().open() as infile:
                for line in infile:
                    line = line.strip()
                    if line.startswith('VALUES'):
                        section = 'values'
                        dimensions.append([line.split('"')[1], [], 0])
                        line = line.split('=')[1]

                    if section == 'values':
                        dimensions[-1][1].extend([l.strip(';" ') for l in line.split(',') if l])
                        if line.endswith(';'):
                            section = None
                        continue

                    if line.startswith('DATA='):
                        section = 'data'
                        headers = [d[0] for d in dimensions[0:-1]]
                        headers.extend([h.strip(';" ') for h in dimensions.pop()[1] if h])
                        writer = csv.DictWriter(outfile, headers)
                        writer.writeheader()
                        continue

                    if section == 'data':
                        if line.startswith(';'):
                            continue

                        values = {}
                        for dimname, dimvalues, dimcnt in dimensions:
                            values[dimname] = dimvalues[dimcnt]
                        i = len(dimensions) - 1
                        while dimensions[i][2] + 2 > len(dimensions[i][1]):
                            dimensions[i][2] = 0
                            i -= 1
                        dimensions[i][2] += 1

                        for i, d in enumerate(line.split(' ')):
                            values[headers[len(dimensions) + i]] = d

                        writer.writerow(values)


    def output(self):
        return LocalTarget(os.path.join('tmp', classpath(self), '0001.csv'))


class FiveYearPopulationColumns(ColumnsTask):

    def requires(self):
        return {
            'geoms': Geometry(),
            'tags': Tags()
        }

    def columns(self):
        geometries = self.input()['geometries']
        tags = self.input()['tags']
        total_pop = BMDColumn(
            id='total_pop',
            type='Numeric',
            name='Total Population',
            description='The total number of all people living in a geographic area.',
            aggregate='sum',
            weight=10,
            tags=[tags['demographics']]
        )
        return OrderedDict([
            ('gender', BMDColumn(
                id='gender',
                type='Numeric',
                name='Gender',
                weight=0
            )),
            ('cusec', geometries['cusec']),
            ('total_pop', total_pop),
            ('pop_0_4', BMDColumn()),
            ('pop_5_9', BMDColumn()),
            ('pop_10_14', BMDColumn()),
            ('pop_15_19', BMDColumn()),
            ('pop_20_24', BMDColumn()),
            ('pop_25_29', BMDColumn()),
            ('pop_30_34', BMDColumn()),
            ('pop_35_39', BMDColumn()),
            ('pop_40_44', BMDColumn()),
            ('pop_45_49', BMDColumn()),
            ('pop_50_54', BMDColumn()),
            ('pop_55_59', BMDColumn()),
            ('pop_60_64', BMDColumn()),
            ('pop_65_69', BMDColumn()),
            ('pop_70_74', BMDColumn()),
            ('pop_75_79', BMDColumn()),
            ('pop_80_84', BMDColumn()),
            ('pop_85_89', BMDColumn()),
            ('pop_90_94', BMDColumn()),
            ('pop_95_99', BMDColumn()),
            ('pop_100_more', BMDColumn()),
        ])


class FiveYearPopulation(TableTask):
    '''
    Load csv into postgres
    '''

    def requires(self):
        return Download()

    def runsession(self, session):
        pass