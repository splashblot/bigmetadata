'''
Sphinx functions for luigi bigmetadata tasks.
'''

import re
from jinja2 import Environment, PackageLoader
from luigi import WrapperTask, Task, LocalTarget, BooleanParameter, Parameter
from tasks.util import shell
from tasks.meta import current_session, OBSTag


env = Environment(loader=PackageLoader('catalog', 'templates'))

def test_filter(arg):
    pass

env.filters['test'] = test_filter

TAG_TEMPLATE = env.get_template('tag.html')


class GenerateRST(Task):

    force = BooleanParameter(default=False)
    format = Parameter()

    def __init__(self, *args, **kwargs):
        super(GenerateRST, self).__init__(*args, **kwargs)
        if self.force:
            shell('rm -rf catalog/source/*/*')

    def output(self):
        targets = {}
        session = current_session()
        for tag in session.query(OBSTag).filter(OBSTag.type=='category'):
            targets[tag.id] = LocalTarget('catalog/source/{type}/{tag}.rst'.format(
                type=tag.type,
                tag=tag.id))
        return targets

    def run(self):
        session = current_session()
        for tag_id, target in self.output().iteritems():
            fhandle = target.open('w')

            tag = session.query(OBSTag).get(tag_id)
            columns = [c for c in tag.columns if not c.has_denominator()]
            #columns.sort(lambda x, y: -x.weight.__cmp__(y.weight))
            columns.sort(lambda x, y: cmp(x.name, y.name))

            fhandle.write(TAG_TEMPLATE.render(tag=tag, columns=columns,
                                              format=self.format).encode('utf8'))
            fhandle.close()


class Sphinx(Task):

    force = BooleanParameter(default=False)
    format = Parameter(default='html')

    def requires(self):
        return GenerateRST(force=self.force, format=self.format)

    def complete(self):
        return False

    def run(self):
        shell('cd catalog && make {}'.format(self.format))
        # copy PDF outputs to HTML to allow for public access
        if self.format == 'latexpdf':
            shell('cp catalog/build/latex/*.pdf catalog/build/html/')
